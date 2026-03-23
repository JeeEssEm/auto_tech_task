import React, { useState } from "react"
import { toast } from "sonner"

import { chatApi } from "@/shared/api/chat-service"
import { tzApi } from "@/shared/api/tz-service"
import type { Attachment, Message } from "@/shared/api/chat-service"
import type { FileItem } from "../lib/types"

type UseSendMessageOptions = {
  chatId: string | undefined
  files: FileItem[]
  inputValue: string
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>
  setInputValue: (value: string) => void
  clearFiles: () => void
  onAttachmentsSent?: (attachments: Attachment[]) => void
  resolveActionId?: string | null
  onActionResolved?: (actionId: string) => void
}

export function useSendMessage({
  chatId,
  files,
  inputValue,
  setMessages,
  setInputValue,
  clearFiles,
  onAttachmentsSent,
  resolveActionId,
  onActionResolved,
}: UseSendMessageOptions) {
  const [isSending, setIsSending] = useState(false)

  const handleSendMessage = async () => {
    if (!chatId) return
    if (!inputValue.trim() && files.length === 0) return

    if (files.some(f => f.status === "uploading")) {
      toast.warning("Дождитесь загрузки файлов")
      return
    }

    if (files.some(f => f.status === "error")) {
      toast.warning("Некоторые файлы не загрузились. Удалите их перед отправкой.")
      return
    }

    setIsSending(true)
    const tempId = Date.now()

    try {
      const attachmentIds = files
        .filter(f => f.status === "success" && f.id)
        .map(f => f.id!)

      if (resolveActionId && attachmentIds.length > 0) {
        toast.warning("Для ответа на действие отправьте только текст без файлов")
        return
      }

      const optimisticMessage: Message = {
        id: tempId,
        sender: "user",
        text: inputValue,
        attachments: files
          .filter(f => f.status === "success")
          .map(f => ({
            key: f.id!,
            file_name: f.file.name,
            file_type: f.file.type,
            file_size: f.file.size,
          })),
        created_at: new Date().toISOString(),
      }

      setMessages(prev => [...prev, optimisticMessage])
      setInputValue("")
      clearFiles()

      // Reset textarea height
      const textarea = document.querySelector("textarea")
      if (textarea) textarea.style.height = "auto"

      if (resolveActionId) {
        await tzApi.resolveConflict(chatId, resolveActionId, optimisticMessage.text)
        onActionResolved?.(resolveActionId)
        toast.success("Ответ на действие отправлен")
      } else {
        const sentMessage = await chatApi.sendMessage(chatId, {
          text: optimisticMessage.text,
          attachment_ids: attachmentIds,
        })
        setMessages(prev => prev.map(m => (m.id === tempId ? sentMessage : m)))

        if (onAttachmentsSent && optimisticMessage.attachments.length > 0) {
          onAttachmentsSent(optimisticMessage.attachments)
        }
      }
    } catch (error) {
      setMessages(prev => prev.filter(m => m.id !== tempId))
      const message = error instanceof Error ? error.message : "Ошибка отправки сообщения"
      toast.error(message)
    } finally {
      setIsSending(false)
    }
  }

  const isSubmitDisabled =
    (!inputValue.trim() && files.length === 0) ||
    isSending ||
    files.some(f => f.status === "uploading")

  return { isSending, handleSendMessage, isSubmitDisabled }
}
