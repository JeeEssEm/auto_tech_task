import { useState } from "react"
import { Check, ChevronDown, ChevronRight, Circle, Clock, Pencil, RefreshCw, X } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import type { DocumentSection, SectionStatus } from "../../lib/types"

type DocumentTabProps = {
  sections: DocumentSection[]
  onSectionFocus: (sectionNumber: string) => void
}

const statusConfig: Record<SectionStatus, { label: string; color: string; icon: React.ComponentType<{ className?: string }> }> = {
  empty: { label: "Пусто", color: "text-muted-foreground", icon: Circle },
  draft: { label: "Черновик", color: "text-amber-500", icon: Clock },
  review: { label: "Ревью", color: "text-blue-500", icon: RefreshCw },
  approved: { label: "Готово", color: "text-emerald-500", icon: Check },
}

export function DocumentTab({ sections, onSectionFocus }: DocumentTabProps) {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(["s3"]))
  const [editingId, setEditingId] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>("s2")

  const toggle = (id: string) => {
    setExpandedSections(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const allFlat: DocumentSection[] = []
  for (const s of sections) {
    allFlat.push(s)
    if (s.children) allFlat.push(...s.children)
  }
  const selected = allFlat.find(s => s.id === selectedId) ?? null

  return (
    <div className="flex h-full">
      {/* TOC sidebar */}
      <div className="w-[260px] shrink-0 border-r overflow-y-auto chat-scrollbar p-3 space-y-0.5">
        {sections.map(section => {
          const StatusIcon = statusConfig[section.status].icon
          const hasChildren = section.children && section.children.length > 0
          const isExpanded = expandedSections.has(section.id)

          return (
            <div key={section.id}>
              <button
                onClick={() => {
                  if (hasChildren) toggle(section.id)
                  setSelectedId(section.id)
                  onSectionFocus(section.number)
                }}
                className={cn(
                  "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors hover:bg-accent/50",
                  selectedId === section.id && "bg-accent text-accent-foreground",
                )}
              >
                {hasChildren ? (
                  isExpanded ? <ChevronDown className="size-3.5 shrink-0 text-muted-foreground" /> : <ChevronRight className="size-3.5 shrink-0 text-muted-foreground" />
                ) : (
                  <span className="w-3.5" />
                )}
                <StatusIcon className={cn("size-3 shrink-0", statusConfig[section.status].color)} />
                <span className="text-muted-foreground mr-1">{section.number}</span>
                <span className="truncate">{section.title}</span>
              </button>
              {hasChildren && isExpanded && (
                <div className="ml-4 pl-2 border-l border-border/50 space-y-0.5 mt-0.5">
                  {section.children!.map(child => {
                    const ChildIcon = statusConfig[child.status].icon
                    return (
                      <button
                        key={child.id}
                        onClick={() => {
                          setSelectedId(child.id)
                          onSectionFocus(child.number)
                        }}
                        className={cn(
                          "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors hover:bg-accent/50",
                          selectedId === child.id && "bg-accent text-accent-foreground",
                        )}
                      >
                        <ChildIcon className={cn("size-3 shrink-0", statusConfig[child.status].color)} />
                        <span className="text-muted-foreground mr-1">{child.number}</span>
                        <span className="truncate">{child.title}</span>
                      </button>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Content area */}
      <div className="flex-1 min-w-0 overflow-y-auto chat-scrollbar p-6">
        {selected ? (
          <div className="max-w-3xl">
            {/* Section header */}
            <div className="flex items-start justify-between gap-4 mb-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm text-muted-foreground font-mono">§{selected.number}</span>
                  <Badge
                    variant="outline"
                    className={cn("text-[10px]", statusConfig[selected.status].color)}
                  >
                    {statusConfig[selected.status].label}
                  </Badge>
                </div>
                <h2 className="text-xl font-semibold">{selected.title}</h2>
              </div>
              <div className="flex gap-1.5 shrink-0">
                {editingId === selected.id ? (
                  <>
                    <Button size="sm" variant="default" className="h-7 text-xs gap-1" onClick={() => setEditingId(null)}>
                      <Check className="size-3" /> Сохранить
                    </Button>
                    <Button size="sm" variant="ghost" className="h-7 text-xs" onClick={() => setEditingId(null)}>
                      <X className="size-3" />
                    </Button>
                  </>
                ) : (
                  <>
                    <Button size="sm" variant="outline" className="h-7 text-xs gap-1" onClick={() => setEditingId(selected.id)}>
                      <Pencil className="size-3" /> Редактировать
                    </Button>
                    <Button size="sm" variant="outline" className="h-7 text-xs gap-1">
                      <RefreshCw className="size-3" /> Перегенерировать
                    </Button>
                  </>
                )}
              </div>
            </div>

            {/* Content */}
            {selected.content ? (
              editingId === selected.id ? (
                <textarea
                  className="w-full min-h-[300px] rounded-lg border bg-background p-4 text-sm leading-relaxed font-mono resize-y focus:outline-none focus:ring-1 focus:ring-ring"
                  defaultValue={selected.content}
                />
              ) : (
                <div className="prose prose-sm dark:prose-invert max-w-none">
                  {selected.content.split("\n").map((line, i) => {
                    if (line.startsWith("**") && line.endsWith("**")) {
                      return <p key={i} className="font-semibold text-sm text-foreground mt-3 first:mt-0">{line.replace(/\*\*/g, "")}</p>
                    }
                    if (line.startsWith("- ")) {
                      return <div key={i} className="flex gap-2 text-sm text-foreground/80 pl-2 py-0.5"><span className="text-muted-foreground">•</span>{line.slice(2)}</div>
                    }
                    if (line.trim() === "") return <div key={i} className="h-2" />
                    return <p key={i} className="text-sm text-foreground/80 leading-relaxed">{line}</p>
                  })}
                </div>
              )
            ) : (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <Circle className="size-10 text-muted-foreground/30 mb-3" />
                <p className="text-sm text-muted-foreground mb-3">Раздел пока пуст</p>
                <div className="flex gap-2">
                  <Button size="sm" variant="default" className="text-xs gap-1">
                    <RefreshCw className="size-3" /> Сгенерировать
                  </Button>
                  <Button size="sm" variant="outline" className="text-xs gap-1" onClick={() => setEditingId(selected.id)}>
                    <Pencil className="size-3" /> Написать вручную
                  </Button>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
            Выберите раздел слева
          </div>
        )}
      </div>
    </div>
  )
}
