import { useCallback, useEffect, useState } from "react"

import type {
  BusinessEntity,
  DocumentSection,
  GlossaryTerm,
  Requirement,
  Stakeholder,
  WorkspaceChatMessage,
  WorkspaceProject,
  WorkspaceTab,
} from "../lib/types"
import { workspaceMockApi } from "../api/mock-workspace-api"

export function useWorkspace(projectId: string | undefined) {
  const [activeTab, setActiveTab] = useState<WorkspaceTab>("document")
  const [chatOpen, setChatOpen] = useState(true)
  const [isLoading, setIsLoading] = useState(true)

  const [project, setProject] = useState<WorkspaceProject | null>(null)
  const [sections, setSections] = useState<DocumentSection[]>([])
  const [requirements, setRequirements] = useState<Requirement[]>([])
  const [entities, setEntities] = useState<BusinessEntity[]>([])
  const [glossary, setGlossary] = useState<GlossaryTerm[]>([])
  const [stakeholders, setStakeholders] = useState<Stakeholder[]>([])
  const [chatMessages, setChatMessages] = useState<WorkspaceChatMessage[]>([])

  const [chatContext, setChatContext] = useState<string | null>(null)

  useEffect(() => {
    if (!projectId) return
    setIsLoading(true)

    Promise.all([
      workspaceMockApi.getProject(projectId),
      workspaceMockApi.getSections(projectId),
      workspaceMockApi.getRequirements(projectId),
      workspaceMockApi.getEntities(projectId),
      workspaceMockApi.getGlossary(projectId),
      workspaceMockApi.getStakeholders(projectId),
      workspaceMockApi.getChatMessages(projectId),
    ]).then(([proj, sec, req, ent, gls, stk, msgs]) => {
      setProject(proj)
      setSections(sec)
      setRequirements(req)
      setEntities(ent)
      setGlossary(gls)
      setStakeholders(stk)
      setChatMessages(msgs)
      setIsLoading(false)
    })
  }, [projectId])

  const toggleChat = useCallback(() => setChatOpen(prev => !prev), [])

  const sendChatMessage = useCallback((text: string) => {
    const userMsg: WorkspaceChatMessage = {
      id: Date.now(),
      sender: "user",
      text,
      created_at: new Date().toISOString(),
    }
    setChatMessages(prev => [...prev, userMsg])

    // Simulate assistant response
    setTimeout(() => {
      const reply: WorkspaceChatMessage = {
        id: Date.now() + 1,
        sender: "assistant",
        text: "Принял. Обновил соответствующий раздел документа.",
        created_at: new Date().toISOString(),
      }
      setChatMessages(prev => [...prev, reply])
    }, 1200)
  }, [])

  return {
    activeTab,
    setActiveTab,
    chatOpen,
    toggleChat,
    isLoading,
    project,
    sections,
    requirements,
    entities,
    glossary,
    stakeholders,
    chatMessages,
    chatContext,
    setChatContext,
    sendChatMessage,
  }
}
