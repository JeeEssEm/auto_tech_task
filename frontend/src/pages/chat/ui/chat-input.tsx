import { ArrowUp, FileText, Loader2, Paperclip, X } from "lucide-react"
import React from "react"

import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"
import type { FileItem } from "../lib/types"

type ChatInputProps = {
  inputValue: string
  isSending: boolean
  isSubmitDisabled: boolean
  files: FileItem[]
  fileInputRef: React.RefObject<HTMLInputElement | null>
  onInput: (e: React.FormEvent<HTMLTextAreaElement>) => void
  onSend: () => void
  onAttachClick: () => void
  onFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  onRemoveFile: (item: FileItem) => void
}

export function ChatInput({
  inputValue,
  isSending,
  isSubmitDisabled,
  files,
  fileInputRef,
  onInput,
  onSend,
  onAttachClick,
  onFileChange,
  onRemoveFile,
}: ChatInputProps) {
  return (
    <div className="p-4 bg-background/80 backdrop-blur-sm border-t mt-auto">
      <div className="mx-auto w-full max-w-3xl xl:max-w-4xl relative flex flex-col gap-2 rounded-xl border bg-background p-2 shadow-sm focus-within:ring-1 focus-within:ring-ring transition-shadow">
        {files.length > 0 && (
          <div className="flex flex-wrap gap-2 px-2 pt-2">
            {files.map((item, index) => (
              <div
                key={`${item.file.name}-${index}`}
                className={cn(
                  "flex items-center gap-2 rounded-md border px-2 py-1 text-xs transition-colors",
                  item.status === "error"
                    ? "bg-destructive/10 border-destructive/20 text-destructive"
                    : "bg-muted/40 text-foreground",
                  item.status === "uploading" && "opacity-70",
                )}
                title={item.error}
              >
                <FileText className="size-3" />
                <span className="max-w-[150px] truncate">{item.file.name}</span>
                {item.status === "uploading" && <Loader2 className="size-3 animate-spin" />}
                <button
                  onClick={() => onRemoveFile(item)}
                  className="ml-1 text-muted-foreground hover:text-destructive"
                >
                  <X className="size-3" />
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="flex items-end gap-2">
          <input
            type="file"
            multiple
            className="hidden"
            ref={fileInputRef}
            onChange={onFileChange}
          />
          <Button
            variant="ghost"
            size="icon"
            className="h-9 w-9 shrink-0 text-muted-foreground rounded-full hover:bg-muted"
            onClick={onAttachClick}
            disabled={isSending}
          >
            <Paperclip className="size-5" />
          </Button>
          <Textarea
            value={inputValue}
            onInput={onInput}
            placeholder="Сообщение..."
            className="min-h-[36px] max-h-[200px] w-full resize-none border-0 bg-transparent p-2 focus-visible:ring-0 shadow-none text-sm leading-relaxed"
            rows={1}
            onKeyDown={e => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault()
                if (!isSubmitDisabled) onSend()
              }
            }}
          />
          <Button
            size="icon"
            className="h-9 w-9 shrink-0 rounded-full transition-all"
            disabled={isSubmitDisabled}
            onClick={onSend}
          >
            {isSending ? (
              <Loader2 className="size-5 animate-spin" />
            ) : (
              <ArrowUp className="size-5" />
            )}
          </Button>
        </div>
      </div>
    </div>
  )
}
