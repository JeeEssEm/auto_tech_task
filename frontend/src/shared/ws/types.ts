import type { Attachment } from "@/shared/api/chat-service"

export type ParsingStatus = "PENDING" | "IN_PROCESS" | "SUCCESS" | "FAILED"

export type GenerationStatusType = string

/**
 * Map of all WebSocket event types to their payload shapes.
 * To handle a new event, add its type here and pass a handler to `useChatSocket`.
 */
export type WsEventMap = {
  LLM_ANSWER: {
    chat_id?: number | string
    id: number
    text: string
    attachments: Attachment[]
    created_at: string
    is_final?: boolean
  }
  PARSING_STATUS: {
    chat_id?: number | string
    status: ParsingStatus
    attachment_id: string
  }
  GENERATION_STATUS: {
    chat_id?: number | string
    status: GenerationStatusType
    step?: string
    progress?: number
  }
  CONFLICT_REQUIRES_INPUT: {
    chat_id?: number | string
    run_id?: number
    conflicts: Array<{
      conflict_id: string
      title: string
      options: string[]
      rationale?: string
      evidence?: string[]
      resolved?: boolean
    }>
  }
  SECTION_AUDIT_FAILED: {
    chat_id?: number | string
    run_id?: number
    sections: Array<{
      section_id: string
      audit_notes: string[]
      unsupported_claims_count?: number
    }>
  }
  EXPORT_READY: {
    chat_id: number
    export_key: string
    format: string
  }
  ERROR: {
    message?: string
    [key: string]: unknown
  }
}

export type WsEventType = keyof WsEventMap

export type WsEventHandlers = {
  [K in WsEventType]?: (data: WsEventMap[K]) => void
}
