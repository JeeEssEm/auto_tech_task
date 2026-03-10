import { FileText, GitBranch, Loader2, ScrollText, X } from "lucide-react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import type { PanelTab } from "../../hooks/use-chat-panel"
import type { GeneratedTechnicalTask, KnowledgeGraph, ParsedAttachment } from "../../lib/types"
import { AttachmentsTab } from "./attachments-tab"
import { GeneratedTzTab } from "./generated-tz-tab"
import { KnowledgeGraphTab } from "./knowledge-graph-tab"

type ChatSidePanelProps = {
  activeTab: PanelTab
  onTabChange: (tab: PanelTab) => void
  onClose: () => void
  isLoading: boolean
  attachments: ParsedAttachment[]
  selectedAttachment: ParsedAttachment | null
  onSelectAttachment: (att: ParsedAttachment) => void
  tasks: GeneratedTechnicalTask[]
  selectedTask: GeneratedTechnicalTask | null
  onSelectTask: (task: GeneratedTechnicalTask) => void
  graph: KnowledgeGraph | null
}

const tabs: { id: PanelTab; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { id: "files", label: "Файлы", icon: FileText },
  { id: "tasks", label: "ТЗ", icon: ScrollText },
  { id: "graph", label: "Граф", icon: GitBranch },
]

export function ChatSidePanel({
  activeTab,
  onTabChange,
  onClose,
  isLoading,
  attachments,
  selectedAttachment,
  onSelectAttachment,
  tasks,
  selectedTask,
  onSelectTask,
  graph,
}: ChatSidePanelProps) {
  return (
    <div className="flex flex-col h-full border-l bg-background">
      {/* Header */}
      <div className="flex items-center justify-between border-b px-3 py-2">
        <div className="flex gap-1">
          {tabs.map(tab => {
            const Icon = tab.icon
            return (
              <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                className={cn(
                  "flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors",
                  activeTab === tab.id
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50",
                )}
              >
                <Icon className="size-3.5" />
                {tab.label}
              </button>
            )
          })}
        </div>
        <Button variant="ghost" size="icon" className="size-7" onClick={onClose}>
          <X className="size-4" />
        </Button>
      </div>

      {/* Content */}
      <div className="flex-1 min-h-0">
        {isLoading ? (
          <div className="flex h-full items-center justify-center text-muted-foreground">
            <Loader2 className="size-6 animate-spin" />
          </div>
        ) : (
          <>
            {activeTab === "files" && (
              <AttachmentsTab
                attachments={attachments}
                selected={selectedAttachment}
                onSelect={onSelectAttachment}
              />
            )}
            {activeTab === "tasks" && (
              <GeneratedTzTab
                tasks={tasks}
                selected={selectedTask}
                onSelect={onSelectTask}
              />
            )}
            {activeTab === "graph" && (
              <KnowledgeGraphTab graph={graph} />
            )}
          </>
        )}
      </div>
    </div>
  )
}
