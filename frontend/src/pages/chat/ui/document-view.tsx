import { useCallback, useEffect, useMemo, useState } from "react"
import {
  ArrowDown,
  ArrowUp,
  Check,
  ChevronDown,
  Circle,
  Download,
  Loader2,
  Plus,
  RefreshCw,
  ScrollText,
  Sparkles,
  Trash2,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { RichTextEditor } from "@/components/ui/rich-text-editor"
import { cn } from "@/lib/utils"
import type { GenerationRun } from "@/shared/api/chat-service"
import type { SectionVersionMeta } from "@/shared/api/tz-service"
import type { TZResult, TZSection } from "../lib/types"

type DocumentViewProps = {
  selected: GenerationRun | null
  content: TZResult | null
  isContentLoading: boolean
  onRegenerateBlock: (fieldPath: string, instruction?: string) => void
  onGenerateCustomBlock: (fieldPath: string, customTopic: string) => void
  onSaveSections: (sections: TZSection[]) => Promise<void>
  onSaveCurrentVersion: () => Promise<void>
  onLoadVersions: () => Promise<SectionVersionMeta[]>
  onPreviewVersion: (versionId: string) => Promise<TZSection[]>
  onRestoreVersion: (versionId: string) => Promise<void>
  onExport: (resultKey: string, format: "markdown" | "word" | "pdf") => void
}

const EXPORT_FORMATS = [
  { value: "markdown" as const, label: "Markdown" },
  { value: "word" as const, label: "Word" },
  { value: "pdf" as const, label: "PDF" },
]

const REF_TAG_REGEX = /<ref\b[^>]*\/>/g
const RU_TO_LATIN: Record<string, string> = {
  "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh",
  "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
  "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "ts",
  "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}

function stripRefTags(text: string): string {
  return text
    .replace(/`\s*<ref\b[^>]*\/>\s*`/g, "")
    .replace(REF_TAG_REGEX, "")
    .replace(/``/g, "")
    .replace(/[ \t]{2,}/g, " ")
}

function isFilled(value: string): boolean {
  return value.trim().length > 0
}

function slugifySectionId(title: string): string {
  const lowered = title.trim().toLowerCase()
  const translit = [...lowered].map(ch => RU_TO_LATIN[ch] ?? ch).join("")
  const slug = translit.replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "")
  return slug || "section"
}

function nextUniqueSectionId(base: string, taken: Set<string>): string {
  if (!taken.has(base)) {
    taken.add(base)
    return base
  }
  let i = 2
  while (true) {
    const candidate = `${base}_${i}`
    if (!taken.has(candidate)) {
      taken.add(candidate)
      return candidate
    }
    i += 1
  }
}

function normalizeIncomingSections(sections: TZSection[]): TZSection[] {
  const taken = new Set<string>()
  return sections.map((section, index) => {
    const sectionId = nextUniqueSectionId(slugifySectionId(section.section_id || section.title), taken)
    return {
      section_id: sectionId,
      title: section.title,
      level: Number.isFinite(section.level) ? Number(section.level) : index,
      required: section.required,
      context_hint: section.context_hint,
      is_manual: section.is_manual,
      content_md: stripRefTags(section.content_md || ""),
    }
  })
}

function moveSection(sections: TZSection[], index: number, direction: -1 | 1): TZSection[] {
  const target = index + direction
  if (target < 0 || target >= sections.length) return sections
  const next = [...sections]
  ;[next[index], next[target]] = [next[target], next[index]]
  return next.map((section, idx) => ({ ...section, level: idx }))
}

export function DocumentView({
  selected,
  content,
  isContentLoading,
  onRegenerateBlock,
  onGenerateCustomBlock,
  onSaveSections,
  onSaveCurrentVersion,
  onLoadVersions,
  onPreviewVersion,
  onRestoreVersion,
  onExport,
}: DocumentViewProps) {
  const [mode, setMode] = useState<"view" | "edit">("view")
  const [selectedSectionId, setSelectedSectionId] = useState<string>("")
  const [draftSections, setDraftSections] = useState<TZSection[]>([])
  const [dirty, setDirty] = useState(false)
  const [savingAll, setSavingAll] = useState(false)
  const [exportOpen, setExportOpen] = useState(false)
  const [regenOpen, setRegenOpen] = useState(false)
  const [regenInstruction, setRegenInstruction] = useState("")
  const [regenLoading, setRegenLoading] = useState(false)
  const [customOpen, setCustomOpen] = useState(false)
  const [customTopic, setCustomTopic] = useState("")
  const [customLoading, setCustomLoading] = useState(false)
  const [savingVersion, setSavingVersion] = useState(false)
  const [versionsOpen, setVersionsOpen] = useState(false)
  const [versionsLoading, setVersionsLoading] = useState(false)
  const [versions, setVersions] = useState<SectionVersionMeta[]>([])
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewSections, setPreviewSections] = useState<TZSection[]>([])
  const [restoringVersion, setRestoringVersion] = useState(false)

  const validation = content?.validation
  const validationGaps = validation?.gaps ?? []

  useEffect(() => {
    const incoming = content?.sections ?? []
    const normalized = normalizeIncomingSections(incoming)
    setDraftSections(normalized)
    setDirty(false)

    if (normalized.length === 0) {
      setSelectedSectionId("")
      return
    }

    setSelectedSectionId(prev => {
      if (normalized.some(section => section.section_id === prev)) {
        return prev
      }
      return normalized[0].section_id
    })
  }, [content])

  const selectedIndex = useMemo(
    () => draftSections.findIndex(section => section.section_id === selectedSectionId),
    [draftSections, selectedSectionId],
  )

  const selectedSection = selectedIndex >= 0 ? draftSections[selectedIndex] : null

  const updateSection = useCallback((sectionId: string, updater: (section: TZSection) => TZSection) => {
    setDraftSections(prev => prev.map(section => section.section_id === sectionId ? updater(section) : section))
    setDirty(true)
  }, [])

  const handleTitleChange = useCallback((title: string) => {
    if (!selectedSection) return
    updateSection(selectedSection.section_id, section => ({ ...section, title }))
  }, [selectedSection, updateSection])

  const handleContentChange = useCallback((markdown: string) => {
    if (mode !== "edit" || !selectedSection) return
    updateSection(selectedSection.section_id, section => ({ ...section, content_md: markdown }))
  }, [mode, selectedSection, updateSection])

  const handleMove = useCallback((index: number, direction: -1 | 1) => {
    setDraftSections(prev => moveSection(prev, index, direction))
    setDirty(true)
  }, [])

  const handleDeleteSection = useCallback((index: number) => {
    setDraftSections(prev => {
      const next = prev.filter((_, idx) => idx !== index)
      const withPosition = next.map((section, idx) => ({ ...section, level: idx }))
      const newSelected = withPosition[Math.max(0, index - 1)]
      setSelectedSectionId(newSelected?.section_id ?? "")
      return withPosition
    })
    setDirty(true)
  }, [])

  const handleAddSection = useCallback(() => {
    setDraftSections(prev => {
      const taken = new Set(prev.map(section => section.section_id))
      const sectionId = nextUniqueSectionId("new_section", taken)
      const next: TZSection = {
        section_id: sectionId,
        title: "Новая секция",
        level: prev.length,
        required: false,
        context_hint: null,
        is_manual: true,
        content_md: "",
      }
      const updated = [...prev, next]
      setSelectedSectionId(next.section_id)
      return updated
    })
    setDirty(true)
    setMode("edit")
  }, [])

  const handleSaveAll = useCallback(async () => {
    setSavingAll(true)
    try {
      const normalized = normalizeIncomingSections(draftSections).map((section, index) => ({
        ...section,
        level: index,
      }))
      await onSaveSections(normalized)
      setDraftSections(normalized)
      setDirty(false)
    } finally {
      setSavingAll(false)
    }
  }, [draftSections, onSaveSections])

  const handleSaveVersion = useCallback(async () => {
    setSavingVersion(true)
    try {
      await onSaveCurrentVersion()
    } finally {
      setSavingVersion(false)
    }
  }, [onSaveCurrentVersion])

  const handleOpenVersions = useCallback(async () => {
    setVersionsOpen(true)
    setVersionsLoading(true)
    try {
      const loaded = await onLoadVersions()
      setVersions(loaded)
      if (loaded.length > 0) {
        const firstId = loaded[0].id
        setSelectedVersionId(firstId)
        setPreviewLoading(true)
        try {
          const preview = await onPreviewVersion(firstId)
          setPreviewSections(preview)
        } finally {
          setPreviewLoading(false)
        }
      } else {
        setSelectedVersionId(null)
        setPreviewSections([])
      }
    } finally {
      setVersionsLoading(false)
    }
  }, [onLoadVersions, onPreviewVersion])

  const handleSelectVersion = useCallback(async (versionId: string) => {
    setSelectedVersionId(versionId)
    setPreviewLoading(true)
    try {
      const preview = await onPreviewVersion(versionId)
      setPreviewSections(preview)
    } finally {
      setPreviewLoading(false)
    }
  }, [onPreviewVersion])

  const handleRestoreSelectedVersion = useCallback(async () => {
    if (!selectedVersionId) return
    if (dirty) {
      const confirmed = window.confirm("Все текущие несохраненные изменения будут сброшены. Продолжить восстановление?")
      if (!confirmed) return
    }

    setRestoringVersion(true)
    try {
      await onRestoreVersion(selectedVersionId)
      setVersionsOpen(false)
    } finally {
      setRestoringVersion(false)
    }
  }, [dirty, onRestoreVersion, selectedVersionId])

  const handleRegenerate = useCallback(() => {
    if (!selectedSection) return
    setRegenLoading(true)
    onRegenerateBlock(selectedSection.section_id, regenInstruction || undefined)
    setRegenOpen(false)
    setRegenInstruction("")
    setTimeout(() => setRegenLoading(false), 1000)
  }, [selectedSection, regenInstruction, onRegenerateBlock])

  const handleGenerateCustom = useCallback(() => {
    if (!selectedSection || !customTopic.trim()) return
    setCustomLoading(true)
    onGenerateCustomBlock(selectedSection.section_id, customTopic)
    setCustomOpen(false)
    setCustomTopic("")
    setTimeout(() => setCustomLoading(false), 1000)
  }, [selectedSection, customTopic, onGenerateCustomBlock])

  if (!selected) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 p-8 text-center">
        <ScrollText className="size-12 text-muted-foreground/30" />
        <div className="space-y-1">
          <p className="text-sm font-medium">ТЗ пока не сгенерировано</p>
          <p className="max-w-sm text-xs text-muted-foreground">Отправьте сообщение в чат, чтобы запустить генерацию.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="relative flex h-full flex-col">
      <div className="flex shrink-0 items-center justify-between gap-2 border-b px-4 py-2.5">
        <span className="text-xs text-muted-foreground">Рабочая версия документа</span>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="h-7 gap-1.5 text-xs"
            onClick={handleSaveVersion}
            disabled={savingVersion}
          >
            {savingVersion ? <Loader2 className="size-3.5 animate-spin" /> : "Сохранить текущую версию"}
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="h-7 gap-1.5 text-xs"
            onClick={() => {
              void handleOpenVersions()
            }}
          >
            Прошлые версии
          </Button>
          {mode === "edit" && dirty && (
            <Button size="sm" className="h-7 gap-1.5 text-xs" onClick={handleSaveAll} disabled={savingAll}>
              {savingAll ? <Loader2 className="size-3.5 animate-spin" /> : "Сохранить все изменения"}
            </Button>
          )}
          {selected?.result_key && (
            <div className="relative shrink-0">
              <Button variant="outline" size="sm" className="h-7 gap-1.5 text-xs" onClick={() => setExportOpen(o => !o)}>
                <Download className="size-3.5" />Экспорт<ChevronDown className="size-3" />
              </Button>
              {exportOpen && (
                <div className="absolute right-0 top-full z-10 mt-1 min-w-[140px] rounded-md border bg-popover p-1 shadow-md">
                  {EXPORT_FORMATS.map(format => (
                    <button
                      key={format.value}
                      className="flex w-full items-center rounded-sm px-2 py-1.5 text-xs hover:bg-accent"
                      onClick={() => {
                        onExport(selected.result_key!, format.value)
                        setExportOpen(false)
                      }}
                    >
                      {format.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {isContentLoading ? (
        <div className="flex flex-1 items-center justify-center"><Loader2 className="size-6 animate-spin text-muted-foreground" /></div>
      ) : (
        <div className="flex min-h-0 flex-1">
          <div className="chat-scrollbar w-[300px] shrink-0 space-y-0.5 overflow-y-auto border-r p-3">
            {validation && (
              <div className="mb-3 border-b px-2 pb-3">
                <div className="mb-1.5 flex items-center gap-2 text-xs text-muted-foreground">
                  <span>Заполнено</span>
                  <span className="font-medium text-foreground">{validation.completeness_percent}%</span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                  <div
                    className={cn(
                      "h-full rounded-full transition-all",
                      validation.completeness_percent >= 80
                        ? "bg-emerald-500"
                        : validation.completeness_percent >= 40
                          ? "bg-primary"
                          : "bg-amber-500",
                    )}
                    style={{ width: `${validation.completeness_percent}%` }}
                  />
                </div>
              </div>
            )}

            {draftSections.map((section, index) => {
              const isActive = section.section_id === selectedSectionId
              const canMoveUp = index > 0
              const canMoveDown = index < draftSections.length - 1

              return (
                <button
                  key={section.section_id}
                  onClick={() => setSelectedSectionId(section.section_id)}
                  className={cn(
                    "group/sec flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors hover:bg-accent/50",
                    isActive && "bg-accent text-accent-foreground",
                  )}
                >
                  {isFilled(section.content_md) ? (
                    <Check className="size-3 shrink-0 text-emerald-500" />
                  ) : (
                    <Circle className="size-3 shrink-0 text-muted-foreground" />
                  )}
                  <span className="mr-1 text-xs text-muted-foreground">{index + 1}</span>
                  <span className="flex-1 truncate text-xs">{section.title || "Без названия"}</span>
                  {mode === "edit" && (
                    <span className="flex shrink-0 items-center gap-0.5 opacity-0 transition-opacity group-hover/sec:opacity-100">
                      <span role="button" className={cn("rounded p-0.5 hover:bg-accent", !canMoveUp && "pointer-events-none opacity-40")} onClick={e => { e.stopPropagation(); handleMove(index, -1) }} title="Вверх"><ArrowUp className="size-3" /></span>
                      <span role="button" className={cn("rounded p-0.5 hover:bg-accent", !canMoveDown && "pointer-events-none opacity-40")} onClick={e => { e.stopPropagation(); handleMove(index, 1) }} title="Вниз"><ArrowDown className="size-3" /></span>
                      <span role="button" className="rounded p-0.5 hover:bg-destructive/20 hover:text-destructive" onClick={e => { e.stopPropagation(); handleDeleteSection(index) }} title="Удалить"><Trash2 className="size-3" /></span>
                    </span>
                  )}
                </button>
              )
            })}

            {mode === "edit" && (
              <Button variant="outline" size="sm" className="mt-2 h-7 w-full gap-1.5 text-xs" onClick={handleAddSection}>
                <Plus className="size-3.5" />Добавить секцию
              </Button>
            )}
          </div>

          <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
            <div className="flex shrink-0 items-center justify-between gap-2 border-b px-6 py-3">
              <div className="min-w-0 flex-1">
                {selectedSection ? (
                  mode === "edit" ? (
                    <input
                      value={selectedSection.title}
                      onChange={e => handleTitleChange(e.target.value)}
                      className="w-full min-w-0 border-b border-ring bg-transparent text-lg font-semibold outline-none"
                    />
                  ) : (
                    <h2 className="truncate text-lg font-semibold">{selectedSection.title}</h2>
                  )
                ) : (
                  <h2 className="text-lg font-semibold">Секции не найдены</h2>
                )}
              </div>

              <div className="flex shrink-0 items-center gap-1.5">
                <div className="inline-flex rounded-md border p-0.5">
                  <Button variant={mode === "view" ? "secondary" : "ghost"} size="sm" className="h-6 px-2 text-[11px]" onClick={() => setMode("view")}>Просмотр</Button>
                  <Button variant={mode === "edit" ? "secondary" : "ghost"} size="sm" className="h-6 px-2 text-[11px]" onClick={() => setMode("edit")}>Редактирование</Button>
                </div>

                {selectedSection && (
                  isFilled(selectedSection.content_md) ? (
                    <div className="relative">
                      <Button variant="ghost" size="sm" className="h-7 gap-1.5 text-xs" disabled={regenLoading} onClick={() => setRegenOpen(o => !o)}>
                        {regenLoading ? <Loader2 className="size-3.5 animate-spin" /> : <RefreshCw className="size-3.5" />}
                        Перегенерировать
                      </Button>
                      {regenOpen && (
                        <div className="absolute right-0 top-full z-10 mt-1 w-[280px] space-y-2 rounded-md border bg-popover p-3 shadow-md">
                          <p className="text-xs text-muted-foreground">Инструкция (необязательно):</p>
                          <textarea
                            className="w-full resize-none rounded-md border bg-background px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
                            rows={2}
                            placeholder="Например: сократи до списка"
                            value={regenInstruction}
                            onChange={e => setRegenInstruction(e.target.value)}
                          />
                          <div className="flex justify-end gap-1.5">
                            <Button variant="ghost" size="sm" className="h-6 text-xs" onClick={() => setRegenOpen(false)}>Отмена</Button>
                            <Button size="sm" className="h-6 text-xs" onClick={handleRegenerate}>Запустить</Button>
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="relative">
                      <Button variant="ghost" size="sm" className="h-7 gap-1.5 text-xs" disabled={customLoading} onClick={() => setCustomOpen(o => !o)}>
                        {customLoading ? <Loader2 className="size-3.5 animate-spin" /> : <Sparkles className="size-3.5" />}
                        Заполнить AI
                      </Button>
                      {customOpen && (
                        <div className="absolute right-0 top-full z-10 mt-1 w-[280px] space-y-2 rounded-md border bg-popover p-3 shadow-md">
                          <p className="text-xs text-muted-foreground">Тема для генерации:</p>
                          <textarea
                            className="w-full resize-none rounded-md border bg-background px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
                            rows={2}
                            placeholder="Например: Метрики производительности"
                            value={customTopic}
                            onChange={e => setCustomTopic(e.target.value)}
                          />
                          <div className="flex justify-end gap-1.5">
                            <Button variant="ghost" size="sm" className="h-6 text-xs" onClick={() => setCustomOpen(false)}>Отмена</Button>
                            <Button size="sm" className="h-6 text-xs" disabled={!customTopic.trim()} onClick={handleGenerateCustom}>Сгенерировать</Button>
                          </div>
                        </div>
                      )}
                    </div>
                  )
                )}
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-6 chat-scrollbar">
              {selectedSection ? (
                <>
                  <div className="mb-3 flex items-center gap-2">
                    <Badge variant="outline" className="text-[10px]">ID: {selectedSection.section_id}</Badge>
                    {isFilled(selectedSection.content_md)
                      ? <Badge variant="outline" className="text-[10px] text-emerald-500">Заполнено</Badge>
                      : <Badge variant="outline" className="text-[10px] text-muted-foreground">Пусто</Badge>}
                  </div>
                  <RichTextEditor
                    value={selectedSection.content_md}
                    onChange={handleContentChange}
                    placeholder="Содержимое секции..."
                    minHeight="320px"
                    editable={mode === "edit"}
                  />
                  {validation && validationGaps.filter(gap => gap.section === selectedSection.section_id).length > 0 && (
                    <div className="mt-6 rounded-lg border border-amber-500/20 bg-amber-500/5 p-4">
                      <p className="mb-2 text-xs font-medium text-amber-600 dark:text-amber-400">Незаполненные поля</p>
                      <div className="space-y-1">
                        {validationGaps.filter(gap => gap.section === selectedSection.section_id).map(gap => (
                          <div key={gap.field_path} className="text-xs text-foreground/70">
                            <span className="font-medium">{gap.field_name}</span>
                            <span className="text-muted-foreground"> - {gap.description}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="flex h-full items-center justify-center text-sm text-muted-foreground">Нет выбранной секции</div>
              )}
            </div>
          </div>
        </div>
      )}

      {versionsOpen && (
        <div className="absolute inset-0 z-20 flex items-center justify-center bg-background/60 p-6">
          <div className="flex h-[70vh] w-full max-w-5xl gap-4 rounded-xl border bg-background p-4 shadow-xl">
            <div className="flex w-[280px] shrink-0 flex-col rounded-lg border">
              <div className="border-b px-3 py-2 text-sm font-medium">Прошлые версии</div>
              <div className="chat-scrollbar flex-1 space-y-1 overflow-y-auto p-2">
                {versionsLoading ? (
                  <div className="flex items-center justify-center py-10 text-muted-foreground"><Loader2 className="size-4 animate-spin" /></div>
                ) : versions.length === 0 ? (
                  <div className="px-2 py-6 text-xs text-muted-foreground">Сохраненных версий пока нет</div>
                ) : (
                  versions.map(version => (
                    <button
                      key={version.id}
                      onClick={() => {
                        void handleSelectVersion(version.id)
                      }}
                      className={cn(
                        "w-full rounded-md border px-2 py-2 text-left text-xs hover:bg-accent/50",
                        selectedVersionId === version.id && "bg-accent",
                      )}
                    >
                      <div className="font-medium">{version.title}</div>
                      <div className="text-muted-foreground">{new Date(version.created_at).toLocaleString()}</div>
                      <div className="text-muted-foreground">{version.sections_count} секций</div>
                    </button>
                  ))
                )}
              </div>
            </div>

            <div className="flex min-w-0 flex-1 flex-col rounded-lg border">
              <div className="border-b px-3 py-2 text-sm font-medium">Предпросмотр</div>
              <div className="chat-scrollbar flex-1 overflow-y-auto p-3">
                {previewLoading ? (
                  <div className="flex items-center justify-center py-10 text-muted-foreground"><Loader2 className="size-4 animate-spin" /></div>
                ) : previewSections.length === 0 ? (
                  <div className="py-8 text-center text-sm text-muted-foreground">Выберите версию для просмотра</div>
                ) : (
                  <div className="space-y-3">
                    {previewSections.map((section, idx) => (
                      <div key={`${section.section_id}-${idx}`} className="rounded-md border p-3">
                        <div className="mb-1 text-sm font-medium">{idx + 1}. {section.title}</div>
                        <div className="line-clamp-4 whitespace-pre-wrap text-xs text-muted-foreground">{section.content_md || "Пусто"}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="flex items-center justify-between border-t px-3 py-2">
                <p className="text-xs text-amber-600">При восстановлении несохраненные изменения будут потеряны.</p>
                <div className="flex items-center gap-2">
                  <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => setVersionsOpen(false)}>
                    Закрыть
                  </Button>
                  <Button
                    size="sm"
                    className="h-7 text-xs"
                    disabled={!selectedVersionId || restoringVersion}
                    onClick={() => {
                      void handleRestoreSelectedVersion()
                    }}
                  >
                    {restoringVersion ? <Loader2 className="size-3.5 animate-spin" /> : "Восстановить версию"}
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
