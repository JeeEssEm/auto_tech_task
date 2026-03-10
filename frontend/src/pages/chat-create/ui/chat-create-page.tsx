import { useEffect, useRef, useState } from "react"
import React from "react"
import { ArrowUp, FileText, Loader2, Paperclip, X } from "lucide-react"
import { useNavigate } from "react-router-dom"
import { toast } from "sonner"

import { mockApi } from "@/shared/api/mock-service"
import { chatApi, ChatTemplate } from "@/shared/api/chat-service"
import { fileApi } from "@/shared/api/file-service"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"

type FileItem = {
  file: File
  id?: string
  status: 'uploading' | 'success' | 'error'
  error?: string
}

const TEMPLATE_MAP: Record<string, ChatTemplate> = {
  "ГОСТ 19": ChatTemplate.GOST19,
  "Свободный": ChatTemplate.FREE,
  "IT-проект": ChatTemplate.IT_PROJECT,
  "Строительный проект": ChatTemplate.CONSTRUCTION_PROJECT,
  "Инженерный проект": ChatTemplate.ENGINEERING_PROJECT,
}

export function ChatCreatePage() {
  const [templates, setTemplates] = useState<
    Awaited<ReturnType<typeof mockApi.getChatTemplates>> | undefined
  >()
  const [query, setQuery] = useState("")
  const [projectName, setProjectName] = useState("")
  const [selectedTemplateTitle, setSelectedTemplateTitle] = useState<string | null>(null)
  const [files, setFiles] = useState<FileItem[]>([])
  const [isCreating, setIsCreating] = useState(false)

  const navigate = useNavigate()
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    mockApi.getChatTemplates().then((data) => {
        setTemplates(data)
        // Select Free template by default if available
        const defaultTemplate = data.find(t => t.title === "Свободный")
        if (defaultTemplate) {
            setSelectedTemplateTitle(defaultTemplate.title)
        }
    })
  }, [])

  const handleAttachClick = () => {
    fileInputRef.current?.click()
  }

  const uploadFile = async (file: File) => {
    // Add to list with uploading status
    const newItem: FileItem = { file, status: 'uploading' }

    // Use functional update to append new item
    setFiles((prev) => [...prev, newItem])

    try {
      const id = await fileApi.uploadFile(file)
      // Update item with success
      setFiles((prev) => 
        prev.map((item) => item.file === file ? { ...item, status: 'success', id } : item)
      )
    } catch (error) {
      // Update item with error
      const message = error instanceof Error ? error.message : "Unknown error"
      setFiles((prev) => 
        prev.map((item) => item.file === file ? { ...item, status: 'error', error: message } : item)
      )
      toast.error(`Ошибка загрузки ${file.name}: ${message}`)
    }
  }

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
      const newFiles = Array.from(event.target.files)
      // Upload each file
      newFiles.forEach(file => uploadFile(file))
    }
    // Reset input
    if (fileInputRef.current) {
        fileInputRef.current.value = ""
    }
  }

  const removeFile = (fileItem: FileItem) => {
    setFiles(files.filter((f) => f !== fileItem))
  }

  const handleTemplateSelect = (templateTitle: string) => {
    if (selectedTemplateTitle === templateTitle) {
      setSelectedTemplateTitle(null)
    } else {
      setSelectedTemplateTitle(templateTitle)
    }
  }

  const handleCreateChat = async () => {
    if (!query.trim() && files.length === 0) return

    // Check if any file is still uploading
    if (files.some(f => f.status === 'uploading')) {
        toast.warning("Дождитесь загрузки файлов")
        return
    }

    // Check for errors?
    if (files.some(f => f.status === 'error')) {
         toast.warning("Некоторые файлы не загрузились. Удалите их перед созданием чата.")
         return
    }

    setIsCreating(true)
    try {
        const templateType = selectedTemplateTitle 
            ? TEMPLATE_MAP[selectedTemplateTitle] 
            : ChatTemplate.FREE

        // Collect attachment IDs
        const attachmentIds = files
            .filter(f => f.status === 'success' && f.id)
            .map(f => f.id!)

        const chat = await chatApi.createChat({
            name: projectName || "Новый проект",
            init_user_message: query,
            template_type: templateType,
            attachment_ids: attachmentIds
        })

        navigate(`/chats/${chat}`)
        toast.success("Чат создан!")
    } catch (error) {
        const message = error instanceof Error ? error.message : "Ошибка создания чата"
        toast.error(message)
    } finally {
        setIsCreating(false)
    }
  }

  // Derived state for disabled button
  const isSubmitDisabled = !query.trim() && files.length === 0
  const isUploading = files.some(f => f.status === 'uploading')

  return (
    <div className="px-6 py-8">
    <div className="flex min-h-[calc(100vh-8rem)] flex-col justify-center gap-8">
      <div className="mx-auto w-full max-w-3xl space-y-2 text-center">
        <h1 className="text-3xl font-semibold md:text-4xl">
          Что будем проектировать сегодня?
        </h1>
        <p className="text-muted-foreground">
          Загрузите документы или опишите идею, чтобы получить ТЗ.
        </p>
      </div>

      <div className="mx-auto w-full max-w-3xl">
        <div className="relative flex flex-col rounded-2xl border bg-background p-4 shadow-lg ring-offset-background focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2">
          {/* Top minimal inputs */}
          <div className="pt-3 mb-2">
             <Input 
                className="h-auto border-0 py-2 px-2 text-2xl font-medium placeholder:text-muted-foreground/50 focus-visible:ring-0 shadow-none"
                placeholder="Название проекта..."
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
             />
          </div>

          {/* Files display */}
          {files.length > 0 && (
            <div className="flex flex-wrap gap-2 px-4 py-2">
              {files.map((item, index) => (
                <div
                  key={`${item.file.name}-${index}`}
                  className={cn(
                      "flex items-center gap-2 rounded-md border px-2 py-1 text-xs transition-colors",
                      item.status === 'error' ? "bg-destructive/10 border-destructive/20 text-destructive" : "bg-muted/40 text-foreground",
                      item.status === 'uploading' && "opacity-70"
                  )}
                  title={item.error}
                >
                  <FileText className="size-3" />
                  <span className="max-w-[150px] truncate">{item.file.name}</span>
                  {item.status === 'uploading' && <Loader2 className="size-3 animate-spin"/>}
                  <button
                    onClick={() => removeFile(item)}
                    className="ml-1 text-muted-foreground hover:text-destructive"
                  >
                    <X className="size-3" />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Main Text Area */}
          <Textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Опишите цель продукта, целевую аудиторию и основные ограничения..."
            className="min-h-[120px] resize-none border-0 px-4 py-3 shadow-none focus-visible:ring-0 text-base"
          />

          {/* Bottom Toolbar */}
          <div className="flex items-center justify-between px-2 py-2">
            <div className="flex items-center gap-2">
              <input
                type="file"
                multiple
                className="hidden"
                ref={fileInputRef}
                onChange={handleFileChange}
              />
              <Button
                variant="ghost"
                size="icon"
                className="rounded-full text-muted-foreground hover:bg-muted"
                onClick={handleAttachClick}
                disabled={isCreating}
                title="Прикрепить файл"
              >
                <Paperclip className="size-5" />
              </Button>
              <div className="h-4 w-px bg-border" />
              <Button variant="ghost" size="sm" className="h-8 rounded-full text-xs text-muted-foreground">
                + Формат результата
              </Button>
            </div>
            <Button
              size="icon"
              className="rounded-full transition-all"
              disabled={isSubmitDisabled || isUploading || isCreating}
              onClick={handleCreateChat}
            >
              {isCreating ? <Loader2 className="size-5 animate-spin" /> : <ArrowUp className="size-5" />}
            </Button>
          </div>
        </div>
      </div>

      {/* Templates / Suggestions */}
      <div className="mx-auto w-full max-w-3xl">
        <div className="mb-2 text-sm font-medium text-muted-foreground">
          Выберите шаблон (опционально):
        </div>
        <div className="flex flex-wrap justify-center gap-3">
          {(templates ?? []).map((template) => {
            const isSelected = selectedTemplateTitle === template.title
            return (
              <Card
                key={template.title}
                className={cn(
                  "group cursor-pointer border bg-muted/20 p-4 transition-colors hover:bg-background hover:border-primary/50 w-full sm:w-[calc(50%-6px)] md:w-[calc(33.333%-8px)]",
                  isSelected && "border-primary bg-background ring-1 ring-primary"
                )}
                onClick={() => handleTemplateSelect(template.title)}
              >
                <div className="space-y-1">
                  <h3 className={cn("text-sm font-medium leading-none group-hover:text-primary", isSelected && "text-primary")}>
                    {template.title}
                  </h3>
                  <p className="text-xs text-muted-foreground line-clamp-2">
                    {template.description}
                  </p>
                </div>
              </Card>
            )
          })}
        </div>
      </div>
    </div>
    </div>
  )
}
