import { CheckCircle2, FileText, Loader2, XCircle, Clock, X } from "lucide-react"

import { cn } from "@/lib/utils"
import type { ParsingStatus } from "@/shared/ws/types"
import type { ParsingEntry } from "../lib/types"

type ParsingStatusPanelProps = {
  entries: ParsingEntry[]
  onDismiss: (attachmentId: string) => void
}

const statusConfig: Record<
  ParsingStatus,
  {
    label: string
    icon: React.ComponentType<{ className?: string }>
    barClass: string
    cardClass: string
    animate: boolean
  }
> = {
  PENDING: {
    label: "Ожидание…",
    icon: Clock,
    barClass: "bg-muted-foreground/40",
    cardClass: "border-border",
    animate: false,
  },
  IN_PROCESS: {
    label: "Обработка…",
    icon: Loader2,
    barClass: "bg-primary",
    cardClass: "border-primary/30",
    animate: true,
  },
  SUCCESS: {
    label: "Готово",
    icon: CheckCircle2,
    barClass: "bg-emerald-500",
    cardClass: "border-emerald-500/30",
    animate: false,
  },
  FAILED: {
    label: "Ошибка",
    icon: XCircle,
    barClass: "bg-destructive",
    cardClass: "border-destructive/30",
    animate: false,
  },
}

export function ParsingStatusPanel({ entries, onDismiss }: ParsingStatusPanelProps) {
  if (entries.length === 0) return null

  return (
    <div className="mx-auto w-full max-w-4xl px-4">
      <div className="flex gap-2 overflow-x-auto pb-1 pt-2 scrollbar-none">
        {entries.map(entry => {
          const config = statusConfig[entry.status]
          const Icon = config.icon

          return (
            <div
              key={entry.attachmentId}
              className={cn(
                "flex flex-col gap-1.5 rounded-lg border bg-background/80 backdrop-blur-sm px-3 py-2 min-w-[180px] max-w-[220px] shadow-sm transition-all duration-300",
                config.cardClass,
              )}
            >
              {/* Header: file name + dismiss */}
              <div className="flex items-center gap-1.5">
                <FileText className="size-3.5 shrink-0 text-muted-foreground" />
                <span className="truncate text-xs font-medium">{entry.fileName}</span>
                {entry.status === "FAILED" && (
                  <button
                    onClick={() => onDismiss(entry.attachmentId)}
                    className="ml-auto shrink-0 text-muted-foreground hover:text-destructive transition-colors"
                  >
                    <X className="size-3" />
                  </button>
                )}
              </div>

              {/* Status line */}
              <div className="flex items-center gap-1.5">
                <Icon
                  className={cn(
                    "size-3.5 shrink-0",
                    entry.status === "IN_PROCESS" && "animate-spin text-primary",
                    entry.status === "PENDING" && "text-muted-foreground",
                    entry.status === "SUCCESS" && "text-emerald-500",
                    entry.status === "FAILED" && "text-destructive",
                  )}
                />
                <span
                  className={cn(
                    "text-[11px]",
                    entry.status === "SUCCESS" && "text-emerald-500",
                    entry.status === "FAILED" && "text-destructive",
                    entry.status === "IN_PROCESS" && "text-primary",
                    entry.status === "PENDING" && "text-muted-foreground",
                  )}
                >
                  {config.label}
                </span>
              </div>

              {/* Progress bar */}
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted/60">
                {config.animate ? (
                  <div
                    className={cn("h-full w-2/5 rounded-full", config.barClass)}
                    style={{ animation: "progress-indeterminate 1.4s ease-in-out infinite" }}
                  />
                ) : (
                  <div
                    className={cn(
                      "h-full rounded-full transition-all duration-500",
                      config.barClass,
                      entry.status === "PENDING" && "w-[10%] animate-pulse",
                      (entry.status === "SUCCESS" || entry.status === "FAILED") && "w-full",
                    )}
                  />
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
