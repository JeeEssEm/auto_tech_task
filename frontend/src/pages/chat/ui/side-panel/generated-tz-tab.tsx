import { FileCheck } from "lucide-react"

import { cn } from "@/lib/utils"
import type { GeneratedTechnicalTask } from "../../lib/types"

type GeneratedTzTabProps = {
  tasks: GeneratedTechnicalTask[]
  selected: GeneratedTechnicalTask | null
  onSelect: (task: GeneratedTechnicalTask) => void
}

export function GeneratedTzTab({ tasks, selected, onSelect }: GeneratedTzTabProps) {
  return (
    <div className="flex flex-col h-full">
      {/* Version list */}
      <div className="border-b overflow-y-auto max-h-[40%] chat-scrollbar">
        {tasks.length === 0 ? (
          <div className="flex h-24 items-center justify-center text-sm text-muted-foreground">
            Нет сгенерированных ТЗ
          </div>
        ) : (
          <div className="flex flex-col">
            {tasks.map(task => {
              const isActive = selected?.version === task.version
              return (
                <button
                  key={task.version}
                  onClick={() => onSelect(task)}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2.5 text-left text-sm transition-colors border-b last:border-b-0",
                    isActive
                      ? "bg-accent text-accent-foreground"
                      : "hover:bg-muted/50",
                  )}
                >
                  <FileCheck className="size-4 shrink-0 text-muted-foreground" />
                  <div className="flex flex-col min-w-0 flex-1">
                    <span className="truncate font-medium text-xs">{task.name}</span>
                    <span className="text-[10px] text-muted-foreground">
                      Версия {task.version} · {task.technical_task_template}
                    </span>
                  </div>
                </button>
              )
            })}
          </div>
        )}
      </div>

      {/* Preview */}
      <div className="flex-1 min-h-0 overflow-y-auto p-3 chat-scrollbar">
        {selected ? (
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <pre className="whitespace-pre-wrap text-xs leading-relaxed font-sans bg-transparent p-0 m-0 border-0">
              {selected.content}
            </pre>
          </div>
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
            Выберите версию ТЗ
          </div>
        )}
      </div>
    </div>
  )
}
