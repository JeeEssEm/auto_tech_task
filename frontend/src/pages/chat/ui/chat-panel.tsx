import { useEffect, useRef } from "react"
import { ArrowUp, FileText, Loader2, Paperclip, X } from "lucide-react"
import React from "react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import type { Message } from "@/shared/api/chat-service"
import type { ParsingStatus } from "@/shared/ws/types"
import type { PendingItemsResponse } from "@/shared/api/tz-service"
import type { FileItem, GenerationStep } from "../lib/types"
import { MessageBubble } from "./message-bubble"
import { ThinkingIndicator } from "./thinking-indicator"

type ChatPanelProps = {
  messages: Message[]
  isLoading: boolean
  parsingStatuses: Map<string, ParsingStatus>
  generationSteps: GenerationStep[]
  isThinking: boolean
  inputValue: string
  isSending: boolean
  isSubmitDisabled: boolean
  files: FileItem[]
  fileInputRef: React.RefObject<HTMLInputElement | null>
  onInput: (e: React.FormEvent<HTMLTextAreaElement>) => void
  onSend: () => void
  onAttachClick: () => void
  onFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  onRemoveFile: (item: FileItem) => void
  onFileClick: (fileId: string, fileName: string) => void
  onClose: () => void
  pendingItems: PendingItemsResponse | null
  isPendingItemsLoading: boolean
  selectedActionId: string | null
  onSelectAction: (actionId: string) => void
  onClearSelectedAction: () => void
}

export function ChatPanel({
  messages,
  isLoading,
  parsingStatuses,
  generationSteps,
  isThinking,
  inputValue,
  isSending,
  isSubmitDisabled,
  files,
  fileInputRef,
  onInput,
  onSend,
  onAttachClick,
  onFileChange,
  onRemoveFile,
  onFileClick,
  onClose,
  pendingItems,
  isPendingItemsLoading,
  selectedActionId,
  onSelectAction,
  onClearSelectedAction,
}: ChatPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [activeTab, setActiveTab] = React.useState<"chat" | "actions">("chat")

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, generationSteps])

  return (
    <div className="flex flex-col h-full border-l bg-background">
      {/* Header */}
      <div className="flex items-center justify-between border-b px-3 py-2.5 shrink-0">
        <div className="flex items-center gap-1 rounded-md bg-muted p-0.5">
          <button
            type="button"
            onClick={() => setActiveTab("chat")}
            className={cn(
              "rounded px-2 py-1 text-xs font-medium transition-colors",
              activeTab === "chat" ? "bg-background text-foreground" : "text-muted-foreground",
            )}
          >
            Чат
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("actions")}
            className={cn(
              "rounded px-2 py-1 text-xs font-medium transition-colors",
              activeTab === "actions" ? "bg-background text-foreground" : "text-muted-foreground",
            )}
          >
            Действия
          </button>
        </div>
        <Button variant="ghost" size="icon" className="size-7" onClick={onClose}>
          <X className="size-4" />
        </Button>
      </div>

      {activeTab === "chat" ? (
        <>
          {/* Messages */}
          <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-4 chat-scrollbar">
            {selectedActionId ? (
              <div className="rounded-md border border-primary/30 bg-primary/5 px-3 py-2 text-xs">
                <p className="font-medium">Режим ответа на действие</p>
                <p className="text-muted-foreground mt-1">Следующее сообщение отправится в resolve endpoint.</p>
                <button
                  type="button"
                  className="mt-2 text-xs text-primary hover:underline"
                  onClick={onClearSelectedAction}
                >
                  Отменить выбор
                </button>
              </div>
            ) : null}

            {isLoading ? (
              <div className="flex h-full items-center justify-center">
                <Loader2 className="size-6 animate-spin text-muted-foreground" />
              </div>
            ) : messages.length === 0 ? (
              <div className="flex h-full items-center justify-center text-xs text-muted-foreground text-center px-4">
                Отправьте сообщение, чтобы начать генерацию ТЗ
              </div>
            ) : (
              messages.map(msg => (
                <MessageBubble
                  key={msg.id}
                  message={msg}
                  parsingStatuses={parsingStatuses}
                  onFileClick={onFileClick}
                />
              ))
            )}
            {isThinking && generationSteps.length > 0 && (
              <ThinkingIndicator steps={generationSteps} />
            )}
          </div>
        </>
      ) : (
        <div className="flex-1 overflow-y-auto p-3 chat-scrollbar">
          {isPendingItemsLoading ? (
            <div className="flex h-full items-center justify-center">
              <Loader2 className="size-6 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <div className="space-y-3">
              <div>
                <p className="text-xs font-semibold uppercase text-muted-foreground mb-2">Конфликты</p>
                {pendingItems?.conflicts?.length ? (
                  <div className="space-y-2">
                    {pendingItems.conflicts.map(conflict => (
                      <div key={conflict.id} className="rounded-md border p-2.5 space-y-1.5">
                        <p className="text-xs font-medium">{conflict.scope} / {conflict.property}</p>
                        {conflict.rationale ? (
                          <p className="text-xs text-muted-foreground">{conflict.rationale}</p>
                        ) : null}
                        {conflict.options.length > 0 ? (
                          <ul className="text-xs text-muted-foreground list-disc pl-4">
                            {conflict.options.map((opt, idx) => (
                              <li key={`${conflict.id}-${idx}`}>{opt}</li>
                            ))}
                          </ul>
                        ) : null}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground">Нет активных конфликтов</p>
                )}
              </div>

              <div>
                <p className="text-xs font-semibold uppercase text-muted-foreground mb-2">Действия</p>
                {pendingItems?.actions?.length ? (
                  <div className="space-y-2">
                    {pendingItems.actions.map(action => (
                      <button
                        key={action.id}
                        type="button"
                        className={cn(
                          "w-full text-left rounded-md border p-2.5 space-y-1.5 transition-colors hover:bg-accent/40",
                          selectedActionId === action.id && "border-primary bg-primary/5"
                        )}
                        onClick={() => {
                          onSelectAction(action.id)
                          setActiveTab("chat")
                        }}
                      >
                        <p className="text-xs font-medium">{action.question}</p>
                        {action.options.length > 0 ? (
                          <p className="text-xs text-muted-foreground">
                            Варианты: {action.options.join(", ")}
                          </p>
                        ) : null}
                        <p className="text-[11px] text-primary">Выбрать и ответить в чате</p>
                      </button>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground">Нет активных действий</p>
                )}
              </div>

              <div className="rounded-md border border-dashed p-2.5 text-xs text-muted-foreground">
                Посмотрите список и перейдите во вкладку "Чат", чтобы описать, что нужно поправить.
              </div>
            </div>
          )}
        </div>
      )}

      {/* File previews */}
      {activeTab === "chat" && files.length > 0 && (
        <div className="flex flex-wrap gap-1.5 px-3 py-2 border-t">
          {files.map((item, index) => (
            <div
              key={`${item.file.name}-${index}`}
              className={cn(
                "flex items-center gap-1.5 rounded-md border px-2 py-1 text-[11px] transition-colors",
                item.status === "error"
                  ? "bg-destructive/10 border-destructive/20 text-destructive"
                  : "bg-muted/40 text-foreground",
                item.status === "uploading" && "opacity-70",
              )}
            >
              <FileText className="size-3" />
              <span className="max-w-[100px] truncate">{item.file.name}</span>
              {item.status === "uploading" && <Loader2 className="size-3 animate-spin" />}
              <button onClick={() => onRemoveFile(item)} className="text-muted-foreground hover:text-destructive">
                <X className="size-3" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Input */}
      {activeTab === "chat" && (
      <div className="border-t px-3 py-2.5 shrink-0">
        <input type="file" multiple className="hidden" ref={fileInputRef} onChange={onFileChange} />
        <div className="flex items-end gap-1.5 rounded-lg border bg-background px-2 py-1.5 focus-within:ring-1 focus-within:ring-ring">
          <Button
            variant="ghost"
            size="icon"
            className="size-7 shrink-0 text-muted-foreground rounded-full hover:bg-muted"
            onClick={onAttachClick}
            disabled={isSending}
          >
            <Paperclip className="size-4" />
          </Button>
          <textarea
            value={inputValue}
            onInput={onInput}
            placeholder="Сообщение…"
            className="flex-1 min-h-[28px] max-h-[120px] resize-none border-0 bg-transparent py-1 text-sm leading-relaxed outline-none placeholder:text-muted-foreground"
            rows={1}
            onKeyDown={e => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault()
                if (!isSubmitDisabled) onSend()
              }
            }}
          />
          <Button
            size="icon"
            className="size-7 shrink-0 rounded-full"
            disabled={isSubmitDisabled}
            onClick={onSend}
          >
            {isSending ? <Loader2 className="size-4 animate-spin" /> : <ArrowUp className="size-4" />}
          </Button>
        </div>
      </div>
      )}
    </div>
  )
}
