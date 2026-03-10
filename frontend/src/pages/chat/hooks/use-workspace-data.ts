import { useCallback, useEffect, useState } from "react"

import { chatApi } from "@/shared/api/chat-service"
import type { GenerationRun, ParsedAttachmentDetail } from "@/shared/api/chat-service"
import { panelMockApi } from "../api/mock-panel-api"
import type { KnowledgeGraph, ParsedAttachment, TZResult } from "../lib/types"

export type WorkspaceTab = "document" | "files" | "graph"

export function useWorkspaceData(chatId: string | undefined) {
  const [activeTab, setActiveTab] = useState<WorkspaceTab>("document")
  const [isLoading, setIsLoading] = useState(false)

  // Parsed files
  const [attachments, setAttachments] = useState<ParsedAttachment[]>([])
  const [selectedAttachment, setSelectedAttachment] = useState<ParsedAttachment | null>(null)

  // Generation runs (TZ versions)
  const [generations, setGenerations] = useState<GenerationRun[]>([])
  const [selectedGeneration, setSelectedGeneration] = useState<GenerationRun | null>(null)
  const [generationContent, setGenerationContent] = useState<TZResult | null>(null)
  const [isContentLoading, setIsContentLoading] = useState(false)

  // Knowledge graph (still mock)
  const [graph, setGraph] = useState<KnowledgeGraph | null>(null)

  // Load workspace data
  useEffect(() => {
    if (!chatId) return
    setIsLoading(true)

    const controller = new AbortController()

    const loadData = async () => {
      // Parsed files: try real API, fallback to mock
      let parsedFiles: ParsedAttachment[]
      try {
        const real = await chatApi.getParsedAttachments(chatId, controller.signal)
        parsedFiles = real.map((f: ParsedAttachmentDetail) => ({
          key: f.key,
          file_name: f.file_name,
          file_type: f.file_type,
          file_size: f.file_size,
          transcript: f.transcript,
        }))
      } catch {
        parsedFiles = await panelMockApi.getParsedAttachments(chatId)
      }

      // Generations: try real API, fallback to empty
      let gens: GenerationRun[]
      try {
        gens = await chatApi.getGenerations(chatId, controller.signal)
      } catch {
        gens = []
      }

      // Graph: mock for now
      let gr: KnowledgeGraph | null
      try {
        gr = await panelMockApi.getKnowledgeGraph(chatId)
      } catch {
        gr = null
      }

      if (!controller.signal.aborted) {
        setAttachments(parsedFiles)
        setSelectedAttachment(parsedFiles[0] ?? null)
        setGenerations(gens)
        setSelectedGeneration(gens[gens.length - 1] ?? null)
        setGraph(gr)
        setIsLoading(false)
      }
    }

    loadData()
    return () => controller.abort()
  }, [chatId])

  // Load content when selected generation changes
  useEffect(() => {
    if (!chatId || !selectedGeneration?.result_key) {
      setGenerationContent(null)
      return
    }

    setIsContentLoading(true)
    const controller = new AbortController()

    chatApi.getGenerationContent(chatId, selectedGeneration.result_key, controller.signal)
      .then(raw => {
        if (!controller.signal.aborted) {
          setGenerationContent(raw as TZResult)
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setGenerationContent(null)
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setIsContentLoading(false)
        }
      })

    return () => controller.abort()
  }, [chatId, selectedGeneration])

  // Reload generations (called after LLM_ANSWER)
  const refreshGenerations = useCallback(async () => {
    if (!chatId) return
    try {
      const gens = await chatApi.getGenerations(chatId)
      setGenerations(gens)
      if (gens.length > 0) {
        setSelectedGeneration(gens[gens.length - 1])
      }
    } catch {
      // silent
    }
  }, [chatId])

  // Reload content for current generation (called after manual edits)
  const refreshContent = useCallback(async () => {
    if (!chatId || !selectedGeneration?.result_key) return
    try {
      const raw = await chatApi.getGenerationContent(chatId, selectedGeneration.result_key)
      setGenerationContent(raw as TZResult)
    } catch {
      // silent
    }
  }, [chatId, selectedGeneration])

  // Reload parsed files (called after PARSING_STATUS SUCCESS)
  const refreshAttachments = useCallback(async () => {
    if (!chatId) return
    try {
      const real = await chatApi.getParsedAttachments(chatId)
      const files = real.map((f: ParsedAttachmentDetail) => ({
        key: f.key,
        file_name: f.file_name,
        file_type: f.file_type,
        file_size: f.file_size,
        transcript: f.transcript,
      }))
      setAttachments(files)
      if (!selectedAttachment && files.length > 0) {
        setSelectedAttachment(files[0])
      }
    } catch {
      // silent
    }
  }, [chatId, selectedAttachment])

  return {
    activeTab,
    setActiveTab,
    isLoading,
    attachments,
    selectedAttachment,
    setSelectedAttachment,
    generations,
    selectedGeneration,
    setSelectedGeneration,
    generationContent,
    isContentLoading,
    graph,
    refreshGenerations,
    refreshContent,
    refreshAttachments,
  }
}
