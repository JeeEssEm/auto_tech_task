import { useCallback, useEffect } from "react"
import { useEditor, EditorContent } from "@tiptap/react"
import StarterKit from "@tiptap/starter-kit"
import Placeholder from "@tiptap/extension-placeholder"
import { Markdown } from "tiptap-markdown"
import {
  Bold,
  Italic,
  List,
  ListOrdered,
  Heading2,
  Heading3,
  Undo,
  Redo,
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
      Markdown,
    ],
    content: value,
    editable,
    onUpdate: ({ editor }) => {
      const md = editor.storage.markdown.getMarkdown()
      onChange(md)
    },
  })

  // Sync external value changes (e.g. on cancel)
  useEffect(() => {
    if (!editor) return
    const current = editor.storage.markdown.getMarkdown()
    if (current !== value) {
      editor.commands.setContent(value)
    }
  }, [value, editor])

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
          "prose prose-sm dark:prose-invert max-w-none px-3 py-2",
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
