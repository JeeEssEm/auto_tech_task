import { useCallback, useEffect, useState } from "react"
import { useEditor, EditorContent } from "@tiptap/react"
import StarterKit from "@tiptap/starter-kit"
import Placeholder from "@tiptap/extension-placeholder"
import Underline from "@tiptap/extension-underline"
import Highlight from "@tiptap/extension-highlight"
import Link from "@tiptap/extension-link"
import { Table } from "@tiptap/extension-table"
import TableRow from "@tiptap/extension-table-row"
import TableCell from "@tiptap/extension-table-cell"
import TableHeader from "@tiptap/extension-table-header"
import { Markdown } from "tiptap-markdown"
import {
  Bold,
  Italic,
  Underline as UnderlineIcon,
  Strikethrough,
  Highlighter,
  List,
  ListOrdered,
  Heading2,
  Heading3,
  Link as LinkIcon,
  Table as TableIcon,
  Undo,
  Redo,
  Plus,
  Minus,
  Trash2,
  Rows3,
  Columns3,
} from "lucide-react"

import { cn } from "@/lib/utils"

type RichTextEditorProps = {
  value: string
  onChange: (markdown: string) => void
  placeholder?: string
  className?: string
  editable?: boolean
  minHeight?: string
}

export function RichTextEditor({
  value,
  onChange,
  placeholder = "Начните вводить текст…",
  className,
  editable = true,
  minHeight = "120px",
}: RichTextEditorProps) {
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: { levels: [2, 3] },
      }),
      Placeholder.configure({ placeholder }),
      Underline,
      Highlight.configure({ multicolor: false }),
      Link.configure({
        openOnClick: false,
        HTMLAttributes: { rel: "noopener noreferrer", target: "_blank" },
      }),
      Table.configure({ resizable: false }),
      TableRow,
      TableCell,
      TableHeader,
      Markdown.configure({
        html: false,
        transformPastedText: true,
        transformCopiedText: true,
      }),
    ],
    content: "",
    editable,
    onUpdate: ({ editor }) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const md = (editor.storage as Record<string, any>).markdown.getMarkdown()
      onChange(md)
    },
  })

  // Sync external value changes
  useEffect(() => {
    if (!editor) return
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const current = (editor.storage as Record<string, any>).markdown.getMarkdown()
    if (current !== value) {
      editor.commands.setContent(value)
    }
  }, [value, editor])

  const [linkUrl, setLinkUrl] = useState("")
  const [showLinkInput, setShowLinkInput] = useState(false)

  const handleSetLink = useCallback(() => {
    if (!editor) return
    if (!linkUrl.trim()) {
      editor.chain().focus().extendMarkRange("link").unsetLink().run()
    } else {
      const url = linkUrl.startsWith("http") ? linkUrl : `https://${linkUrl}`
      editor.chain().focus().extendMarkRange("link").setLink({ href: url }).run()
    }
    setShowLinkInput(false)
    setLinkUrl("")
  }, [editor, linkUrl])

  const handleInsertTable = useCallback(() => {
    if (!editor) return
    editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()
  }, [editor])

  if (!editor) return null

  return (
    <div className={cn("rounded-md border bg-background", className)}>
      {/* Toolbar */}
      {editable && (
        <div className="flex items-center gap-0.5 border-b px-1 py-1 flex-wrap">
          <ToolbarButton
            active={editor.isActive("bold")}
            onClick={() => editor.chain().focus().toggleBold().run()}
            title="Жирный"
          >
            <Bold className="size-3.5" />
          </ToolbarButton>
          <ToolbarButton
            active={editor.isActive("italic")}
            onClick={() => editor.chain().focus().toggleItalic().run()}
            title="Курсив"
          >
            <Italic className="size-3.5" />
          </ToolbarButton>
          <ToolbarButton
            active={editor.isActive("underline")}
            onClick={() => editor.chain().focus().toggleUnderline().run()}
            title="Подчёркивание"
          >
            <UnderlineIcon className="size-3.5" />
          </ToolbarButton>
          <ToolbarButton
            active={editor.isActive("highlight")}
            onClick={() => editor.chain().focus().toggleHighlight().run()}
            title="Выделение"
          >
            <Highlighter className="size-3.5" />
          </ToolbarButton>

          <div className="w-px h-4 bg-border mx-0.5" />

          <ToolbarButton
            active={editor.isActive("heading", { level: 2 })}
            onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
            title="Заголовок 2"
          >
            <Heading2 className="size-3.5" />
          </ToolbarButton>
          <ToolbarButton
            active={editor.isActive("heading", { level: 3 })}
            onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
            title="Заголовок 3"
          >
            <Heading3 className="size-3.5" />
          </ToolbarButton>

          <div className="w-px h-4 bg-border mx-0.5" />

          <ToolbarButton
            active={editor.isActive("bulletList")}
            onClick={() => editor.chain().focus().toggleBulletList().run()}
            title="Маркированный список"
          >
            <List className="size-3.5" />
          </ToolbarButton>
          <ToolbarButton
            active={editor.isActive("orderedList")}
            onClick={() => editor.chain().focus().toggleOrderedList().run()}
            title="Нумерованный список"
          >
            <ListOrdered className="size-3.5" />
          </ToolbarButton>

          <div className="w-px h-4 bg-border mx-0.5" />

          <div className="relative">
            <ToolbarButton
              active={editor.isActive("link")}
              onClick={() => {
                if (editor.isActive("link")) {
                  editor.chain().focus().unsetLink().run()
                } else {
                  const prev = editor.getAttributes("link").href ?? ""
                  setLinkUrl(prev)
                  setShowLinkInput(true)
                }
              }}
              title="Ссылка"
            >
              <LinkIcon className="size-3.5" />
            </ToolbarButton>
            {showLinkInput && (
              <div className="absolute left-0 top-full mt-1 z-20 flex items-center gap-1 rounded-md border bg-popover p-1.5 shadow-md">
                <input
                  className="rounded border bg-background px-2 py-0.5 text-xs w-48 focus:outline-none focus:ring-1 focus:ring-ring"
                  placeholder="https://…"
                  value={linkUrl}
                  onChange={e => setLinkUrl(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === "Enter") handleSetLink()
                    if (e.key === "Escape") setShowLinkInput(false)
                  }}
                  autoFocus
                />
                <button className="rounded bg-primary px-2 py-0.5 text-xs text-primary-foreground" onClick={handleSetLink}>OK</button>
                <button className="rounded px-1.5 py-0.5 text-xs text-muted-foreground hover:text-foreground" onClick={() => setShowLinkInput(false)}>✕</button>
              </div>
            )}
          </div>

          <ToolbarButton
            onClick={handleInsertTable}
            title="Вставить таблицу"
          >
            <TableIcon className="size-3.5" />
          </ToolbarButton>

          {/* Table controls — visible only when cursor is inside a table */}
          {editor.isActive("table") && (
            <>
              <div className="w-px h-4 bg-border mx-0.5" />
              <ToolbarButton
                onClick={() => editor.chain().focus().addRowAfter().run()}
                title="Добавить строку снизу"
              >
                <span className="flex items-center gap-px"><Rows3 className="size-3" /><Plus className="size-2.5" /></span>
              </ToolbarButton>
              <ToolbarButton
                onClick={() => editor.chain().focus().deleteRow().run()}
                title="Удалить строку"
              >
                <span className="flex items-center gap-px"><Rows3 className="size-3" /><Minus className="size-2.5" /></span>
              </ToolbarButton>
              <ToolbarButton
                onClick={() => editor.chain().focus().addColumnAfter().run()}
                title="Добавить столбец справа"
              >
                <span className="flex items-center gap-px"><Columns3 className="size-3" /><Plus className="size-2.5" /></span>
              </ToolbarButton>
              <ToolbarButton
                onClick={() => editor.chain().focus().deleteColumn().run()}
                title="Удалить столбец"
              >
                <span className="flex items-center gap-px"><Columns3 className="size-3" /><Minus className="size-2.5" /></span>
              </ToolbarButton>
              <ToolbarButton
                onClick={() => editor.chain().focus().deleteTable().run()}
                title="Удалить таблицу"
              >
                <Trash2 className="size-3.5 text-destructive" />
              </ToolbarButton>
            </>
          )}

          <div className="w-px h-4 bg-border mx-0.5" />

          <ToolbarButton
            onClick={() => editor.chain().focus().undo().run()}
            disabled={!editor.can().undo()}
            title="Отменить"
          >
            <Undo className="size-3.5" />
          </ToolbarButton>
          <ToolbarButton
            onClick={() => editor.chain().focus().redo().run()}
            disabled={!editor.can().redo()}
            title="Повторить"
          >
            <Redo className="size-3.5" />
          </ToolbarButton>
        </div>
      )}

      {/* Editor area */}
      <EditorContent
        editor={editor}
        className={cn(
          "max-w-none px-3 py-2",
          "[&_.tiptap]:outline-none [&_.tiptap]:min-h-[var(--min-h)]",
          "[&_.tiptap_p.is-editor-empty:first-child::before]:text-muted-foreground",
          "[&_.tiptap_p.is-editor-empty:first-child::before]:content-[attr(data-placeholder)]",
          "[&_.tiptap_p.is-editor-empty:first-child::before]:float-left",
          "[&_.tiptap_p.is-editor-empty:first-child::before]:h-0",
          "[&_.tiptap_p.is-editor-empty:first-child::before]:pointer-events-none",
        )}
        style={{ "--min-h": minHeight } as React.CSSProperties}
      />
    </div>
  )
}

function ToolbarButton({
  active,
  disabled,
  onClick,
  title,
  children,
}: {
  active?: boolean
  disabled?: boolean
  onClick: () => void
  title: string
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onMouseDown={e => e.preventDefault()}
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={cn(
        "inline-flex items-center justify-center rounded px-1.5 py-1 text-muted-foreground transition-colors",
        "hover:bg-accent hover:text-foreground",
        "disabled:opacity-40 disabled:pointer-events-none",
        active && "bg-accent text-foreground",
      )}
    >
      {children}
    </button>
  )
}
