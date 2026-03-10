import { Link, Outlet } from "react-router-dom"

import { Button } from "@/components/ui/button"

export function AuthLayout() {
  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <header className="border-b">
        <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-4">
          <Link to="/" className="flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-lg bg-primary text-sm font-semibold text-primary-foreground">
              AT
            </div>
            <div className="leading-tight">
              <p className="text-sm font-semibold">AutoTZ</p>
              <p className="text-xs text-muted-foreground">Генерация технических заданий</p>
            </div>
          </Link>
          <div className="flex items-center gap-2">
            <Button asChild variant="ghost">
              <Link to="/auth/login">Войти</Link>
            </Button>
            <Button asChild variant="secondary">
              <Link to="/auth/register">Регистрация</Link>
            </Button>
          </div>
        </div>
      </header>
      <main className="flex flex-1 px-4 py-8">
        <div className="mx-auto flex w-full max-w-4xl flex-1">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
