import { useCallback, useEffect, useMemo, useRef, useState } from "react"

import type { Attachment } from "@/shared/api/chat-service"
import type { ParsingStatus, WsEventMap } from "@/shared/ws/types"
import type { ParsingEntry } from "../lib/types"

const SUCCESS_DISMISS_DELAY = 6000
const FAILED_DISPLAY_DELAY = 3000

type UseParsingStatusOptions = {
  onFailed?: (attachmentId: string, fileName: string) => void
  onFailedCleanup?: (attachmentId: string) => void
  onSuccess?: () => void
}

export function useParsingStatus(options?: UseParsingStatusOptions) {
  const [entries, setEntries] = useState<ParsingEntry[]>([])
  const namesRef = useRef(new Map<string, string>())
  const dismissTimers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map())
  const onFailedRef = useRef(options?.onFailed)
  const onFailedCleanupRef = useRef(options?.onFailedCleanup)
  const onSuccessRef = useRef(options?.onSuccess)

  useEffect(() => {
    onFailedRef.current = options?.onFailed
    onFailedCleanupRef.current = options?.onFailedCleanup
    onSuccessRef.current = options?.onSuccess
  })

  // Quick lookup: attachment_id → ParsingStatus
  const statusMap = useMemo<Map<string, ParsingStatus>>(
    () => new Map(entries.map(e => [e.attachmentId, e.status])),
    [entries],
  )

  // Clean up timers on unmount
  useEffect(() => {
    const timers = dismissTimers.current
    return () => {
      timers.forEach(t => clearTimeout(t))
      timers.clear()
    }
  }, [])

  const scheduleDismiss = useCallback((attachmentId: string) => {
    const existing = dismissTimers.current.get(attachmentId)
    if (existing) clearTimeout(existing)

    const timer = setTimeout(() => {
      setEntries(prev => prev.filter(e => e.attachmentId !== attachmentId))
      dismissTimers.current.delete(attachmentId)
    }, SUCCESS_DISMISS_DELAY)

    dismissTimers.current.set(attachmentId, timer)
  }, [])

  // Register attachment_id → fileName at upload time (earliest known mapping)
  const registerName = useCallback((attachmentId: string, fileName: string) => {
    namesRef.current.set(attachmentId, fileName)
  }, [])

  // Called after message is sent — creates tracking entries for each attachment
  const trackAttachments = useCallback((attachments: Attachment[]) => {
    setEntries(prev => {
      const newEntries = [...prev]
      for (const att of attachments) {
        namesRef.current.set(att.key, att.file_name)
        const idx = newEntries.findIndex(e => e.attachmentId === att.key)
        if (idx >= 0) {
          newEntries[idx] = { ...newEntries[idx], fileName: att.file_name }
        } else {
          newEntries.push({
            attachmentId: att.key,
            fileName: att.file_name,
            status: "PENDING",
          })
        }
      }
      return newEntries
    })
  }, [])

  // WS event handler
  const handleParsingStatus = useCallback((data: WsEventMap["PARSING_STATUS"]) => {
    const fileName = namesRef.current.get(data.attachment_id) ?? data.attachment_id.slice(0, 8) + "…"

    if (data.status === "FAILED") {
      // Show FAILED state (red highlight) immediately
      setEntries(prev => {
        const idx = prev.findIndex(e => e.attachmentId === data.attachment_id)
        if (idx >= 0) {
          const updated = [...prev]
          updated[idx] = { ...updated[idx], status: "FAILED" }
          return updated
        }
        return [...prev, { attachmentId: data.attachment_id, fileName, status: "FAILED" }]
      })

      // Toast immediately
      onFailedRef.current?.(data.attachment_id, fileName)

      // Remove entry + attachment after delay so user sees the red highlight
      const existing = dismissTimers.current.get(data.attachment_id)
      if (existing) clearTimeout(existing)

      const timer = setTimeout(() => {
        setEntries(prev => prev.filter(e => e.attachmentId !== data.attachment_id))
        onFailedCleanupRef.current?.(data.attachment_id)
        dismissTimers.current.delete(data.attachment_id)
      }, FAILED_DISPLAY_DELAY)

      dismissTimers.current.set(data.attachment_id, timer)
      return
    }

    setEntries(prev => {
      const idx = prev.findIndex(e => e.attachmentId === data.attachment_id)
      if (idx >= 0) {
        const updated = [...prev]
        updated[idx] = { ...updated[idx], status: data.status }
        return updated
      }
      return [
        ...prev,
        { attachmentId: data.attachment_id, fileName, status: data.status },
      ]
    })

    if (data.status === "SUCCESS") {
      scheduleDismiss(data.attachment_id)
      onSuccessRef.current?.()
    }
  }, [scheduleDismiss])

  const dismissEntry = useCallback((attachmentId: string) => {
    setEntries(prev => prev.filter(e => e.attachmentId !== attachmentId))
    const timer = dismissTimers.current.get(attachmentId)
    if (timer) {
      clearTimeout(timer)
      dismissTimers.current.delete(attachmentId)
    }
  }, [])

  return { entries, statusMap, registerName, trackAttachments, handleParsingStatus, dismissEntry }
}
