import { useEffect, useState } from "react"

import { panelMockApi } from "../api/mock-panel-api"
import type { GeneratedTechnicalTask, KnowledgeGraph, ParsedAttachment } from "../lib/types"

export type PanelTab = "files" | "tasks" | "graph"

export function useChatPanel(chatId: string | undefined) {
  const [activeTab, setActiveTab] = useState<PanelTab>("files")
  const [isOpen, setIsOpen] = useState(false)

  const [attachments, setAttachments] = useState<ParsedAttachment[]>([])
  const [selectedAttachment, setSelectedAttachment] = useState<ParsedAttachment | null>(null)

  const [tasks, setTasks] = useState<GeneratedTechnicalTask[]>([])
  const [selectedTask, setSelectedTask] = useState<GeneratedTechnicalTask | null>(null)

  const [graph, setGraph] = useState<KnowledgeGraph | null>(null)

  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (!chatId || !isOpen) return

    setIsLoading(true)
    const controller = new AbortController()

    Promise.all([
      panelMockApi.getParsedAttachments(chatId),
      panelMockApi.getGeneratedTasks(chatId),
      panelMockApi.getKnowledgeGraph(chatId),
    ])
      .then(([atts, tks, gr]) => {
        if (controller.signal.aborted) return
        setAttachments(atts)
        setSelectedAttachment(atts[0] ?? null)
        setTasks(tks)
        setSelectedTask(tks[tks.length - 1] ?? null)
        setGraph(gr)
      })
      .catch(err => {
        if (err.name !== "AbortError") console.error(err)
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsLoading(false)
      })

    return () => controller.abort()
  }, [chatId, isOpen])

  const toggle = () => setIsOpen(prev => !prev)

  return {
    isOpen,
    toggle,
    activeTab,
    setActiveTab,
    isLoading,
    attachments,
    selectedAttachment,
    setSelectedAttachment,
    tasks,
    selectedTask,
    setSelectedTask,
    graph,
  }
}
