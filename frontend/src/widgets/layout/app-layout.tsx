import { Link, Outlet, useNavigate } from "react-router-dom"
import { useEffect, useState } from "react"
import { PanelLeft } from "lucide-react"

import { Button } from "@/components/ui/button"
import { useAuth } from "@/app/auth-provider"

import { AppNavigation } from "./app-navigation"
import { ChatSidebar } from "./chat-sidebar"

export function AppLayout() {
  const { isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  useEffect(() => {
    if (!isAuthenticated) {
        navigate("/auth/login")
    }
  }, [isAuthenticated, navigate])

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <header className="border-b shrink-0">
        <div className="flex h-14 w-full items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              className="size-9"
              onClick={() => setSidebarOpen(prev => !prev)}
              title={sidebarOpen ? "Скрыть боковую панель" : "Показать боковую панель"}
            >
              <PanelLeft className="size-5" />
            </Button>
            <Link to="/chats/new" className="flex items-center gap-3">
              <div className="flex size-8 items-center justify-center rounded-lg bg-primary text-xs font-semibold text-primary-foreground">
                AT
              </div>
              <div className="leading-tight hidden sm:block">
                <p className="text-sm font-semibold">AutoTZ</p>
                <p className="text-[11px] text-muted-foreground">Генерация ТЗ</p>
              </div>
            </Link>
          </div>
          <div className="flex items-center gap-2">
            <AppNavigation />
            {isAuthenticated ? (
              <Button asChild variant="secondary" size="sm">
                <Link to="/profile">Профиль</Link>
              </Button>
            ) : (
              <>
                <Button asChild variant="ghost" size="sm">
                  <Link to="/auth/login">Войти</Link>
                </Button>
                <Button asChild variant="secondary" size="sm">
                  <Link to="/auth/register">Регистрация</Link>
                </Button>
              </>
            )}
          </div>
        </div>
      </header>
      <div className="flex flex-1 overflow-hidden">
        <ChatSidebar isOpen={sidebarOpen} />
        <main className="flex-1 min-w-0 overflow-hidden">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
