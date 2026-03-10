import { cn } from "@/lib/utils"
import type { KnowledgeGraph } from "../../lib/types"

type KnowledgeGraphTabProps = {
  graph: KnowledgeGraph | null
}

const nodeColors: Record<string, string> = {
  entity: "bg-primary/15 border-primary/40 text-primary",
  module: "bg-blue-500/15 border-blue-500/40 text-blue-600 dark:text-blue-400",
  actor: "bg-amber-500/15 border-amber-500/40 text-amber-600 dark:text-amber-400",
  requirement: "bg-emerald-500/15 border-emerald-500/40 text-emerald-600 dark:text-emerald-400",
}

const nodeLabels: Record<string, string> = {
  entity: "Сущность",
  module: "Модуль",
  actor: "Актор",
  requirement: "Требование",
}

export function KnowledgeGraphTab({ graph }: KnowledgeGraphTabProps) {
  if (!graph) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
        Граф не загружен
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full overflow-y-auto p-3 gap-4 chat-scrollbar">
      {/* Legend */}
      <div className="flex flex-wrap gap-2">
        {Object.entries(nodeLabels).map(([type, label]) => (
          <span
            key={type}
            className={cn(
              "inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium",
              nodeColors[type],
            )}
          >
            {label}
          </span>
        ))}
      </div>

      {/* Nodes */}
      <div>
        <p className="text-[11px] font-medium text-muted-foreground mb-2">
          Сущности ({graph.nodes.length})
        </p>
        <div className="flex flex-wrap gap-1.5">
          {graph.nodes.map(node => (
            <span
              key={node.id}
              className={cn(
                "inline-flex items-center rounded-md border px-2 py-1 text-[11px] font-medium transition-colors",
                nodeColors[node.type] ?? "bg-muted text-muted-foreground",
              )}
            >
              {node.label}
            </span>
          ))}
        </div>
      </div>

      {/* Edges */}
      <div>
        <p className="text-[11px] font-medium text-muted-foreground mb-2">
          Связи ({graph.edges.length})
        </p>
        <div className="flex flex-col gap-1">
          {graph.edges.map((edge, i) => {
            const from = graph.nodes.find(n => n.id === edge.from)
            const to = graph.nodes.find(n => n.id === edge.to)
            return (
              <div key={i} className="flex items-center gap-1.5 text-[11px]">
                <span className={cn("rounded px-1.5 py-0.5 border font-medium", nodeColors[from?.type ?? ""])}>
                  {from?.label}
                </span>
                <span className="text-muted-foreground">→ {edge.label} →</span>
                <span className={cn("rounded px-1.5 py-0.5 border font-medium", nodeColors[to?.type ?? ""])}>
                  {to?.label}
                </span>
              </div>
            )
          })}
        </div>
      </div>

      <div className="mt-auto pt-4 border-t">
        <p className="text-[10px] text-muted-foreground text-center">
          Визуализация графа будет доступна в следующей версии
        </p>
      </div>
    </div>
  )
}
