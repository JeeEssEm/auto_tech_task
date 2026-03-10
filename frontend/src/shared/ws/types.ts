import type { Attachment } from "@/shared/api/chat-service"

export type ParsingStatus = "PENDING" | "IN_PROCESS" | "SUCCESS" | "FAILED"

export type GenerationStatusType = string

/**
 * Map of all WebSocket event types to their payload shapes.
 * To handle a new event, add its type here and pass a handler to `useChatSocket`.
 */
export type WsEventMap = {
  LLM_ANSWER: {
    id: number
    text: string
    attachments: Attachment[]
    created_at: string
  }
  PARSING_STATUS: {
    status: ParsingStatus
    attachment_id: string
  }
  GENERATION_STATUS: {
    status: GenerationStatusType
    step?: string
    progress?: number
  }
  EXPORT_READY: {
    chat_id: number
    export_key: string
    format: string
  }
  ERROR: {
    message: string
    [key: string]: unknown
  }
}

export type WsEventType = keyof WsEventMap

export type WsEventHandlers = {
  [K in WsEventType]?: (data: WsEventMap[K]) => void
}
