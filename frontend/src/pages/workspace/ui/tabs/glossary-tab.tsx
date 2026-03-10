import { useState } from "react"
import { BookOpen, Search } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import type { GlossaryTerm } from "../../lib/types"

type GlossaryTabProps = {
  glossary: GlossaryTerm[]
}

export function GlossaryTab({ glossary }: GlossaryTabProps) {
  const [search, setSearch] = useState("")
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const filtered = search
    ? glossary.filter(g =>
        g.term.toLowerCase().includes(search.toLowerCase()) ||
        g.variants.some(v => v.toLowerCase().includes(search.toLowerCase()))
      )
    : glossary

  return (
    <div className="flex flex-col h-full">
      {/* Search */}
      <div className="flex items-center gap-2 border-b px-4 py-3">
        <Search className="size-4 text-muted-foreground shrink-0" />
        <input
          type="text"
          placeholder="Поиск по терминам…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
        />
        <span className="text-xs text-muted-foreground">{filtered.length} терминов</span>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto chat-scrollbar divide-y">
        {filtered.map(term => (
          <button
            key={term.id}
            onClick={() => setExpandedId(prev => prev === term.id ? null : term.id)}
            className="w-full text-left px-4 py-3 hover:bg-accent/30 transition-colors"
          >
            <div className="flex items-start gap-3">
              <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary mt-0.5">
                <BookOpen className="size-4" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-semibold">{term.term}</span>
                  {term.variants.slice(0, 2).map(v => (
                    <Badge key={v} variant="outline" className="text-[10px]">{v}</Badge>
                  ))}
                  {term.variants.length > 2 && (
                    <span className="text-[10px] text-muted-foreground">+{term.variants.length - 2}</span>
                  )}
                </div>
                <p className="text-sm text-muted-foreground leading-relaxed mt-1">
                  {term.definition}
                </p>
                {expandedId === term.id && (
                  <div className="mt-2 space-y-1.5 text-xs">
                    {term.variants.length > 0 && (
                      <div>
                        <span className="text-muted-foreground">Варианты: </span>
                        <span className="text-foreground/80">{term.variants.join(", ")}</span>
                      </div>
                    )}
                    <div>
                      <span className="text-muted-foreground">Используется в разделах: </span>
                      <span className="text-foreground/80">{term.usedInSections.join(", ")}</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
