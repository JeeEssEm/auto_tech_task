import { useEffect, useState } from "react"
import { toast } from "sonner"
import { LogOut, Mail, User, CreditCard, Shield, BarChart3, FileText, MessageSquare, Zap } from "lucide-react"

import { authApi } from "@/shared/api/auth-service"
import type { UserProfile, UsageInfo } from "@/shared/api/auth-service"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { useAuth } from "@/app/auth-provider"

export function ProfilePage() {
  const [profile, setProfile] = useState<UserProfile | undefined>()
  const [usage, setUsage] = useState<UsageInfo | undefined>()
  const { logout } = useAuth()

  useEffect(() => {
    authApi.getMe().then(setProfile).catch(() => {})
    authApi.getUsage().then(setUsage).catch(() => {})
  }, [])

  const handleLogout = async () => {
    try {
        await authApi.logout()
        logout()
        toast.info("Вышли из системы")
    } catch {
        logout()
    }
  }

  const fullName = profile
    ? [profile.lastname, profile.firstname, profile.middlename].filter(Boolean).join(" ")
    : undefined

  const initials = fullName
    ? fullName.split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase()
    : "…"

  const usagePercent = (used: number, limit: number) =>
    limit > 0 ? Math.min(Math.round((used / limit) * 100), 100) : 0

  return (
    <div className="mx-auto w-full max-w-4xl px-6 py-10">
      {/* Header card with avatar */}
      <Card className="mb-6 overflow-hidden">
        <div className="h-24 bg-gradient-to-r from-primary/10 via-primary/5 to-transparent" />
        <CardContent className="relative px-6 pb-6 -mt-12">
          <div className="flex flex-col gap-6 sm:flex-row sm:items-end">
            <div className="flex size-20 items-center justify-center rounded-2xl border-4 border-background bg-primary text-2xl font-bold text-primary-foreground shadow-sm">
              {initials}
            </div>
            <div className="flex-1 space-y-1">
              <h1 className="text-xl font-semibold">{fullName ?? "Загрузка…"}</h1>
              <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                <Badge variant="secondary">{profile?.role ?? "—"}</Badge>
                {profile?.login && (
                  <>
                    <span>·</span>
                    <span>@{profile.login}</span>
                  </>
                )}
              </div>
            </div>
            <Button variant="outline" size="sm" className="gap-2 text-destructive hover:bg-destructive/10 hover:text-destructive border-destructive/20 self-start sm:self-auto" onClick={handleLogout}>
              <LogOut className="size-4" />
              Выйти
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Info grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardContent className="flex items-start gap-3 p-5">
            <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Mail className="size-4" />
            </div>
            <div className="min-w-0">
              <p className="text-xs text-muted-foreground">Email</p>
              <p className="truncate text-sm font-medium">{profile?.email ?? "—"}</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-start gap-3 p-5">
            <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <User className="size-4" />
            </div>
            <div className="min-w-0">
              <p className="text-xs text-muted-foreground">Логин</p>
              <p className="truncate text-sm font-medium">{profile?.login ?? "—"}</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-start gap-3 p-5">
            <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <CreditCard className="size-4" />
            </div>
            <div className="min-w-0">
              <p className="text-xs text-muted-foreground">Подписка</p>
              <p className="truncate text-sm font-medium">{profile?.subscription_tier ?? "—"}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Account status */}
      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <Card>
          <CardContent className="flex items-start gap-4 p-5">
            <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-500">
              <Shield className="size-4" />
            </div>
            <div className="flex-1 space-y-1">
              <p className="text-xs text-muted-foreground">Состояние аккаунта</p>
              <div className="flex items-center gap-2">
                <span className={`size-2 rounded-full ${profile?.is_active ? "bg-emerald-500" : "bg-destructive"}`} />
                <span className="text-sm font-medium">{profile?.is_active ? "Активен" : "Неактивен"}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {usage && (
          <Card>
            <CardContent className="flex items-start gap-4 p-5">
              <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <MessageSquare className="size-4" />
              </div>
              <div className="flex-1 space-y-1">
                <p className="text-xs text-muted-foreground">Всего чатов</p>
                <p className="text-lg font-semibold">{usage.total_chats}</p>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Usage statistics */}
      {usage && (
        <div className="mt-6 space-y-4">
          <div className="flex items-center gap-2">
            <BarChart3 className="size-5 text-primary" />
            <h2 className="text-lg font-semibold">Статистика использования</h2>
            <Badge variant="outline" className="ml-auto">{usage.tier}</Badge>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {/* Generate TZ usage */}
            <Card>
              <CardContent className="p-5 space-y-3">
                <div className="flex items-center gap-2">
                  <Zap className="size-4 text-primary" />
                  <p className="text-sm font-medium">Генерации ТЗ сегодня</p>
                </div>
                <div className="flex items-baseline justify-between">
                  <span className="text-2xl font-bold">{usage.today.generate_tz}</span>
                  <span className="text-xs text-muted-foreground">из {usage.limits.generate_tz}</span>
                </div>
                <Progress value={usagePercent(usage.today.generate_tz, usage.limits.generate_tz)} className="h-2" />
              </CardContent>
            </Card>

            {/* Parsed files usage */}
            <Card>
              <CardContent className="p-5 space-y-3">
                <div className="flex items-center gap-2">
                  <FileText className="size-4 text-primary" />
                  <p className="text-sm font-medium">Файлов обработано сегодня</p>
                </div>
                <div className="flex items-baseline justify-between">
                  <span className="text-2xl font-bold">{usage.today.parsed_files}</span>
                  <span className="text-xs text-muted-foreground">из {usage.limits.parse_files}</span>
                </div>
                <Progress value={usagePercent(usage.today.parsed_files, usage.limits.parse_files)} className="h-2" />
              </CardContent>
            </Card>

            {/* Chat creation limit */}
            <Card>
              <CardContent className="p-5 space-y-3">
                <div className="flex items-center gap-2">
                  <MessageSquare className="size-4 text-primary" />
                  <p className="text-sm font-medium">Лимит создания чатов</p>
                </div>
                <div className="flex items-baseline justify-between">
                  <span className="text-2xl font-bold">{usage.total_chats}</span>
                  <span className="text-xs text-muted-foreground">из {usage.limits.create_chat}</span>
                </div>
                <Progress value={usagePercent(usage.total_chats, usage.limits.create_chat)} className="h-2" />
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  )
}
