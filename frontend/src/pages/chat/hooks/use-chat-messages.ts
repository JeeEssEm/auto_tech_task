import { useCallback, useEffect, useRef, useState } from "react"
import { useNavigate } from "react-router-dom"
import { toast } from "sonner"

import { chatApi } from "@/shared/api/chat-service"
import type { Message } from "@/shared/api/chat-service"
import type { WsEventMap } from "@/shared/ws/types"

export function useChatMessages(chatId: string | undefined) {
  const navigate = useNavigate()
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Fetch messages on mount / chat change
  useEffect(() => {
    if (!chatId) return

    setIsLoading(true)
    const controller = new AbortController()

    chatApi.getMessages(chatId, controller.signal)
      .then(setMessages)
      .catch(err => {
        if (err.name !== "AbortError") {
          if (err.message?.includes("404") || err.code === "404") {
            toast.error("Чат не найден")
            navigate("/chats/new")
          } else {
            console.error(err)
            toast.error("Не удалось загрузить сообщения")
          }
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setIsLoading(false)
        }
      })

    return () => controller.abort()
  }, [chatId, navigate])

  // WS handler — to be passed into useChatSocket at page level
  const handleLlmAnswer = useCallback((data: WsEventMap["LLM_ANSWER"]) => {
    const newMessage: Message = {
      id: data.id,
      sender: "LLM",
      text: data.text,
      attachments: data.attachments || [],
      created_at: data.created_at,
    }
    setMessages(prev => [...prev, newMessage])
  }, [])

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  const scrollToBottom = useCallback(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [])

  return { messages, setMessages, isLoading, scrollRef, handleLlmAnswer, scrollToBottom }
}
