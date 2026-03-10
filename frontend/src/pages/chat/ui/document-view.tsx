import { useCallback, useEffect, useState } from "react"
import {
  Check, ChevronDown, Circle, Download, FileCheck, Loader2,
  Pencil, Plus, RefreshCw, ScrollText, Sparkles, Trash2,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { RichTextEditor } from "@/components/ui/rich-text-editor"
import { cn } from "@/lib/utils"
import type { GenerationRun } from "@/shared/api/chat-service"
import type { ContentNode, TZResult, TZSectionConfig } from "../lib/types"

type DocumentViewProps = {
  chatId: string | undefined
  generations: GenerationRun[]
  selected: GenerationRun | null
  onSelect: (run: GenerationRun) => void
  content: TZResult | null
  isContentLoading: boolean
  onRegenerateBlock: (fieldPath: string, instruction?: string) => void
  onGenerateCustomBlock: (fieldPath: string, customTopic: string) => void
  onManualEdit: (fieldPath: string, value: unknown) => Promise<void>
  onExport: (resultKey: string, format: "markdown" | "word" | "pdf") => void
  onUpdateCustomSections: (sectionKey: string, nodes: ContentNode[]) => Promise<void>
}

const sectionConfigs: TZSectionConfig[] = [
  { key: "general", number: "1", title: "Общее описание проекта" },
  { key: "functional", number: "2", title: "Функциональные требования" },
  { key: "ui_ux", number: "3", title: "Требования к интерфейсу" },
  { key: "technical", number: "4", title: "Технические требования" },
  { key: "non_functional", number: "5", title: "Нефункциональные требования" },
  { key: "stages", number: "6", title: "Этапы разработки" },
  { key: "acceptance", number: "7", title: "Критерии приёмки" },
]

const MAX_DEPTH = 3
const EXPORT_FORMATS = [
  { value: "markdown" as const, label: "Markdown" },
  { value: "word" as const, label: "Word" },
  { value: "pdf" as const, label: "PDF" },
]

function isFilled(value: unknown): boolean {
  if (value == null) return false
  if (typeof value === "string") return value.trim().length > 0
  if (Array.isArray(value)) return value.length > 0
  if (typeof value === "object") return Object.values(value).some(isFilled)
  return true
}

const fieldLabels: Record<string, string> = {
  purpose: "Назначение системы", analogues: "Аналоги/конкуренты",
  expected_outcome: "Итоговый продукт", roles: "Пользовательские роли",
  use_cases: "Сценарии использования", modules: "Модули и страницы",
  name: "Название", capabilities: "Возможности", steps: "Шаги",
  design_system: "Дизайн-система", responsiveness: "Адаптивность",
  colors: "Цвета", fonts: "Шрифты", style: "Стиль",
  mobile: "Мобильные", desktop: "Десктоп", tablet: "Планшеты",
  tech_stack: "Стек технологий", frontend: "Фронтенд", backend: "Бэкенд",
  database: "База данных", other: "Прочие технологии",
  integrations: "Интеграции", performance: "Производительность",
  details: "Детали", security: "Безопасность", scalability: "Масштабируемость",
  response_time: "Время отклика", mvp: "MVP", release: "Основной релиз",
  support: "Поддержка", deadline: "Срок", features: "Функции",
  testing: "Тестирование", documentation: "Документация",
}

function sectionDataToMarkdown(data: unknown): string {
  if (data == null) return ""
  if (typeof data === "string") return data
  if (typeof data === "number" || typeof data === "boolean") return String(data)
  if (Array.isArray(data)) {
    return data.map(item => {
      if (typeof item === "string") return `- ${item}`
      if (typeof item === "object" && item !== null) return sectionDataToMarkdown(item)
      return `- ${String(item)}`
    }).join("\n")
  }
  if (typeof data === "object") {
    const parts: string[] = []
    for (const [key, val] of Object.entries(data as Record<string, unknown>)) {
      if (val == null || (typeof val === "string" && !val.trim())) continue
      const label = fieldLabels[key] ?? key
      if (typeof val === "string" || typeof val === "number" || typeof val === "boolean") {
        parts.push(`**${label}:** ${val}`)
      } else if (Array.isArray(val)) {
        if (val.length === 0) continue
        const items = val.map(item => {
          if (typeof item === "string") return `- ${item}`
          if (typeof item === "object" && item !== null) {
            return Object.entries(item as Record<string, unknown>)
              .filter(([, v]) => v != null && v !== "" && !(Array.isArray(v) && v.length === 0))
              .map(([k, v]) => {
                const l = fieldLabels[k] ?? k
                if (Array.isArray(v)) return `  **${l}:**\n${(v as string[]).map(s => `  - ${s}`).join("\n")}`
                return `  **${l}:** ${v}`
              }).join("\n")
          }
          return `- ${String(item)}`
        }).join("\n\n")
        parts.push(`**${label}:**\n\n${items}`)
      } else if (typeof val === "object") {
        parts.push(`### ${label}\n\n${sectionDataToMarkdown(val)}`)
      }
    }
    return parts.join("\n\n")
  }
  return String(data)
}

function findSubsectionById(nodes: ContentNode[], id: string): ContentNode | null {
  for (const n of nodes) {
    if (n.id === id) return n
    const c = findSubsectionById(n.children, id)
    if (c) return c
  }
  return null
}

function mapSubsectionById(nodes: ContentNode[], id: string, fn: (n: ContentNode) => ContentNode): ContentNode[] {
  return nodes.map(n => n.id === id ? fn(n) : { ...n, children: mapSubsectionById(n.children, id, fn) })
}

function removeSubsection(nodes: ContentNode[], id: string): ContentNode[] {
  return nodes.filter(n => n.id !== id).map(n => ({ ...n, children: removeSubsection(n.children, id) }))
}

function addChildToSubsection(nodes: ContentNode[], parentId: string, child: ContentNode): ContentNode[] {
  return nodes.map(n => n.id === parentId ? { ...n, children: [...n.children, child] } : { ...n, children: addChildToSubsection(n.children, parentId, child) })
}

export function DocumentView({ chatId, generations, selected, onSelect, content, isContentLoading, onRegenerateBlock, onGenerateCustomBlock, onManualEdit, onExport, onUpdateCustomSections }: DocumentViewProps) {
  const [selectedSection, setSelectedSection] = useState<string>("general")
  const [selectedSubId, setSelectedSubId] = useState<string | null>(null)
  const [exportOpen, setExportOpen] = useState(false)
  const [editorContent, setEditorContent] = useState("")
  const [editorDirty, setEditorDirty] = useState(false)
  const [saving, setSaving] = useState(false)
  const [editingSubTitle, setEditingSubTitle] = useState(false)
  const [subTitleDraft, setSubTitleDraft] = useState("")
  const [regenOpen, setRegenOpen] = useState(false)
  const [regenInstruction, setRegenInstruction] = useState("")
  const [regenLoading, setRegenLoading] = useState(false)
  const [customOpen, setCustomOpen] = useState(false)
  const [customTopic, setCustomTopic] = useState("")
  const [customLoading, setCustomLoading] = useState(false)

  const doc = content?.document as Record<string, unknown> | undefined
  const validation = content?.validation
  const sectionConfig = sectionConfigs.find(s => s.key === selectedSection)
  const allCustomSections = (content?.custom_sections ?? {}) as Record<string, ContentNode[]>
  const currentSubs: ContentNode[] = allCustomSections[selectedSection] ?? []
  const activeSub = selectedSubId ? findSubsectionById(currentSubs, selectedSubId) : null
  const sectionFilled = isFilled(doc?.[selectedSection])

  useEffect(() => {
    if (selectedSubId) {
      const subs: ContentNode[] = ((content?.custom_sections ?? {}) as Record<string, ContentNode[]>)[selectedSection] ?? []
      const sub = findSubsectionById(subs, selectedSubId)
      setEditorContent(sub?.content ?? "")
      setSubTitleDraft(sub?.title ?? "")
    } else {
      setEditorContent(sectionDataToMarkdown(doc?.[selectedSection]))
    }
    setEditorDirty(false)
    setEditingSubTitle(false)
  }, [selectedSection, selectedSubId, content])

  const genId = () => Math.random().toString(36).slice(2, 10)
  const handleEditorChange = useCallback((md: string) => { setEditorContent(md); setEditorDirty(true) }, [])

  const handleSave = useCallback(async () => {
    setSaving(true)
    try {
      if (selectedSubId) {
        await onUpdateCustomSections(selectedSection, mapSubsectionById(currentSubs, selectedSubId, n => ({ ...n, content: editorContent })))
      } else {
        await onManualEdit(selectedSection, editorContent)
      }
      setEditorDirty(false)
    } finally { setSaving(false) }
  }, [selectedSubId, currentSubs, selectedSection, editorContent, onManualEdit, onUpdateCustomSections])

  const handleSaveSubTitle = useCallback(async () => {
    if (!selectedSubId) return
    await onUpdateCustomSections(selectedSection, mapSubsectionById(currentSubs, selectedSubId, n => ({ ...n, title: subTitleDraft })))
    setEditingSubTitle(false)
  }, [selectedSubId, currentSubs, selectedSection, subTitleDraft, onUpdateCustomSections])

  const handleAddSubsection = useCallback((sectionKey: string) => {
    const subs: ContentNode[] = allCustomSections[sectionKey] ?? []
    onUpdateCustomSections(sectionKey, [...subs, { id: genId(), title: "Новый подпункт", content: "", children: [] }])
  }, [allCustomSections, onUpdateCustomSections])

  const handleAddChildSub = useCallback((parentId: string, sectionKey: string) => {
    const subs: ContentNode[] = allCustomSections[sectionKey] ?? []
    onUpdateCustomSections(sectionKey, addChildToSubsection(subs, parentId, { id: genId(), title: "Новый подпункт", content: "", children: [] }))
  }, [allCustomSections, onUpdateCustomSections])

  const handleDeleteSub = useCallback((id: string, sectionKey: string) => {
    const subs: ContentNode[] = allCustomSections[sectionKey] ?? []
    onUpdateCustomSections(sectionKey, removeSubsection(subs, id))
    if (selectedSubId === id) setSelectedSubId(null)
  }, [allCustomSections, onUpdateCustomSections, selectedSubId])

  const handleSelectSection = useCallback((key: string) => { setSelectedSection(key); setSelectedSubId(null) }, [])

  const handleRegenerate = useCallback(() => {
    setRegenLoading(true)
    onRegenerateBlock(selectedSection, regenInstruction || undefined)
    setRegenOpen(false)
    setRegenInstruction("")
    setTimeout(() => setRegenLoading(false), 1000)
  }, [selectedSection, regenInstruction, onRegenerateBlock])

  const handleGenerateCustom = useCallback(() => {
    if (!customTopic.trim()) return
    setCustomLoading(true)
    onGenerateCustomBlock(selectedSection, customTopic)
    setCustomOpen(false)
    setCustomTopic("")
    setTimeout(() => setCustomLoading(false), 1000)
  }, [selectedSection, customTopic, onGenerateCustomBlock])

  if (generations.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 text-center p-8">
        <ScrollText className="size-12 text-muted-foreground/30" />
        <div className="space-y-1">
          <p className="text-sm font-medium">ТЗ пока не сгенерировано</p>
          <p className="text-xs text-muted-foreground max-w-sm">Отправьте сообщение в чат, чтобы запустить генерацию.</p>
        </div>
      </div>
    )
  }

  const renderSidebarSubs = (nodes: ContentNode[], sectionKey: string, parentNum: string, depth: number): React.ReactNode =>
    nodes.map((node, i) => {
      const num = `${parentNum}.${i + 1}`
      const isActive = selectedSubId === node.id && selectedSection === sectionKey
      return (
        <div key={node.id}>
          <button
            onClick={() => { setSelectedSection(sectionKey); setSelectedSubId(node.id) }}
            className={cn("flex w-full items-center gap-1.5 rounded-md py-1 text-left text-xs transition-colors hover:bg-accent/50 group/sub", isActive && "bg-accent text-accent-foreground")}
            style={{ paddingLeft: `${8 + depth * 12}px`, paddingRight: "8px" }}
          >
            <span className="text-muted-foreground font-mono shrink-0 text-[10px]">{num}</span>
            <span className="truncate flex-1">{node.title || <span className="italic text-muted-foreground">Без названия</span>}</span>
            <span className="flex items-center gap-0.5 opacity-0 group-hover/sub:opacity-100 transition-opacity shrink-0">
              {depth < MAX_DEPTH && (
                <span role="button" className="p-0.5 rounded hover:bg-accent" onClick={e => { e.stopPropagation(); handleAddChildSub(node.id, sectionKey) }} title="Добавить дочерний"><Plus className="size-2.5" /></span>
              )}
              <span role="button" className="p-0.5 rounded hover:bg-destructive/20 hover:text-destructive" onClick={e => { e.stopPropagation(); handleDeleteSub(node.id, sectionKey) }} title="Удалить"><Trash2 className="size-2.5" /></span>
            </span>
          </button>
          {node.children.length > 0 && renderSidebarSubs(node.children, sectionKey, num, depth + 1)}
        </div>
      )
    })

  return (
    <div className="flex flex-col h-full">
      {/* Version selector + export */}
      <div className="flex items-center justify-between gap-2 border-b px-4 py-2.5 shrink-0">
        <div className="flex items-center gap-2 overflow-x-auto chat-scrollbar">
          {generations.map((run, i) => (
            <button key={run.id} onClick={() => onSelect(run)} className={cn("flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors whitespace-nowrap", selected?.id === run.id ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:text-foreground hover:bg-muted/50")}>
              <FileCheck className="size-3.5" />
              Версия {i + 1}
            </button>
          ))}
        </div>
        {selected?.result_key && (
          <div className="relative shrink-0">
            <Button variant="outline" size="sm" className="h-7 text-xs gap-1.5" onClick={() => setExportOpen(o => !o)}>
              <Download className="size-3.5" />Экспорт<ChevronDown className="size-3" />
            </Button>
            {exportOpen && (
              <div className="absolute right-0 top-full mt-1 z-10 rounded-md border bg-popover p-1 shadow-md min-w-[140px]">
                {EXPORT_FORMATS.map(f => (
                  <button key={f.value} className="flex w-full items-center rounded-sm px-2 py-1.5 text-xs hover:bg-accent" onClick={() => { onExport(selected.result_key!, f.value); setExportOpen(false) }}>{f.label}</button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Main area */}
      {isContentLoading ? (
        <div className="flex items-center justify-center flex-1"><Loader2 className="size-6 animate-spin text-muted-foreground" /></div>
      ) : content ? (
        <div className="flex flex-1 min-h-0">
          {/* Sidebar */}
          <div className="w-[240px] shrink-0 border-r overflow-y-auto chat-scrollbar p-3 space-y-0.5">
            {validation && (
              <div className="mb-3 px-2 pb-3 border-b">
                <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1.5">
                  <span>Заполнено</span>
                  <span className="font-medium text-foreground">{validation.completeness_percent}%</span>
                </div>
                <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                  <div className={cn("h-full rounded-full transition-all", validation.completeness_percent >= 80 ? "bg-emerald-500" : validation.completeness_percent >= 40 ? "bg-primary" : "bg-amber-500")} style={{ width: `${validation.completeness_percent}%` }} />
                </div>
                <div className="text-[10px] text-muted-foreground mt-1">
                  {validation.filled_fields}/{validation.total_fields} полей
                  {validation.gaps.length > 0 && ` · ${validation.gaps.length} пропусков`}
                </div>
              </div>
            )}

            {sectionConfigs.map(section => {
              const filled = isFilled(doc?.[section.key])
              const subs: ContentNode[] = (allCustomSections[section.key] ?? []) as ContentNode[]
              const isActiveSec = selectedSection === section.key && selectedSubId === null
              return (
                <div key={section.key}>
                  <button onClick={() => handleSelectSection(section.key)} className={cn("flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors hover:bg-accent/50 group/sec", isActiveSec && "bg-accent text-accent-foreground")}>
                    {filled ? <Check className="size-3 shrink-0 text-emerald-500" /> : <Circle className="size-3 shrink-0 text-muted-foreground" />}
                    <span className="text-muted-foreground mr-1 text-xs">{section.number}</span>
                    <span className="truncate text-xs flex-1">{section.title}</span>
                    <span role="button" className="opacity-0 group-hover/sec:opacity-100 transition-opacity p-0.5 rounded hover:bg-accent shrink-0" onClick={e => { e.stopPropagation(); handleAddSubsection(section.key) }} title="Добавить подпункт">
                      <Plus className="size-3" />
                    </span>
                  </button>
                  {subs.length > 0 && renderSidebarSubs(subs, section.key, section.number, 1)}
                </div>
              )
            })}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0 flex flex-col overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between gap-2 px-6 py-3 border-b shrink-0">
              <div className="flex items-center gap-2 min-w-0">
                {activeSub ? (
                  <>
                    {editingSubTitle ? (
                      <input className="text-lg font-semibold bg-transparent border-b border-ring outline-none min-w-0" value={subTitleDraft} onChange={e => setSubTitleDraft(e.target.value)} onBlur={() => handleSaveSubTitle()} onKeyDown={e => { if (e.key === "Enter") handleSaveSubTitle(); if (e.key === "Escape") setEditingSubTitle(false) }} autoFocus />
                    ) : (
                      <h2 className="text-lg font-semibold truncate cursor-pointer" onDoubleClick={() => { setSubTitleDraft(activeSub.title); setEditingSubTitle(true) }}>{activeSub.title || "Без названия"}</h2>
                    )}
                    <button className="p-1 text-muted-foreground hover:text-foreground shrink-0" onClick={() => { setSubTitleDraft(activeSub.title); setEditingSubTitle(true) }}>
                      <Pencil className="size-3.5" />
                    </button>
                  </>
                ) : (
                  <>
                    <span className="text-sm text-muted-foreground font-mono shrink-0">§{sectionConfig?.number}</span>
                    <h2 className="text-lg font-semibold truncate">{sectionConfig?.title}</h2>
                    {sectionFilled
                      ? <Badge variant="outline" className="text-[10px] text-emerald-500 shrink-0">Заполнено</Badge>
                      : <Badge variant="outline" className="text-[10px] text-muted-foreground shrink-0">Пусто</Badge>}
                  </>
                )}
              </div>

              <div className="flex items-center gap-1.5 shrink-0">
                {editorDirty && (
                  <Button size="sm" className="h-7 text-xs gap-1.5" disabled={saving} onClick={handleSave}>
                    {saving ? <Loader2 className="size-3.5 animate-spin" /> : "Сохранить"}
                  </Button>
                )}
                {activeSub ? (
                  <div className="relative">
                    <Button variant="ghost" size="sm" className="h-7 text-xs gap-1.5" disabled={customLoading} onClick={() => setCustomOpen(o => !o)}>
                      {customLoading ? <Loader2 className="size-3.5 animate-spin" /> : <Sparkles className="size-3.5" />}
                      Сгенерировать
                    </Button>
                    {customOpen && (
                      <div className="absolute right-0 top-full mt-1 z-10 rounded-md border bg-popover p-3 shadow-md w-[280px] space-y-2">
                        <p className="text-xs text-muted-foreground">Тема для генерации:</p>
                        <textarea className="w-full rounded-md border bg-background px-2 py-1.5 text-xs resize-none focus:outline-none focus:ring-1 focus:ring-ring" rows={2} placeholder="Например: Требования к анимациям…" value={customTopic} onChange={e => setCustomTopic(e.target.value)} onKeyDown={e => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); handleGenerateCustom() } if (e.key === "Escape") setCustomOpen(false) }} autoFocus />
                        <div className="flex gap-1.5 justify-end">
                          <Button variant="ghost" size="sm" className="h-6 text-xs" onClick={() => setCustomOpen(false)}>Отмена</Button>
                          <Button size="sm" className="h-6 text-xs" disabled={!customTopic.trim()} onClick={handleGenerateCustom}>Сгенерировать</Button>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (sectionFilled ? (
                  <div className="relative">
                    <Button variant="ghost" size="sm" className="h-7 text-xs gap-1.5" disabled={regenLoading} onClick={() => setRegenOpen(o => !o)}>
                      {regenLoading ? <Loader2 className="size-3.5 animate-spin" /> : <RefreshCw className="size-3.5" />}
                      Перегенерировать
                    </Button>
                    {regenOpen && (
                      <div className="absolute right-0 top-full mt-1 z-10 rounded-md border bg-popover p-3 shadow-md w-[280px] space-y-2">
                        <p className="text-xs text-muted-foreground">Инструкция (необязательно):</p>
                        <textarea className="w-full rounded-md border bg-background px-2 py-1.5 text-xs resize-none focus:outline-none focus:ring-1 focus:ring-ring" rows={2} placeholder="Например: сделай покороче…" value={regenInstruction} onChange={e => setRegenInstruction(e.target.value)} onKeyDown={e => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); handleRegenerate() } if (e.key === "Escape") setRegenOpen(false) }} autoFocus />
                        <div className="flex gap-1.5 justify-end">
                          <Button variant="ghost" size="sm" className="h-6 text-xs" onClick={() => setRegenOpen(false)}>Отмена</Button>
                          <Button size="sm" className="h-6 text-xs" onClick={handleRegenerate}>Запустить</Button>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="relative">
                    <Button variant="ghost" size="sm" className="h-7 text-xs gap-1.5" disabled={customLoading} onClick={() => setCustomOpen(o => !o)}>
                      {customLoading ? <Loader2 className="size-3.5 animate-spin" /> : <Sparkles className="size-3.5" />}
                      Заполнить AI
                    </Button>
                    {customOpen && (
                      <div className="absolute right-0 top-full mt-1 z-10 rounded-md border bg-popover p-3 shadow-md w-[280px] space-y-2">
                        <p className="text-xs text-muted-foreground">Тема для генерации:</p>
                        <textarea className="w-full rounded-md border bg-background px-2 py-1.5 text-xs resize-none focus:outline-none focus:ring-1 focus:ring-ring" rows={2} placeholder="Например: Требования к анимациям…" value={customTopic} onChange={e => setCustomTopic(e.target.value)} onKeyDown={e => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); handleGenerateCustom() } if (e.key === "Escape") setCustomOpen(false) }} autoFocus />
                        <div className="flex gap-1.5 justify-end">
                          <Button variant="ghost" size="sm" className="h-6 text-xs" onClick={() => setCustomOpen(false)}>Отмена</Button>
                          <Button size="sm" className="h-6 text-xs" disabled={!customTopic.trim()} onClick={handleGenerateCustom}>Сгенерировать</Button>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Editor */}
            <div className="flex-1 overflow-y-auto chat-scrollbar p-6">
              <RichTextEditor value={editorContent} onChange={handleEditorChange} placeholder={activeSub ? "Содержимое подпункта…" : "Содержимое раздела…"} minHeight="300px" />
              {!activeSub && validation && validation.gaps.filter(g => g.section === selectedSection).length > 0 && (
                <div className="mt-6 rounded-lg border border-amber-500/20 bg-amber-500/5 p-4">
                  <p className="text-xs font-medium text-amber-600 dark:text-amber-400 mb-2">Незаполненные поля</p>
                  <div className="space-y-1">
                    {validation.gaps.filter(g => g.section === selectedSection).map(gap => (
                      <div key={gap.field_path} className="text-xs text-foreground/70">
                        <span className="font-medium">{gap.field_name}</span>
                        <span className="text-muted-foreground"> — {gap.description}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      ) : (
        <div className="flex items-center justify-center flex-1 text-sm text-muted-foreground">Не удалось загрузить содержимое</div>
      )}
    </div>
  )
}