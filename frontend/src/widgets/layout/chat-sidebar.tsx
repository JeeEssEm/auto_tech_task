import { Link, useLocation } from "react-router-dom"
import { FolderOpen, MessageSquare, Plus, User, Home } from "lucide-react"
import { useEffect, useState } from "react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { chatApi, chatEvents } from "@/shared/api/chat-service"
import type { ChatPreview } from "@/shared/api/chat-service"
import { useAuth } from "@/app/auth-provider"

type ChatSidebarProps = {
  isOpen: boolean
}

export function ChatSidebar({ isOpen }: ChatSidebarProps) {
  const location = useLocation()
  const { isAuthenticated } = useAuth()
  const [chats, setChats] = useState<ChatPreview[]>([])

  useEffect(() => {
    let isActive = true
    const controller = new AbortController()

    const fetchChats = async () => {
        try {
            const data = await chatApi.getChats({ limit: 20 }, controller.signal)
            if (isActive) setChats(data)
        } catch (e: any) {
            if (e.name !== 'AbortError') console.error(e)
        }
    }

    if (isAuthenticated) {
        fetchChats()
    } else {
        setChats([])
    }

    const handleChatCreated = () => {
        if (isAuthenticated) fetchChats()
    }

    chatEvents.addEventListener("chatCreated", handleChatCreated)
    return () => {
        isActive = false
        controller.abort()
        chatEvents.removeEventListener("chatCreated", handleChatCreated)
    }
  }, [isAuthenticated])

  return (
    <aside
      className={cn(
        "flex flex-col border-r bg-card/30 transition-[width] duration-300 overflow-hidden shrink-0",
        isOpen ? "w-[260px]" : "w-0 border-r-0",
      )}
    >
      <div className="flex h-full w-[260px] flex-col gap-4 p-3">
        {/* New Chat Button */}
        <Button asChild className="w-full" variant="default">
          <Link to="/chats/new" className="flex items-center gap-3">
            <Plus className="size-5 shrink-0" />
            <span className="whitespace-nowrap">Новый чат</span>
          </Link>
        </Button>

        {/* Workspace demo */}
        <Button asChild variant="outline" className="w-full justify-start gap-3">
          <Link to="/workspace/demo">
            <FolderOpen className="size-4 shrink-0" />
            <span className="whitespace-nowrap">Демо рабочего стола</span>
          </Link>
        </Button>

        {/* Chats List */}
        <div className="flex flex-1 flex-col gap-2 overflow-hidden">
          <span className="px-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Активные чаты
          </span>

          <div className="flex flex-col gap-1 overflow-y-auto">
            {chats.map((chat) => {
              const isActive = location.pathname.includes(String(chat.id))
              return (
                <Link
                  key={chat.id}
                  to={`/chats/${chat.id}`}
                  className={cn(
                    "flex h-9 items-center gap-3 rounded-md px-2 text-sm transition-colors hover:bg-accent hover:text-accent-foreground overflow-hidden",
                    isActive ? "bg-accent text-accent-foreground font-medium" : "text-muted-foreground"
                  )}
                  title={chat.name}
                >
                  <MessageSquare className="size-4 shrink-0" />
                  <span className="truncate">{chat.name}</span>
                </Link>
              )
            })}
          </div>
        </div>

        {/* Footer actions */}
        <div className="mt-auto space-y-1">
          <Button asChild variant="ghost" className="w-full justify-start gap-3">
            <Link to="/profile">
              <User className="size-4 shrink-0" />
              <span className="whitespace-nowrap">Профиль</span>
            </Link>
          </Button>
          <Button asChild variant="ghost" className="w-full justify-start gap-3">
            <Link to="/">
              <Home className="size-4 shrink-0" />
              <span className="whitespace-nowrap">На главную</span>
            </Link>
          </Button>
        </div>
      </div>
    </aside>
  )
}
