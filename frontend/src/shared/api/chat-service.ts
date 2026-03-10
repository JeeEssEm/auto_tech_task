// Enum matching backend - using const object for erasableSyntaxOnly compatibility
export const ChatTemplate = {
  GOST19: "gost19",
  FREE: "free",
  IT_PROJECT: "it_project",
  CONSTRUCTION_PROJECT: "construction_project",
  ENGINEERING_PROJECT: "engineering_project"
} as const

export type ChatTemplate = typeof ChatTemplate[keyof typeof ChatTemplate]

export type CreateChatPayload = {
  name: string
  init_user_message: string
  template_type: ChatTemplate
  attachment_ids: string[]
}

export type Chat = {
  id: string
  name: string
  template_type: ChatTemplate
  created_at: string
  updated_at: string
}

export type ChatPreview = {
  id: string | number
  template: string
  name: string
}

export type GetChatsParams = {
  page?: number
  limit?: number
}

export type Attachment = {
  key: string
  file_name: string
  file_type: string
  file_size: number
}

export type Message = {
  id: number
  sender: "user" | "LLM"
  text: string
  attachments: Attachment[]
  created_at: string
}

export type SendMessagePayload = {
  text: string
  attachment_ids: string[]
}

export type GenerationRun = {
  id: number
  status: string
  step: string | null
  progress: number
  result_key: string | null
  created_at: string
}

export type ParsedAttachmentDetail = {
  key: string
  file_name: string
  file_type: string
  file_size: number
  transcript: string
}

import { apiClient } from "@/shared/api/client"

export const chatEvents = new EventTarget()

export const chatApi = {
  createChat: async (payload: CreateChatPayload): Promise<number> => {
     const chatId = await apiClient.post<number>("/chat/create", payload)
     chatEvents.dispatchEvent(new Event("chatCreated"))
     return chatId
  },

  getChats: async ({ page = 1, limit = 50 }: GetChatsParams = {}, signal?: AbortSignal): Promise<ChatPreview[]> => {
     // Building query string
     const params = new URLSearchParams()
     if (page) params.append("page", page.toString())
     if (limit) params.append("limit", limit.toString())

     return await apiClient.get<ChatPreview[]>(`/chat/all?${params.toString()}`, { signal })
  },

  getMessages: async (chatId: string, signal?: AbortSignal): Promise<Message[]> => {
     return await apiClient.get<Message[]>(`/chat/${chatId}/messages`, { signal })
  },

  sendMessage: async (chatId: string, payload: SendMessagePayload): Promise<Message> => {
     return await apiClient.post<Message>(`/chat/${chatId}/messages`, payload)
  },

  // Mock for now
  getChat: async (chatId: string): Promise<Chat> => {
      // return await apiClient.get<Chat>(`/chat/${chatId}`)
      await new Promise(r => setTimeout(r, 500))
      return {
          id: chatId,
          name: "Новый чат",
          template_type: ChatTemplate.FREE,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
      }
  },

  getGenerations: async (chatId: string, signal?: AbortSignal): Promise<GenerationRun[]> => {
    return await apiClient.get<GenerationRun[]>(`/tz/${chatId}/generations`, { signal })
  },

  getGenerationContent: async (chatId: string, resultKey: string, signal?: AbortSignal): Promise<unknown> => {
    const data = await apiClient.get<{ content: unknown }>(`/tz/${chatId}/generation-content?${new URLSearchParams({ result_key: resultKey })}`, { signal })
    // content is a JSON string from S3 — parse if needed
    if (typeof data.content === "string") {
      try { return JSON.parse(data.content) } catch { return data.content }
    }
    return data.content
  },

  getParsedAttachments: async (chatId: string, signal?: AbortSignal): Promise<ParsedAttachmentDetail[]> => {
    return await apiClient.get<ParsedAttachmentDetail[]>(`/chat/${chatId}/parsed-files`, { signal })
  },
}
