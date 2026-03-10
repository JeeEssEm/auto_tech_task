import { useState } from "react"
import { Box, Cpu, GitFork, Database } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import type { BusinessEntity, EntityType } from "../../lib/types"

type EntitiesTabProps = {
  entities: BusinessEntity[]
}

const typeConfig: Record<EntityType, { label: string; icon: React.ComponentType<{ className?: string }>; color: string }> = {
  system: { label: "Система", icon: Cpu, color: "text-violet-500 bg-violet-500/10" },
  module: { label: "Модуль", icon: Box, color: "text-blue-500 bg-blue-500/10" },
  process: { label: "Процесс", icon: GitFork, color: "text-amber-500 bg-amber-500/10" },
  data: { label: "Данные", icon: Database, color: "text-emerald-500 bg-emerald-500/10" },
}

type FilterKey = "all" | EntityType

export function EntitiesTab({ entities }: EntitiesTabProps) {
  const [filter, setFilter] = useState<FilterKey>("all")

  const filters: { key: FilterKey; label: string }[] = [
    { key: "all", label: "Все" },
    { key: "system", label: "Системы" },
    { key: "module", label: "Модули" },
    { key: "process", label: "Процессы" },
    { key: "data", label: "Данные" },
  ]

  const filtered = filter === "all" ? entities : entities.filter(e => e.type === filter)

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center gap-1.5 border-b px-4 py-3">
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

      {/* Cards */}
      <div className="flex-1 overflow-y-auto chat-scrollbar p-4">
        <div className="grid gap-3 sm:grid-cols-2">
          {filtered.map(entity => {
            const cfg = typeConfig[entity.type]
            const Icon = cfg.icon
            return (
              <Card key={entity.id} className="group hover:shadow-md transition-shadow">
                <CardContent className="p-4 space-y-2.5">
                  <div className="flex items-start gap-3">
                    <div className={cn("flex size-9 shrink-0 items-center justify-center rounded-lg", cfg.color)}>
                      <Icon className="size-4" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="text-sm font-semibold truncate">{entity.name}</h3>
                        <Badge variant="outline" className="text-[10px]">{cfg.label}</Badge>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                        {entity.description}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 text-[11px] text-muted-foreground pt-1 border-t border-border/50">
                    <span>Источник: {entity.source}</span>
                    <span>·</span>
                    <span>Разделы: {entity.relatedSections.join(", ")}</span>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      </div>
    </div>
  )
}
