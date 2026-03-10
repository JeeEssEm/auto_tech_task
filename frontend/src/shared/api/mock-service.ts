type LandingStat = {
  label: string
  value: string
}

type LandingFeature = {
  title: string
  description: string
  icon: string
}

type LandingData = {
  heroTitle: string
  heroSubtitle: string
  stats: LandingStat[]
  features: LandingFeature[]
}

type UserProfile = {
  name: string
  role: string
  team: string
  email: string
  company: string
  plan: string
}

type ChatTemplate = {
  title: string
  description: string
}

const landingData: LandingData = {
  heroTitle: "Автоматизируйте подготовку технических заданий",
  heroSubtitle:
    "Создавайте чаты с LLM, собирайте требования и превращайте их в готовое ТЗ за минуты.",
  stats: [
    { label: "Сценариев генерации", value: "12+" },
    { label: "Среднее время подготовки", value: "~15 мин" },
    { label: "Шаблонов отраслей", value: "25" },
    { label: "Точность структурирования", value: "94%" },
  ],
  features: [
    {
      title: "Умный сбор требований",
      description: "ИИ-ассистент задаёт уточняющие вопросы и помогает собрать полный набор требований, ничего не упустив.",
      icon: "brain",
    },
    {
      title: "Мультиформатный ввод",
      description: "Загружайте документы, аудиозаписи встреч и видео — система извлечёт ключевую информацию автоматически.",
      icon: "files",
    },
    {
      title: "Граф знаний",
      description: "Автоматическое построение графа сущностей и связей из ваших данных для структурированного анализа.",
      icon: "graph",
    },
    {
      title: "Шаблоны по отраслям",
      description: "ГОСТ 19, IT-проекты, строительство, инженерия — выберите подходящий шаблон или создайте свой.",
      icon: "template",
    },
    {
      title: "Версионирование",
      description: "Каждая итерация ТЗ сохраняется. Сравнивайте версии и отслеживайте, как менялись требования.",
      icon: "versions",
    },
    {
      title: "Экспорт в один клик",
      description: "Готовые документы для команды и заказчика в форматах DOCX, PDF и Markdown.",
      icon: "export",
    },
  ],
}

const userProfile: UserProfile = {
  name: "Анна Ветрова",
  role: "Product Manager",
  team: "Команда Growth",
  email: "anna.vetrova@autotz.ru",
  company: "AutoTZ Lab",
  plan: "Pro",
}

const chatTemplates: ChatTemplate[] = [
  {
    title: "ГОСТ 19",
    description: "Строгое следование государственным стандартам для программной документации.",
  },
  {
    title: "Свободный",
    description: "Гибкая структура без жестких ограничений для бытовых задач.",
  },
  {
    title: "IT-проект",
    description: "Типовая структура для разработки программного ПО.",
  },
  {
    title: "Строительный проект",
    description: "Специфические требования для архитектурных и инженерных изысканий.",
  },
  {
    title: "Инженерный проект",
    description: "Техническое задание для разработки оборудования и механизмов.",
  },
]

function resolveAfter<T>(data: T) {
  return Promise.resolve(data)
}

export const mockApi = {
  getLandingData: () => resolveAfter(landingData),
  getUserProfile: () => resolveAfter(userProfile),
  getChatTemplates: () => resolveAfter(chatTemplates),
}

export type { ChatTemplate, LandingData, LandingFeature, LandingStat, UserProfile }
