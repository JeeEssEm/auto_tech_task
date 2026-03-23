import { useEffect, useMemo, useRef } from "react"
import cytoscape, { type Core, type ElementDefinition } from "cytoscape"

import { cn } from "@/lib/utils"
import type { KnowledgeGraph, KnowledgeGraphFact } from "../../lib/types"

type KnowledgeGraphTabProps = {
  graph: KnowledgeGraph | null
  facts: KnowledgeGraphFact[]
  focusedFactId?: string | null
}

const valueStatusPalette: Record<string, string> = {
  accepted: "bg-emerald-500/20 text-emerald-700 dark:text-emerald-300",
  pending: "bg-amber-500/20 text-amber-700 dark:text-amber-300",
  rejected: "bg-rose-500/20 text-rose-700 dark:text-rose-300",
}

function normalizeStatus(status?: string): string {
  return String(status ?? "").trim().toLowerCase()
}

export function KnowledgeGraphTab({ graph, facts, focusedFactId }: KnowledgeGraphTabProps) {
  const graphRef = useRef<HTMLDivElement | null>(null)
  const cyRef = useRef<Core | null>(null)

  const stats = useMemo(() => {
    if (!graph) return { scopes: 0, properties: 0, values: 0 }
    return {
      scopes: graph.nodes.filter(n => n.type === "scope").length,
      properties: graph.nodes.filter(n => n.type === "property").length,
      values: graph.nodes.filter(n => n.type === "value").length,
    }
  }, [graph])

  const elements = useMemo<ElementDefinition[]>(() => {
    if (!graph) return []

    const nodeElements: ElementDefinition[] = graph.nodes.map(node => ({
      data: {
        id: node.id,
        label: node.label,
        nodeType: node.type,
        status: normalizeStatus(node.status),
      },
    }))

    const edgeElements: ElementDefinition[] = graph.edges.map((edge, index) => ({
      data: {
        id: `edge-${index}-${edge.from}-${edge.to}`,
        source: edge.from,
        target: edge.to,
        label: edge.label,
        weight: edge.weight ?? 1,
      },
    }))

    return [...nodeElements, ...edgeElements]
  }, [graph])

  useEffect(() => {
    if (!graphRef.current || !graph || elements.length === 0) {
      if (cyRef.current) {
        cyRef.current.destroy()
        cyRef.current = null
      }
      return
    }

    const cy = cytoscape({
      container: graphRef.current,
      elements,
      minZoom: 0.45,
      maxZoom: 2.25,
      wheelSensitivity: 0.2,
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            shape: "round-rectangle",
            width: 130,
            height: 42,
            "font-size": 10,
            "text-wrap": "wrap",
            "text-max-width": "110px",
            "text-halign": "center",
            "text-valign": "center",
            color: "#0f172a",
            "border-width": 1,
            "border-color": "#cbd5e1",
            "background-color": "#f8fafc",
          },
        },
        {
          selector: 'node[nodeType = "scope"]',
          style: {
            "background-color": "#e0f2fe",
            "border-color": "#38bdf8",
          },
        },
        {
          selector: 'node[nodeType = "property"]',
          style: {
            "background-color": "#fef3c7",
            "border-color": "#f59e0b",
          },
        },
        {
          selector: 'node[nodeType = "value"]',
          style: {
            "background-color": "#dcfce7",
            "border-color": "#4ade80",
          },
        },
        {
          selector: "node.focused",
          style: {
            "border-color": "#2563eb",
            "border-width": 3,
            "overlay-color": "#2563eb",
            "overlay-opacity": 0.08,
            "overlay-padding": 8,
          },
        },
        {
          selector: "edge",
          style: {
            width: "mapData(weight, 1, 6, 1.2, 3.4)",
            "line-color": "#94a3b8",
            "target-arrow-color": "#94a3b8",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            label: "data(label)",
            "font-size": 9,
            color: "#64748b",
            "text-background-opacity": 1,
            "text-background-color": "#ffffff",
            "text-background-padding": "2px",
          },
        },
      ],
      layout: {
        name: "breadthfirst",
        directed: true,
        padding: 18,
        spacingFactor: 1.15,
        avoidOverlap: true,
        animate: false,
      },
    })

    cyRef.current = cy

    const onResize = () => {
      cy.resize()
      cy.fit(undefined, 20)
    }

    window.addEventListener("resize", onResize)
    cy.fit(undefined, 20)

    return () => {
      window.removeEventListener("resize", onResize)
      cy.destroy()
      if (cyRef.current === cy) {
        cyRef.current = null
      }
    }
  }, [elements, graph])

  useEffect(() => {
    const cy = cyRef.current
    if (!cy || !focusedFactId) return

    cy.nodes().removeClass("focused")
    const node = cy.getElementById(`value:${focusedFactId}`)
    if (node.nonempty()) {
      node.addClass("focused")
      cy.animate({
        fit: { eles: node, padding: 80 },
        duration: 350,
      })
    }

    const card = document.querySelector(`[data-fact-id="${CSS.escape(focusedFactId)}"]`) as HTMLElement | null
    card?.scrollIntoView({ block: "nearest", behavior: "smooth" })
  }, [focusedFactId])

  if (!graph || graph.nodes.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
        Факты пока не загружены
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col overflow-y-auto p-3 chat-scrollbar">
      <div className="mb-3 flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
        <span className="rounded-full border px-2 py-1">Scope: {stats.scopes}</span>
        <span className="rounded-full border px-2 py-1">Свойства: {stats.properties}</span>
        <span className="rounded-full border px-2 py-1">Значения: {stats.values}</span>
        <span className="rounded-full border px-2 py-1">Фактов: {facts.length}</span>
      </div>

      <div className="rounded-lg border bg-card">
        <div className="border-b px-3 py-2 text-xs font-medium text-muted-foreground">
          Граф знаний
        </div>
        <div ref={graphRef} className="h-[430px] w-full" />
      </div>

      <div className="mt-3 flex flex-col gap-2">
        <div className="text-xs font-medium text-muted-foreground">Факты</div>
        {facts.length === 0 && (
          <div className="rounded-md border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
            Список фактов пуст
          </div>
        )}
        {facts.map(fact => {
          const status = normalizeStatus(fact.status)
          return (
            <div
              key={fact.id}
              data-fact-id={fact.id}
              className={cn(
                "rounded-md border bg-card px-3 py-2",
                focusedFactId === fact.id && "border-blue-500 ring-1 ring-blue-500/40",
              )}
            >
              <div className="mb-1 flex items-start justify-between gap-2">
                <div className="text-xs font-semibold text-foreground">
                  <span className="text-muted-foreground">{fact.scope}</span>
                  <span className="mx-1.5 text-muted-foreground">/</span>
                  <span>{fact.property}</span>
                </div>
                <span
                  className={cn(
                    "rounded-full px-2 py-0.5 text-[10px] font-medium",
                    valueStatusPalette[status] ?? "bg-muted text-muted-foreground",
                  )}
                >
                  {status || "unknown"}
                </span>
              </div>
              <div className="text-xs text-foreground">{fact.value}</div>
              {fact.source_ids.length > 0 && (
                <div className="mt-1 text-[10px] text-muted-foreground">
                  Источники: {fact.source_ids.join(", ")}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
