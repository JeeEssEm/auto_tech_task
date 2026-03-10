import { Bot, Check, Loader2 } from "lucide-react"

import { cn } from "@/lib/utils"
import type { GenerationStep } from "../lib/types"

type ThinkingIndicatorProps = {
  steps: GenerationStep[]
}

export function ThinkingIndicator({ steps }: ThinkingIndicatorProps) {
  const allDone = steps.length > 0 && steps.every(s => s.state === "done")

  return (
    <div className="flex w-full gap-3 justify-start">
      <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary mt-1">
        <Bot className="size-5" />
      </div>

      <div className="max-w-[85%] md:max-w-[75%]">
        <div
          className={cn(
            "rounded-2xl rounded-tl-sm border bg-muted/50 px-4 py-3 shadow-sm transition-opacity duration-500",
            allDone && "opacity-60",
          )}
        >
          {/* Header */}
          <div className="flex items-center gap-2 mb-2">
            {!allDone ? (
              <Loader2 className="size-4 animate-spin text-primary" />
            ) : (
              <Check className="size-4 text-emerald-500" />
            )}
            <span className="text-sm font-medium">
              {allDone ? "Готово" : "Думаю…"}
            </span>
          </div>

          {/* Steps */}
          <div className="space-y-1.5">
            {steps.map((step, i) => (
              <div
                key={step.status}
                className={cn(
                  "flex items-center gap-2 text-[13px] transition-all duration-300",
                  step.state === "done" && "text-muted-foreground",
                  step.state === "active" && "text-foreground",
                )}
                style={{ animationDelay: `${i * 50}ms` }}
              >
                {step.state === "done" ? (
                  <Check className="size-3.5 shrink-0 text-emerald-500" />
                ) : (
                  <Loader2 className="size-3.5 shrink-0 text-primary animate-spin" />
                )}
                <span>{step.label}</span>
                {step.state === "active" && (
                  <span className="text-muted-foreground animate-pulse">…</span>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
