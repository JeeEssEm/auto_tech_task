import { useEffect, useRef } from "react"

import { API_URL } from "@/shared/config/backend"
import type { WsEventHandlers, WsEventType } from "./types"

const WS_RECONNECT_DELAY = 3000

/**
 * Manages a WebSocket connection for a given chat and dispatches
 * incoming messages to typed event handlers.
 *
 * Usage:
 * ```ts
 * useChatSocket(chatId, {
 *   LLM_ANSWER: (data) => { ... },
 * })
 * ```
 */
export function useChatSocket(chatId: string | undefined, handlers: WsEventHandlers) {
  const handlersRef = useRef(handlers)

  useEffect(() => {
    handlersRef.current = handlers
  })

  useEffect(() => {
    if (!chatId) return

    let ws: WebSocket
    let reconnectTimeout: ReturnType<typeof setTimeout>
    let disposed = false

    const connect = () => {
      // In dev, use Vite proxy (same origin) so cookies are sent.
      // In prod, connect directly to the API server.
      const isDev = import.meta.env.DEV
      const wsUrl = isDev
        ? `${location.protocol === "https:" ? "wss:" : "ws:"}//${location.host}/chat/ws`
        : `${API_URL.replace(/^http/, "ws")}/chat/ws`
      ws = new WebSocket(wsUrl)

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)

          if (chatId) {
            const eventChatId = (data as { chat_id?: number | string }).chat_id
            if (eventChatId !== undefined && String(eventChatId) !== String(chatId)) {
              return
            }
          }

          const type = data.type as WsEventType
          const handler = handlersRef.current[type]
          if (handler) {
            handler(data)
          }
        } catch (e) {
          console.error("WS parse error", e)
        }
      }

      ws.onclose = () => {
        if (!disposed) {
          reconnectTimeout = setTimeout(connect, WS_RECONNECT_DELAY)
        }
      }

      ws.onerror = (error) => {
        console.error("WebSocket error", error)
        ws.close()
      }
    }

    connect()

    return () => {
      disposed = true
      clearTimeout(reconnectTimeout)
      if (ws) {
        ws.onclose = null
        ws.close()
      }
    }
  }, [chatId])
}
