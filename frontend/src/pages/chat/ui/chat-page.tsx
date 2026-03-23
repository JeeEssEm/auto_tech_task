import React, { useCallback, useEffect, useRef, useState } from "react"
import { useParams } from "react-router-dom"
import { toast } from "sonner"
import { FileText, GitBranch, MessageSquareText, ScrollText } from "lucide-react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { fileApi } from "@/shared/api/file-service"
import { tzApi } from "@/shared/api/tz-service"
import type { PendingItemsResponse } from "@/shared/api/tz-service"
import type { WsEventMap } from "@/shared/ws/types"
import { useChatSocket } from "@/shared/ws/use-chat-socket"

import { useChatMessages } from "../hooks/use-chat-messages"
import { useFileAttachments } from "../hooks/use-file-attachments"
import { useGenerationStatus } from "../hooks/use-generation-status"
import { useParsingStatus } from "../hooks/use-parsing-status"
import { useSendMessage } from "../hooks/use-send-message"
import { useWorkspaceData } from "../hooks/use-workspace-data"
import type { TZSection } from "../lib/types"
import type { WorkspaceTab } from "../hooks/use-workspace-data"
import { ChatPanel } from "./chat-panel"
import { DocumentView } from "./document-view.tsx"
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
  const [pendingItems, setPendingItems] = useState<PendingItemsResponse | null>(null)
  const [pendingItemsLoading, setPendingItemsLoading] = useState(false)
  const [selectedActionId, setSelectedActionId] = useState<string | null>(null)
  const pipelineTriggered = useRef(false)

  // Chat data
  const { messages, setMessages, isLoading, handleLlmAnswer } = useChatMessages(id)
  const { steps, isThinking, handleGenerationStatus, completeGeneration, failGeneration, resetGeneration } = useGenerationStatus()

  // Workspace data (document, files, graph)
  const workspace = useWorkspaceData(id)

  // Wrap LLM_ANSWER to also complete generation thinking + refresh TZ
  const handleLlmAnswerWithComplete = useCallback(
    (data: WsEventMap["LLM_ANSWER"]) => {
      handleLlmAnswer(data)
      if (data.is_final !== false) {
        completeGeneration()
        // After a short delay, refresh generations to pick up the new TZ
        setTimeout(() => {
          workspace.refreshGenerations()
          workspace.refreshGraph()
        }, 2000)
      }
    },
    [completeGeneration, handleLlmAnswer, workspace.refreshGenerations, workspace.refreshGraph],
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

  const refreshPendingItems = useCallback(async () => {
    if (!id) return
    setPendingItemsLoading(true)
    try {
      const data = await tzApi.getPendingItems(id)
      setPendingItems(data)
    } catch {
      setPendingItems({ conflicts: [], actions: [] })
    } finally {
      setPendingItemsLoading(false)
    }
  }, [id])

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
    resolveActionId: selectedActionId,
    onActionResolved: async () => {
      setSelectedActionId(null)
      await refreshPendingItems()
    },
  })

  // --- Auto-trigger full pipeline when parsed files are available but no generation exists ---
  useEffect(() => {
    if (!id) return
    if (pipelineTriggered.current) return
    if (workspace.generations.length > 0) return
    if (workspace.attachments.length === 0) return
    if (workspace.isLoading) return

    let cancelled = false

    const maybeStartPipeline = async () => {
      try {
        const status = await tzApi.getGenerationStatus(id)
        if (cancelled || pipelineTriggered.current) return

        // If any run already exists (PENDING/IN_PROCESS/SUCCESS/FAILED), do not auto-trigger again.
        if (status.status !== null) {
          pipelineTriggered.current = true
          return
        }

        pipelineTriggered.current = true
        const attachmentIds = workspace.attachments.map(a => a.key)
        await tzApi.runFullPipeline(id, attachmentIds)
        if (!cancelled) {
          toast.info("Генерация ТЗ запущена")
        }
      } catch (err) {
        if (!cancelled) {
          pipelineTriggered.current = false
          const msg = err instanceof Error ? err.message : "Не удалось запустить генерацию"
          toast.error(msg)
        }
      }
    }

    maybeStartPipeline()

    return () => {
      cancelled = true
    }
  }, [id, workspace.generations.length, workspace.attachments.length, workspace.isLoading])

  // Reset trigger flag when chat changes
  useEffect(() => {
    pipelineTriggered.current = false
    resetGeneration()
  }, [id, resetGeneration])

  // --- EXPORT_READY handler ---
  const handleExportReady = useCallback((data: WsEventMap["EXPORT_READY"]) => {
    const targetChatId = String(data.chat_id)

    tzApi.downloadExport(targetChatId, data.export_key).catch(() => {
      toast.error("Ошибка скачивания файла")
    })

    toast.success("Экспорт готов!", {
      action: {
        label: "Скачать",
        onClick: () => {
          tzApi.downloadExport(targetChatId, data.export_key).catch(() => {
            toast.error("Ошибка скачивания файла")
          })
        },
      },
      duration: 10000,
    })
  }, [])

  const handlePipelineError = useCallback((data: WsEventMap["ERROR"]) => {
    const message = typeof data.message === "string" && data.message.length > 0
      ? data.message
      : "Ошибка пайплайна генерации"
    failGeneration(message)
    toast.error(message)
  }, [failGeneration])

  const handleGenerationStatusWithRefresh = useCallback((data: WsEventMap["GENERATION_STATUS"]) => {
    handleGenerationStatus(data)
    const status = String(data.status || "").toUpperCase()
    if (status.includes("COMPLETED") || status.includes("FAILED")) {
      refreshPendingItems()
      workspace.refreshGraph()
    }
  }, [handleGenerationStatus, refreshPendingItems, workspace.refreshGraph])

  useChatSocket(id, {
    LLM_ANSWER: handleLlmAnswerWithComplete,
    PARSING_STATUS: handleParsingStatus,
    GENERATION_STATUS: handleGenerationStatusWithRefresh,
    EXPORT_READY: handleExportReady,
    ERROR: handlePipelineError,
  })

  useEffect(() => {
    refreshPendingItems()
  }, [refreshPendingItems])

  useEffect(() => {
    if (!selectedActionId || !pendingItems) return
    if (!pendingItems.actions.some(a => a.id === selectedActionId)) {
      setSelectedActionId(null)
    }
  }, [selectedActionId, pendingItems])

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

  const handleSaveSections = useCallback(
    async (sections: TZSection[]) => {
      if (!id) return
      await tzApi.updateSections(id, sections)
      toast.success("Документ сохранен")
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
              selected={workspace.selectedGeneration}
              content={workspace.generationContent}
              isContentLoading={workspace.isContentLoading}
              onRegenerateBlock={handleRegenerateBlock}
              onGenerateCustomBlock={handleGenerateCustomBlock}
              onExport={handleExport}
              onSaveSections={handleSaveSections}
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
            <KnowledgeGraphTab graph={workspace.graph} facts={workspace.graphFacts} focusedFactId={workspace.focusedFactId} />
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
              pendingItems={pendingItems}
              isPendingItemsLoading={pendingItemsLoading}
              selectedActionId={selectedActionId}
              onSelectAction={setSelectedActionId}
              onClearSelectedAction={() => setSelectedActionId(null)}
            />
          </div>
        )}
      </div>
    </div>
  )
}
