import { Loader2 } from "lucide-react"
import React from "react"

import type { Message } from "@/shared/api/chat-service"
import type { ParsingStatus } from "@/shared/ws/types"
import type { GenerationStep } from "../lib/types"
import { MessageBubble } from "./message-bubble"
import { ThinkingIndicator } from "./thinking-indicator"

type MessageListProps = {
  messages: Message[]
  isLoading: boolean
  scrollRef: React.RefObject<HTMLDivElement | null>
  parsingStatuses: Map<string, ParsingStatus>
  generationSteps: GenerationStep[]
  isThinking: boolean
  onFileClick: (fileId: string, fileName: string) => void
}

export function MessageList({
  messages,
  isLoading,
  scrollRef,
  parsingStatuses,
  generationSteps,
  isThinking,
  onFileClick,
}: MessageListProps) {
  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 chat-scrollbar">
      <div className="mx-auto max-w-3xl xl:max-w-4xl space-y-6">
      {isLoading && (
        <div className="flex h-full items-center justify-center text-muted-foreground">
          <Loader2 className="size-8 animate-spin" />
        </div>
      )}
      {!isLoading && messages.length === 0 && (
        <div className="flex h-full items-center justify-center text-muted-foreground">
          Нет сообщений
        </div>
      )}
      {!isLoading &&
        messages.map(msg => (
          <MessageBubble
            key={msg.id}
            message={msg}
            parsingStatuses={parsingStatuses}
            onFileClick={onFileClick}
          />
        ))}
      {isThinking && generationSteps.length > 0 && (
        <ThinkingIndicator steps={generationSteps} />
      )}
      </div>
    </div>
  )
}
