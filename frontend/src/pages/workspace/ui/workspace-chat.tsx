import { useEffect, useRef, useState } from "react"
import { ArrowUp, Bot, MessageSquareText, User, X } from "lucide-react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import type { WorkspaceChatMessage } from "../lib/types"

type WorkspaceChatProps = {
  messages: WorkspaceChatMessage[]
  context: string | null
  onSend: (text: string) => void
  onClose: () => void
}

const quickActions = [
  "Уточни этот раздел",
  "Добавь требование",
  "Перегенерируй",
  "Найди пробелы в ТЗ",
]

export function WorkspaceChat({ messages, context, onSend, onClose }: WorkspaceChatProps) {
  const [input, setInput] = useState("")
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  const handleSend = () => {
    if (!input.trim()) return
    onSend(input.trim())
    setInput("")
  }

  return (
    <div className="flex flex-col h-full border-l bg-background">
      {/* Header */}
      <div className="flex items-center justify-between border-b px-3 py-2.5 shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <MessageSquareText className="size-4 text-primary shrink-0" />
          <span className="text-sm font-medium truncate">Ассистент</span>
        </div>
        <Button variant="ghost" size="icon" className="size-7 shrink-0" onClick={onClose}>
          <X className="size-4" />
        </Button>
      </div>

      {/* Context indicator */}
      {context && (
        <div className="border-b px-3 py-1.5 text-[11px] text-muted-foreground bg-muted/30">
          Контекст: <span className="font-medium text-foreground/80">§{context}</span>
        </div>
      )}

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-3 chat-scrollbar">
        {messages.map(msg => (
          <div key={msg.id} className={cn("flex gap-2", msg.sender === "user" ? "justify-end" : "justify-start")}>
            {msg.sender === "assistant" && (
              <div className="flex size-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary mt-0.5">
                <Bot className="size-3.5" />
              </div>
            )}
            <div
              className={cn(
                "rounded-xl px-3 py-2 text-sm max-w-[85%] leading-relaxed",
                msg.sender === "user"
                  ? "bg-primary text-primary-foreground rounded-tr-sm"
                  : "bg-muted/50 border rounded-tl-sm",
              )}
            >
              {msg.text}
            </div>
            {msg.sender === "user" && (
              <div className="flex size-6 shrink-0 items-center justify-center rounded-full bg-secondary text-secondary-foreground mt-0.5">
                <User className="size-3.5" />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Quick actions */}
      <div className="flex flex-wrap gap-1.5 px-3 py-2 border-t">
        {quickActions.map(action => (
          <button
            key={action}
            onClick={() => onSend(action)}
            className="rounded-full border px-2.5 py-1 text-[11px] text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
          >
            {action}
          </button>
        ))}
      </div>

      {/* Input */}
      <div className="border-t px-3 py-2.5">
        <div className="flex items-center gap-2 rounded-lg border bg-background px-2 py-1 focus-within:ring-1 focus-within:ring-ring">
          <input
            type="text"
            placeholder="Спросить ассистента…"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault()
                handleSend()
              }
            }}
            className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
          />
          <Button
            size="icon"
            className="size-7 rounded-full shrink-0"
            disabled={!input.trim()}
            onClick={handleSend}
          >
            <ArrowUp className="size-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}
