import { useState } from "react"
import { Filter } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import type { Requirement, RequirementPriority, RequirementStatus, RequirementType } from "../../lib/types"

type RequirementsTabProps = {
  requirements: Requirement[]
}

const priorityConfig: Record<RequirementPriority, { label: string; className: string }> = {
  must: { label: "Must", className: "bg-red-500/10 text-red-500 border-red-500/20" },
  should: { label: "Should", className: "bg-amber-500/10 text-amber-500 border-amber-500/20" },
  could: { label: "Could", className: "bg-blue-500/10 text-blue-500 border-blue-500/20" },
  wont: { label: "Won't", className: "bg-muted text-muted-foreground" },
}

const typeLabels: Record<RequirementType, string> = {
  functional: "Функциональное",
  "non-functional": "Нефункциональное",
  constraint: "Ограничение",
}

const statusLabels: Record<RequirementStatus, { label: string; className: string }> = {
  extracted: { label: "Извлечено", className: "bg-muted text-muted-foreground" },
  confirmed: { label: "Подтверждено", className: "bg-amber-500/10 text-amber-500" },
  in_tz: { label: "В ТЗ", className: "bg-emerald-500/10 text-emerald-500" },
}

type FilterKey = "all" | RequirementType

export function RequirementsTab({ requirements }: RequirementsTabProps) {
  const [filter, setFilter] = useState<FilterKey>("all")
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const filters: { key: FilterKey; label: string }[] = [
    { key: "all", label: "Все" },
    { key: "functional", label: "Функциональные" },
    { key: "non-functional", label: "Нефункциональные" },
    { key: "constraint", label: "Ограничения" },
  ]

  const filtered = filter === "all" ? requirements : requirements.filter(r => r.type === filter)

  const counts = {
    must: filtered.filter(r => r.priority === "must").length,
    should: filtered.filter(r => r.priority === "should").length,
    could: filtered.filter(r => r.priority === "could").length,
  }

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-3 border-b px-4 py-3">
        <div className="flex items-center gap-1.5">
          <Filter className="size-3.5 text-muted-foreground" />
          {filters.map(f => (
            <Button
              key={f.key}
              size="sm"
              variant={filter === f.key ? "secondary" : "ghost"}
              className="h-7 text-xs"
              onClick={() => setFilter(f.key)}
            >
              {f.label}
            </Button>
          ))}
        </div>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <span className="text-red-500">Must: {counts.must}</span>
          <span className="text-amber-500">Should: {counts.should}</span>
          <span className="text-blue-500">Could: {counts.could}</span>
        </div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto chat-scrollbar">
        <div className="divide-y">
          {filtered.map(req => (
            <button
              key={req.id}
              onClick={() => setExpandedId(prev => prev === req.id ? null : req.id)}
              className="w-full text-left px-4 py-3 hover:bg-accent/30 transition-colors"
            >
              <div className="flex items-start gap-3">
                <Badge variant="outline" className={cn("text-[10px] shrink-0 mt-0.5", priorityConfig[req.priority].className)}>
                  {priorityConfig[req.priority].label}
                </Badge>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-sm font-medium truncate">{req.title}</span>
                    <Badge variant="outline" className={cn("text-[10px]", statusLabels[req.status].className)}>
                      {statusLabels[req.status].label}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <span>{typeLabels[req.type]}</span>
                    <span>·</span>
                    <span>{req.module}</span>
                    <span>·</span>
                    <span className="truncate">{req.source}</span>
                  </div>
                  {expandedId === req.id && (
                    <p className="mt-2 text-sm text-foreground/80 leading-relaxed">
                      {req.description}
                    </p>
                  )}
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
