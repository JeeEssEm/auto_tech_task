import { Bot, CheckCircle2, Clock, FileText, Loader2, User, XCircle } from "lucide-react"

import { cn } from "@/lib/utils"
import type { Message } from "@/shared/api/chat-service"
import type { ParsingStatus } from "@/shared/ws/types"
import { formatFileSize } from "../lib/format"

type MessageBubbleProps = {
  message: Message
  parsingStatuses: Map<string, ParsingStatus>
  onFileClick: (fileId: string, fileName: string) => void
}

export function MessageBubble({ message, parsingStatuses, onFileClick }: MessageBubbleProps) {
  const isUser = message.sender === "user"

  return (
    <div
      className={cn(
        "flex w-full gap-3 transition-opacity duration-500",
        isUser ? "justify-end" : "justify-start",
      )}
    >
      {!isUser && (
        <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary mt-1">
          <Bot className="size-5" />
        </div>
      )}

      <div
        className={cn(
          "flex flex-col gap-2 max-w-[85%] md:max-w-[75%]",
          isUser ? "items-end" : "items-start",
        )}
      >
        {message.attachments.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-1">
            {message.attachments.map((att, i) => {
              const status = parsingStatuses.get(att.key)
              return (
                <div
                  key={i}
                  className={cn(
                    "flex flex-col rounded-md border p-2 text-xs shadow-sm max-w-[220px] transition-all overflow-hidden",
                    !status && "bg-background/50 hover:bg-accent/50 cursor-pointer",
                    status === "PENDING" && "border-border bg-muted/30",
                    status === "IN_PROCESS" && "border-primary/40 bg-primary/5",
                    status === "SUCCESS" && "border-emerald-500/40 bg-emerald-500/5",
                    status === "FAILED" && "border-destructive/40 bg-destructive/5",
                    (!status || status === "SUCCESS") && "cursor-pointer",
                  )}
                  title={att.file_name || att.key}
                  onClick={() => {
                    if (!status || status === "SUCCESS") {
                      onFileClick(att.key, att.file_name || att.key)
                    }
                  }}
                >
                  <div className="flex items-center gap-2">
                    <FileText className="size-4 shrink-0 text-primary" />
                    <div className="flex flex-col overflow-hidden text-left flex-1 min-w-0">
                      <span className="truncate font-medium">{att.file_name || att.key}</span>
                      <span className="text-[10px] text-muted-foreground">
                        {formatFileSize(att.file_size)}
                      </span>
                    </div>
                    {status === "PENDING" && (
                      <Clock className="size-3.5 shrink-0 text-muted-foreground" />
                    )}
                    {status === "IN_PROCESS" && (
                      <Loader2 className="size-3.5 shrink-0 text-primary animate-spin" />
                    )}
                    {status === "SUCCESS" && (
                      <CheckCircle2 className="size-3.5 shrink-0 text-emerald-500" />
                    )}
                    {status === "FAILED" && (
                      <XCircle className="size-3.5 shrink-0 text-destructive" />
                    )}
                  </div>

                  {status && (
                    <div className="h-1 w-full overflow-hidden rounded-full bg-muted/60 mt-1.5">
                      {status === "IN_PROCESS" ? (
                        <div
                          className="h-full w-2/5 rounded-full bg-primary"
                          style={{ animation: "progress-indeterminate 1.4s ease-in-out infinite" }}
                        />
                      ) : status === "PENDING" ? (
                        <div className="h-full w-[10%] rounded-full bg-muted-foreground/40 animate-pulse" />
                      ) : status === "SUCCESS" ? (
                        <div className="h-full w-full rounded-full bg-emerald-500 transition-all duration-500" />
                      ) : (
                        <div className="h-full w-full rounded-full bg-destructive transition-all duration-500" />
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}

        <div
          className={cn(
            "rounded-2xl px-4 py-3 text-sm shadow-sm whitespace-pre-wrap leading-relaxed",
            isUser
              ? "bg-primary text-primary-foreground rounded-tr-sm"
              : "bg-muted/50 text-foreground border rounded-tl-sm",
          )}
        >
          {message.text}
        </div>

        <span className="text-[10px] text-muted-foreground px-1 select-none">
          {new Date(message.created_at).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </span>
      </div>

      {isUser && (
        <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-secondary text-secondary-foreground mt-1">
          <User className="size-5" />
        </div>
      )}
    </div>
  )
}
