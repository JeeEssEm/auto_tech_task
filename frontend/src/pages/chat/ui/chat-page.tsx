import React, { useCallback, useEffect, useRef, useState } from "react"
import { useParams } from "react-router-dom"
import { toast } from "sonner"
import { FileText, GitBranch, MessageSquareText, ScrollText } from "lucide-react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { fileApi } from "@/shared/api/file-service"
import { tzApi } from "@/shared/api/tz-service"
import type { WsEventMap } from "@/shared/ws/types"
import { useChatSocket } from "@/shared/ws/use-chat-socket"

import { useChatMessages } from "../hooks/use-chat-messages"
import { useFileAttachments } from "../hooks/use-file-attachments"
import { useGenerationStatus } from "../hooks/use-generation-status"
import { useParsingStatus } from "../hooks/use-parsing-status"
import { useSendMessage } from "../hooks/use-send-message"
import { useWorkspaceData } from "../hooks/use-workspace-data"
import type { WorkspaceTab } from "../hooks/use-workspace-data"
import { ChatPanel } from "./chat-panel"
import { DocumentView } from "./document-view"
import { AttachmentsTab } from "./side-panel/attachments-tab"
import { KnowledgeGraphTab } from "./side-panel/knowledge-graph-tab"

const tabs: { id: WorkspaceTab; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { id: "document", label: "Документ", icon: ScrollText },
  { id: "files", label: "Файлы", icon: FileText },
  { id: "graph", label: "Граф", icon: GitBranch },
]

export function ChatPage() {
  const { id } = useParams()
  const [inputValue, setInputValue] = useState("")
  const [chatOpen, setChatOpen] = useState(true)
  const pipelineTriggered = useRef(false)

  // Chat data
  const { messages, setMessages, isLoading, handleLlmAnswer } = useChatMessages(id)
  const { steps, isThinking, handleGenerationStatus, completeGeneration } = useGenerationStatus()

  // Workspace data (document, files, graph)
  const workspace = useWorkspaceData(id)

  // Wrap LLM_ANSWER to also complete generation thinking + refresh TZ
  const handleLlmAnswerWithComplete = useCallback(
    (data: WsEventMap["LLM_ANSWER"]) => {
      completeGeneration()
      handleLlmAnswer(data)
      // After a short delay, refresh generations to pick up the new TZ
      setTimeout(() => workspace.refreshGenerations(), 2000)
    },
    [completeGeneration, handleLlmAnswer, workspace.refreshGenerations],
  )

  const handleParsingFailed = useCallback((_attachmentId: string, fileName: string) => {
    toast.error(`Не удалось обработать файл «${fileName}»`)
  }, [])

  const handleParsingFailedCleanup = useCallback((attachmentId: string) => {
    setMessages(prev =>
      prev.map(msg => ({
        ...msg,
        attachments: msg.attachments.filter(a => a.key !== attachmentId),
      })),
    )
  }, [setMessages])

  const handleParsingSuccess = useCallback(() => {
    workspace.refreshAttachments()
  }, [workspace.refreshAttachments])

  const { statusMap, registerName, trackAttachments, handleParsingStatus } = useParsingStatus({
    onFailed: handleParsingFailed,
    onFailedCleanup: handleParsingFailedCleanup,
    onSuccess: handleParsingSuccess,
  })
  const { files, fileInputRef, handleAttachClick, handleFileChange, removeFile, clearFiles } =
    useFileAttachments({ onFileUploaded: registerName })
  const { isSending, handleSendMessage, isSubmitDisabled } = useSendMessage({
    chatId: id,
    files,
    inputValue,
    setMessages,
    setInputValue,
    clearFiles,
    onAttachmentsSent: trackAttachments,
  })

  // --- Auto-trigger full pipeline when parsed files are available but no generation exists ---
  useEffect(() => {
    if (!id) return
    if (pipelineTriggered.current) return
    if (workspace.generations.length > 0) return
    if (workspace.attachments.length === 0) return
    if (workspace.isLoading) return

    pipelineTriggered.current = true
    const attachmentIds = workspace.attachments.map(a => a.key)

    tzApi
      .runFullPipeline(id, attachmentIds)
      .then(() => toast.info("Генерация ТЗ запущена"))
      .catch(err => {
        pipelineTriggered.current = false
        const msg = err instanceof Error ? err.message : "Не удалось запустить генерацию"
        toast.error(msg)
      })
  }, [id, workspace.generations.length, workspace.attachments.length, workspace.isLoading])

  // Reset trigger flag when chat changes
  useEffect(() => {
    pipelineTriggered.current = false
  }, [id])

  // --- EXPORT_READY handler ---
  const handleExportReady = useCallback((data: WsEventMap["EXPORT_READY"]) => {
    toast.success("Экспорт готов!", {
      action: {
        label: "Скачать",
        onClick: () => tzApi.downloadExport(String(data.chat_id), data.export_key),
      },
      duration: 10000,
    })
  }, [])

  useChatSocket(id, {
    LLM_ANSWER: handleLlmAnswerWithComplete,
    PARSING_STATUS: handleParsingStatus,
    GENERATION_STATUS: handleGenerationStatus,
    EXPORT_READY: handleExportReady,
  })

  // --- Document-level callbacks ---
  const handleRegenerateBlock = useCallback(
    (fieldPath: string, instruction?: string) => {
      if (!id) return
      tzApi.regenerateBlock(id, fieldPath, instruction).catch(err => {
        toast.error(err instanceof Error ? err.message : "Ошибка перегенерации")
      })
    },
    [id],
  )

  const handleGenerateCustomBlock = useCallback(
    (fieldPath: string, customTopic: string) => {
      if (!id) return
      tzApi.generateCustomBlock(id, fieldPath, customTopic).catch(err => {
        toast.error(err instanceof Error ? err.message : "Ошибка генерации блока")
      })
    },
    [id],
  )

  const handleManualEdit = useCallback(
    async (fieldPath: string, value: unknown) => {
      if (!id) return
      await tzApi.manualEditBlock(id, fieldPath, value)
      toast.success("Изменения сохранены")
      workspace.refreshContent()
    },
    [id, workspace.refreshContent],
  )

  const handleExport = useCallback(
    (resultKey: string, format: "markdown" | "word" | "pdf") => {
      if (!id) return
      tzApi
        .exportTZ(id, resultKey, format)
        .then(() => toast.info("Экспорт запущен…"))
        .catch(err => {
          toast.error(err instanceof Error ? err.message : "Ошибка экспорта")
        })
    },
    [id],
  )

  const handleUpdateCustomSections = useCallback(
    async (sectionKey: string, nodes: import("../lib/types").ContentNode[]) => {
      if (!id) return
      await tzApi.updateCustomSections(id, sectionKey, nodes)
      workspace.refreshContent()
    },
    [id, workspace.refreshContent],
  )

  const handleFileClick = async (fileId: string, fileName: string) => {
    try {
      await fileApi.downloadFile(fileId, fileName)
    } catch (e) {
      toast.error("Ошибка скачивания файла")
      console.error(e)
    }
  }

  const handleInput = (e: React.FormEvent<HTMLTextAreaElement>) => {
    const target = e.target as HTMLTextAreaElement
    target.style.height = "auto"
    target.style.height = `${Math.min(target.scrollHeight, 200)}px`
    setInputValue(target.value)
  }

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)]">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-4 border-b px-4 py-2 shrink-0">
        <div className="flex items-center gap-1">
          {tabs.map(tab => {
            const Icon = tab.icon
            return (
              <button
                key={tab.id}
                onClick={() => workspace.setActiveTab(tab.id)}
                className={cn(
                  "flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors",
                  workspace.activeTab === tab.id
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50",
                )}
              >
                <Icon className="size-3.5" />
                <span className="hidden sm:inline">{tab.label}</span>
              </button>
            )
          })}
        </div>

        <div className="flex items-center gap-3">
          {/* Generation count */}
          {workspace.generations.length > 0 && (
            <span className="text-xs text-muted-foreground hidden sm:inline">
              {workspace.generations.length} верс. ТЗ
            </span>
          )}
          {/* Files count */}
          {workspace.attachments.length > 0 && (
            <span className="text-xs text-muted-foreground hidden sm:inline">
              {workspace.attachments.length} файлов
            </span>
          )}
          {/* Chat toggle */}
          {!chatOpen && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs gap-1.5"
              onClick={() => setChatOpen(true)}
            >
              <MessageSquareText className="size-3.5" />
              <span className="hidden sm:inline">Чат</span>
            </Button>
          )}
        </div>
      </div>

      {/* Main content */}
      <div className="flex flex-1 min-h-0">
        {/* Workspace area */}
        <div className="flex-1 min-w-0">
          {workspace.activeTab === "document" && (
            <DocumentView
              chatId={id}
              generations={workspace.generations}
              selected={workspace.selectedGeneration}
              onSelect={workspace.setSelectedGeneration}
              content={workspace.generationContent}
              isContentLoading={workspace.isContentLoading}
              onRegenerateBlock={handleRegenerateBlock}
              onGenerateCustomBlock={handleGenerateCustomBlock}
              onManualEdit={handleManualEdit}
              onExport={handleExport}
              onUpdateCustomSections={handleUpdateCustomSections}
            />
          )}
          {workspace.activeTab === "files" && (
            <AttachmentsTab
              attachments={workspace.attachments}
              selected={workspace.selectedAttachment}
              onSelect={workspace.setSelectedAttachment}
            />
          )}
          {workspace.activeTab === "graph" && (
            <KnowledgeGraphTab graph={workspace.graph} />
          )}
        </div>

        {/* Chat panel */}
        {chatOpen && (
          <div className="w-[380px] shrink-0">
            <ChatPanel
              messages={messages}
              isLoading={isLoading}
              parsingStatuses={statusMap}
              generationSteps={steps}
              isThinking={isThinking}
              inputValue={inputValue}
              isSending={isSending}
              isSubmitDisabled={isSubmitDisabled}
              files={files}
              fileInputRef={fileInputRef}
              onInput={handleInput}
              onSend={handleSendMessage}
              onAttachClick={handleAttachClick}
              onFileChange={handleFileChange}
              onRemoveFile={removeFile}
              onFileClick={handleFileClick}
              onClose={() => setChatOpen(false)}
            />
          </div>
        )}
      </div>
    </div>
  )
}
