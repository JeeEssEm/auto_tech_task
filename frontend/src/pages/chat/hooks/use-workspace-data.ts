import { useCallback, useEffect, useState } from "react"

import { chatApi } from "@/shared/api/chat-service"
import type { GenerationRun, ParsedAttachmentDetail } from "@/shared/api/chat-service"
import { tzApi } from "@/shared/api/tz-service"
import type { KnowledgeGraph, KnowledgeGraphFact, ParsedAttachment, TZResult } from "../lib/types"

export type WorkspaceTab = "document" | "files" | "graph"

function buildKnowledgeGraph(facts: KnowledgeGraphFact[]): KnowledgeGraph {
  const nodes = new Map<string, KnowledgeGraph["nodes"][number]>()
  const edges = new Map<string, KnowledgeGraph["edges"][number]>()

  for (const fact of facts) {
    const scopeLabel = fact.scope?.trim() || "(без scope)"
    const propertyLabel = fact.property?.trim() || "(без property)"
    const valueLabel = fact.value?.trim() || "(без value)"

    const scopeId = `scope:${scopeLabel}`
    const propertyId = `property:${scopeLabel}:${propertyLabel}`
    const valueId = `value:${fact.id}`

    if (!nodes.has(scopeId)) {
      nodes.set(scopeId, {
        id: scopeId,
        label: scopeLabel,
        type: "scope",
      })
    }

    if (!nodes.has(propertyId)) {
      nodes.set(propertyId, {
        id: propertyId,
        label: propertyLabel,
        type: "property",
      })
    }

    nodes.set(valueId, {
      id: valueId,
      label: valueLabel,
      type: "value",
      status: fact.status,
    })

    const scopeToProperty = `${scopeId}->${propertyId}`
    if (!edges.has(scopeToProperty)) {
      edges.set(scopeToProperty, {
        from: scopeId,
        to: propertyId,
        label: "имеет",
        weight: 0,
      })
    }
    const scopeEdge = edges.get(scopeToProperty)
    if (scopeEdge) {
      scopeEdge.weight = (scopeEdge.weight ?? 0) + 1
    }

    edges.set(`${propertyId}->${valueId}`, {
      from: propertyId,
      to: valueId,
      label: "значение",
      weight: 1,
    })
  }

  return {
    nodes: Array.from(nodes.values()),
    edges: Array.from(edges.values()),
  }
}

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
  const [graphFacts, setGraphFacts] = useState<KnowledgeGraphFact[]>([])
  const [focusedFactId, setFocusedFactId] = useState<string | null>(null)

  // Load workspace data
  useEffect(() => {
    if (!chatId) return
    setIsLoading(true)

    const controller = new AbortController()

    const loadData = async () => {
      // Parsed files: try real API, fallback to empty list
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
        parsedFiles = []
      }

      // Generations: try real API, fallback to empty
      let gens: GenerationRun[]
      try {
        gens = await chatApi.getGenerations(chatId, controller.signal)
      } catch {
        gens = []
      }

      // Knowledge graph facts: real API, fallback to empty
      let facts: KnowledgeGraphFact[]
      try {
        const response = await tzApi.getKnowledgeGraphFacts(chatId)
        facts = response.facts
      } catch {
        facts = []
      }

      if (!controller.signal.aborted) {
        setAttachments(parsedFiles)
        setSelectedAttachment(parsedFiles[0] ?? null)
        setGenerations(gens)
        setSelectedGeneration(gens[gens.length - 1] ?? null)
        setGraphFacts(facts)
        setGraph(buildKnowledgeGraph(facts))
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

  const refreshGraph = useCallback(async () => {
    if (!chatId) return
    try {
      const response = await tzApi.getKnowledgeGraphFacts(chatId)
      setGraphFacts(response.facts)
      setGraph(buildKnowledgeGraph(response.facts))
    } catch {
      // silent
    }
  }, [chatId])

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
    graphFacts,
    focusedFactId,
    setFocusedFactId,
    refreshGenerations,
    refreshContent,
    refreshAttachments,
    refreshGraph,
  }
}
