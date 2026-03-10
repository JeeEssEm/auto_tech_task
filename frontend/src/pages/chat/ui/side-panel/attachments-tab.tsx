import { FileAudio, FileImage, FileText, FileVideo } from "lucide-react"

import { cn } from "@/lib/utils"
import { formatFileSize } from "../../lib/format"
import type { ParsedAttachment } from "../../lib/types"

type AttachmentsTabProps = {
  attachments: ParsedAttachment[]
  selected: ParsedAttachment | null
  onSelect: (att: ParsedAttachment) => void
}

function fileIcon(fileType: string) {
  if (fileType.startsWith("audio/")) return FileAudio
  if (fileType.startsWith("video/")) return FileVideo
  if (fileType.startsWith("image/")) return FileImage
  return FileText
}

export function AttachmentsTab({ attachments, selected, onSelect }: AttachmentsTabProps) {
  return (
    <div className="flex flex-col h-full">
      {/* File list */}
      <div className="flex-1 min-h-0 overflow-y-auto border-b chat-scrollbar">
        {attachments.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-muted-foreground p-4">
            Нет файлов
          </div>
        ) : (
          <div className="flex flex-col">
            {attachments.map(att => {
              const Icon = fileIcon(att.file_type)
              const isActive = selected?.key === att.key
              return (
                <button
                  key={att.key}
                  onClick={() => onSelect(att)}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2.5 text-left text-sm transition-colors border-b last:border-b-0",
                    isActive
                      ? "bg-accent text-accent-foreground"
                      : "hover:bg-muted/50",
                  )}
                >
                  <Icon className="size-4 shrink-0 text-muted-foreground" />
                  <div className="flex flex-col min-w-0 flex-1">
                    <span className="truncate font-medium text-xs">{att.file_name}</span>
                    <span className="text-[10px] text-muted-foreground">
                      {formatFileSize(att.file_size)}
                    </span>
                  </div>
                </button>
              )
            })}
          </div>
        )}
      </div>

      {/* Detail view */}
      <div className="flex-1 min-h-0 overflow-y-auto p-3 chat-scrollbar">
        {selected ? (
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              {(() => {
                const Icon = fileIcon(selected.file_type)
                return <Icon className="size-4 shrink-0 text-primary" />
              })()}
              <span className="font-medium text-sm truncate">{selected.file_name}</span>
            </div>
            <div className="flex gap-4 text-[11px] text-muted-foreground">
              <span>{formatFileSize(selected.file_size)}</span>
              <span>{selected.file_type.split("/").pop()}</span>
            </div>
            <div className="mt-2">
              <p className="text-[11px] font-medium text-muted-foreground mb-1">Расшифровка</p>
              <p className="text-xs leading-relaxed text-foreground/90">{selected.transcript}</p>
            </div>
          </div>
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
            Выберите файл
          </div>
        )}
      </div>
    </div>
  )
}
