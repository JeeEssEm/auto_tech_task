import { useEffect, useRef } from "react"
import { ArrowUp, FileText, Loader2, MessageSquareText, Paperclip, X } from "lucide-react"
import React from "react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import type { Message } from "@/shared/api/chat-service"
import type { ParsingStatus } from "@/shared/ws/types"
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
}: ChatPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, generationSteps])

  return (
    <div className="flex flex-col h-full border-l bg-background">
      {/* Header */}
      <div className="flex items-center justify-between border-b px-3 py-2.5 shrink-0">
        <div className="flex items-center gap-2">
          <MessageSquareText className="size-4 text-primary" />
          <span className="text-sm font-medium">Чат</span>
        </div>
        <Button variant="ghost" size="icon" className="size-7" onClick={onClose}>
          <X className="size-4" />
        </Button>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-4 chat-scrollbar">
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

      {/* File previews */}
      {files.length > 0 && (
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
    </div>
  )
}
