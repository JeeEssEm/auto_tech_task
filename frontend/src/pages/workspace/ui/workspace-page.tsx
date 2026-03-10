import { Loader2, FileText, CheckSquare, Box, BookOpen, Users, MessageSquareText } from "lucide-react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { useWorkspace } from "../hooks/use-workspace"
import type { WorkspaceTab } from "../lib/types"
import { CompletenessBar } from "./completeness-bar"
import { WorkspaceChat } from "./workspace-chat"
import { DocumentTab } from "./tabs/document-tab"
import { RequirementsTab } from "./tabs/requirements-tab"
import { EntitiesTab } from "./tabs/entities-tab"
import { GlossaryTab } from "./tabs/glossary-tab"
import { StakeholdersTab } from "./tabs/stakeholders-tab"

const MOCK_PROJECT_ID = "proj-001"

const tabs: { id: WorkspaceTab; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { id: "document", label: "Документ", icon: FileText },
  { id: "requirements", label: "Требования", icon: CheckSquare },
  { id: "entities", label: "Сущности", icon: Box },
  { id: "glossary", label: "Глоссарий", icon: BookOpen },
  { id: "stakeholders", label: "Стейкхолдеры", icon: Users },
]

export function WorkspacePage() {
  const ws = useWorkspace(MOCK_PROJECT_ID)

  if (ws.isLoading) {
    return (
      <div className="flex h-[calc(100vh-3.5rem)] items-center justify-center text-muted-foreground">
        <Loader2 className="size-8 animate-spin" />
      </div>
    )
  }

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)]">
      {/* Toolbar: tabs + progress + chat toggle */}
      <div className="flex items-center justify-between gap-4 border-b px-4 py-2 shrink-0">
        <div className="flex items-center gap-1">
          {tabs.map(tab => {
            const Icon = tab.icon
            return (
              <button
                key={tab.id}
                onClick={() => ws.setActiveTab(tab.id)}
                className={cn(
                  "flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors",
                  ws.activeTab === tab.id
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50",
                )}
              >
                <Icon className="size-3.5" />
                <span className="hidden sm:inline">{tab.label}</span>
              </button>
            )
          })}
        </div>

        <div className="flex items-center gap-3">
          {ws.project && <CompletenessBar project={ws.project} />}
          {!ws.chatOpen && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs gap-1.5"
              onClick={ws.toggleChat}
            >
              <MessageSquareText className="size-3.5" />
              <span className="hidden sm:inline">Ассистент</span>
            </Button>
          )}
        </div>
      </div>

      {/* Main content */}
      <div className="flex flex-1 min-h-0">
        {/* Tab content */}
        <div className="flex-1 min-w-0">
          {ws.activeTab === "document" && (
            <DocumentTab
              sections={ws.sections}
              onSectionFocus={ws.setChatContext}
            />
          )}
          {ws.activeTab === "requirements" && (
            <RequirementsTab requirements={ws.requirements} />
          )}
          {ws.activeTab === "entities" && (
            <EntitiesTab entities={ws.entities} />
          )}
          {ws.activeTab === "glossary" && (
            <GlossaryTab glossary={ws.glossary} />
          )}
          {ws.activeTab === "stakeholders" && (
            <StakeholdersTab stakeholders={ws.stakeholders} />
          )}
        </div>

        {/* Contextual chat */}
        {ws.chatOpen && (
          <div className="w-[320px] shrink-0">
            <WorkspaceChat
              messages={ws.chatMessages}
              context={ws.chatContext}
              onSend={ws.sendChatMessage}
              onClose={ws.toggleChat}
            />
          </div>
        )}
      </div>
    </div>
  )
}
