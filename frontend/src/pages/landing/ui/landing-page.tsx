import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import {
  ArrowRight,
  Brain,
  FileStack,
  GitBranch,
  LayoutTemplate,
  GitCompareArrows,
  Download,
} from "lucide-react"

import { mockApi } from "@/shared/api/mock-service"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"

const featureIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  brain: Brain,
  files: FileStack,
  graph: GitBranch,
  template: LayoutTemplate,
  versions: GitCompareArrows,
  export: Download,
}

export function LandingPage() {
  const [landingData, setLandingData] = useState<
    Awaited<ReturnType<typeof mockApi.getLandingData>> | undefined
  >()

  useEffect(() => {
    mockApi.getLandingData().then(setLandingData)
  }, [])

  return (
    <div className="bg-background text-foreground">
      {/* Nav */}
      <header className="sticky top-0 z-30 border-b bg-background/80 backdrop-blur-sm">
        <div className="mx-auto flex h-14 w-full max-w-6xl items-center justify-between px-6">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="flex size-8 items-center justify-center rounded-lg bg-primary text-xs font-bold text-primary-foreground">
              AT
            </div>
            <span className="text-sm font-semibold">AutoTZ</span>
          </Link>
          <div className="flex items-center gap-2">
            <Button asChild variant="ghost" size="sm">
              <Link to="/auth/login">Войти</Link>
            </Button>
            <Button asChild size="sm">
              <Link to="/auth/register">Начать бесплатно</Link>
            </Button>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden border-b">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-primary/5" />
        <div className="relative mx-auto flex w-full max-w-6xl flex-col items-center gap-8 px-6 py-24 text-center md:py-32">
          <Badge variant="secondary" className="gap-1.5">
            <span className="size-1.5 rounded-full bg-emerald-500 animate-pulse" />
            Бета-версия · Бесплатный доступ
          </Badge>
          <div className="max-w-3xl space-y-4">
            <h1 className="text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl">
              {landingData?.heroTitle ?? "Автоматизируйте подготовку технических заданий"}
            </h1>
            <p className="mx-auto max-w-2xl text-lg text-muted-foreground md:text-xl">
              {landingData?.heroSubtitle ??
                "Загружайте документы и записи встреч, общайтесь с ИИ-ассистентом и получайте структурированное ТЗ за минуты."}
            </p>
          </div>
          <div className="flex flex-wrap justify-center gap-3">
            <Button asChild size="lg" className="gap-2">
              <Link to="/auth/register">
                Попробовать бесплатно
                <ArrowRight className="size-4" />
              </Link>
            </Button>
            <Button asChild variant="outline" size="lg">
              <Link to="/auth/login">Войти в аккаунт</Link>
            </Button>
          </div>

          {/* Stats row */}
          <div className="mt-4 grid w-full max-w-2xl grid-cols-2 gap-4 sm:grid-cols-4">
            {(landingData?.stats ?? []).map((stat) => (
              <div key={stat.label} className="flex flex-col items-center gap-1">
                <span className="text-2xl font-bold">{stat.value}</span>
                <span className="text-xs text-muted-foreground">{stat.label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features grid */}
      <section className="mx-auto w-full max-w-6xl px-6 py-20">
        <div className="mb-12 max-w-2xl space-y-3">
          <Badge variant="outline">Возможности</Badge>
          <h2 className="text-3xl font-bold tracking-tight md:text-4xl">
            Всё для создания качественного ТЗ
          </h2>
          <p className="text-base text-muted-foreground">
            От сбора требований до финального документа — каждый этап автоматизирован.
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {(landingData?.features ?? []).map((feature) => {
            const Icon = featureIcons[feature.icon] ?? Brain
            return (
              <Card key={feature.title} className="group relative overflow-hidden transition-shadow hover:shadow-md">
                <CardContent className="flex flex-col gap-3 p-6">
                  <div className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary transition-colors group-hover:bg-primary/15">
                    <Icon className="size-5" />
                  </div>
                  <h3 className="text-sm font-semibold">{feature.title}</h3>
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    {feature.description}
                  </p>
                </CardContent>
              </Card>
            )
          })}
        </div>
      </section>

      {/* How it works */}
      <section className="border-t bg-muted/30">
        <div className="mx-auto w-full max-w-6xl px-6 py-20">
          <div className="mb-12 max-w-2xl space-y-3">
            <Badge variant="outline">Процесс</Badge>
            <h2 className="text-3xl font-bold tracking-tight md:text-4xl">
              Три шага до готового ТЗ
            </h2>
          </div>
          <div className="grid gap-6 md:grid-cols-3">
            {[
              {
                step: "01",
                title: "Загрузите данные",
                desc: "Документы, аудио встреч, видеозаписи — система обработает любой формат и извлечёт ключевую информацию.",
              },
              {
                step: "02",
                title: "Уточните в диалоге",
                desc: "ИИ-ассистент задаст вопросы, которые помогут раскрыть неочевидные требования и устранить двусмысленности.",
              },
              {
                step: "03",
                title: "Получите документ",
                desc: "Структурированное ТЗ по выбранному шаблону с версионированием и возможностью экспорта.",
              },
            ].map((item) => (
              <div key={item.step} className="flex flex-col gap-3">
                <span className="text-4xl font-bold text-primary/20">{item.step}</span>
                <h3 className="text-lg font-semibold">{item.title}</h3>
                <p className="text-sm leading-relaxed text-muted-foreground">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* TZ structure preview */}
      <section className="mx-auto w-full max-w-6xl px-6 py-20">
        <div className="grid items-center gap-12 md:grid-cols-2">
          <div className="space-y-4">
            <Badge variant="outline">Результат</Badge>
            <h2 className="text-3xl font-bold tracking-tight md:text-4xl">
              Профессиональная структура документа
            </h2>
            <p className="text-base text-muted-foreground">
              Каждое ТЗ создаётся по проверенным шаблонам и включает все необходимые разделы.
            </p>
          </div>
          <div className="space-y-2">
            {[
              "Цели, контекст и метрики продукта",
              "Функциональные и нефункциональные требования",
              "Приоритизация по MoSCoW",
              "Интеграции, зависимости и риски",
              "План релиза и бэклог задач",
            ].map((item, i) => (
              <div
                key={item}
                className="flex items-center gap-3 rounded-lg border bg-background p-3.5 text-sm transition-colors hover:bg-muted/50"
              >
                <div className="flex size-7 shrink-0 items-center justify-center rounded-md bg-primary text-xs font-semibold text-primary-foreground">
                  {i + 1}
                </div>
                <span className="text-foreground/90">{item}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t">
        <div className="mx-auto w-full max-w-6xl px-6 py-20">
          <div className="flex flex-col items-center gap-6 text-center">
            <h2 className="text-3xl font-bold tracking-tight md:text-4xl">
              Готовы автоматизировать создание ТЗ?
            </h2>
            <p className="max-w-lg text-base text-muted-foreground">
              Создайте первый чат, загрузите материалы — и получите черновик ТЗ уже сегодня.
            </p>
            <div className="flex flex-wrap justify-center gap-3">
              <Button asChild size="lg" className="gap-2">
                <Link to="/auth/register">
                  Начать бесплатно
                  <ArrowRight className="size-4" />
                </Link>
              </Button>
              <Button asChild variant="outline" size="lg">
                <Link to="/auth/login">Войти</Link>
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t bg-muted/20">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-6 text-xs text-muted-foreground">
          <span>© {new Date().getFullYear()} AutoTZ Lab</span>
          <span>Сделано с помощью ИИ</span>
        </div>
      </footer>
    </div>
  )
}
