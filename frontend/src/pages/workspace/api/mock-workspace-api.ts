import type {
  BusinessEntity,
  DocumentSection,
  GlossaryTerm,
  Requirement,
  Stakeholder,
  WorkspaceChatMessage,
  WorkspaceProject,
} from "../lib/types"

const delay = (ms = 300) => new Promise(r => setTimeout(r, ms))

const project: WorkspaceProject = {
  id: "proj-001",
  name: "АИС «СкладПро»",
  template: "it_project",
  completeness: 58,
  sectionsTotal: 7,
  sectionsFilled: 4,
  requirementsCount: 9,
  entitiesCount: 7,
  openQuestions: 3,
}

const sections: DocumentSection[] = [
  {
    id: "s1",
    number: "1",
    title: "Общие сведения",
    status: "approved",
    content:
      "**Наименование:** Автоматизированная информационная система «СкладПро»\n" +
      "**Заказчик:** ООО «Логистик Про»\n" +
      "**Исполнитель:** AutoTZ Lab\n" +
      "**Дата создания:** 15.01.2025\n" +
      "**Основание:** Договор № 24-ИТ/0115 от 10.01.2025",
  },
  {
    id: "s2",
    number: "2",
    title: "Назначение и цели",
    status: "approved",
    content:
      "Система предназначена для комплексной автоматизации складского документооборота и управления товарными потоками.\n\n" +
      "**Цели:**\n" +
      "- Сокращение времени приёмки товара на 60%\n" +
      "- Автоматизация инвентаризации\n" +
      "- Снижение ошибок учёта до < 0.1%\n" +
      "- Интеграция с существующей ERP-системой (1С)",
  },
  {
    id: "s3",
    number: "3",
    title: "Функциональные требования",
    status: "draft",
    content: "",
    children: [
      {
        id: "s3-1",
        number: "3.1",
        title: "Приёмка товара",
        status: "draft",
        content:
          "Модуль обеспечивает регистрацию входящих поставок.\n\n" +
          "- Сканирование штрих-кодов и QR-кодов\n" +
          "- Автоматическое обновление остатков при приёмке\n" +
          "- Фотофиксация повреждений\n" +
          "- Формирование акта приёмки\n" +
          "- Уведомление менеджера о расхождениях",
      },
      {
        id: "s3-2",
        number: "3.2",
        title: "Инвентаризация",
        status: "draft",
        content:
          "Модуль плановой и внеплановой инвентаризации.\n\n" +
          "- Мобильный интерфейс для кладовщиков (PWA)\n" +
          "- Генерация инвентаризационных ведомостей\n" +
          "- Автоматическое сравнение с учётными данными\n" +
          "- Протокол расхождений с фотофиксацией",
      },
      {
        id: "s3-3",
        number: "3.3",
        title: "Заказы поставщикам",
        status: "draft",
        content:
          "Автоматический расчёт точки перезаказа на основе:\n" +
          "- Средней скорости расходования\n" +
          "- Минимального остатка (safety stock)\n" +
          "- Сроков доставки поставщика\n\n" +
          "Формирование и отправка заказов через API поставщика.",
      },
      {
        id: "s3-4",
        number: "3.4",
        title: "Отчётность и аналитика",
        status: "empty",
        content: "",
      },
    ],
  },
  {
    id: "s4",
    number: "4",
    title: "Нефункциональные требования",
    status: "review",
    content:
      "- Доступность: 99.5% (SLA)\n" +
      "- Время отклика API: ≤ 200 мс (p95)\n" +
      "- Поддержка до 50 одновременных пользователей\n" +
      "- Обработка до 10 000 SKU\n" +
      "- Горизонтальное масштабирование бэкенда\n" +
      "- Резервное копирование: ежедневно, хранение 30 дней",
  },
  {
    id: "s5",
    number: "5",
    title: "Требования к безопасности",
    status: "empty",
    content: "",
  },
  {
    id: "s6",
    number: "6",
    title: "Этапы реализации",
    status: "empty",
    content: "",
  },
  {
    id: "s7",
    number: "7",
    title: "Приёмка и тестирование",
    status: "empty",
    content: "",
  },
]

const requirements: Requirement[] = [
  {
    id: "r1",
    title: "Сканирование штрих-кодов",
    description: "Система должна поддерживать сканирование штрих-кодов (EAN-13, Code 128) и QR-кодов через камеру мобильного устройства.",
    type: "functional",
    priority: "must",
    status: "in_tz",
    source: "requirements_v2.docx",
    module: "Приёмка товара",
  },
  {
    id: "r2",
    title: "Мобильный интерфейс кладовщика",
    description: "PWA-приложение для проведения инвентаризации с offline-режимом и синхронизацией при восстановлении связи.",
    type: "functional",
    priority: "must",
    status: "in_tz",
    source: "meeting_2024-01-15.mp3",
    module: "Инвентаризация",
  },
  {
    id: "r3",
    title: "Автоматический перезаказ",
    description: "Расчёт точки перезаказа на основе скорости расходования и safety stock. Автоматическое формирование заказа поставщику.",
    type: "functional",
    priority: "should",
    status: "confirmed",
    source: "meeting_2024-01-15.mp3",
    module: "Заказы",
  },
  {
    id: "r4",
    title: "Интеграция с 1С",
    description: "REST API для двусторонней синхронизации номенклатуры, остатков и документов с 1С:Предприятие 8.3.",
    type: "functional",
    priority: "must",
    status: "in_tz",
    source: "requirements_v2.docx",
    module: "Интеграции",
  },
  {
    id: "r5",
    title: "Время отклика API ≤ 200 мс",
    description: "95-й перцентиль времени ответа для всех эндпоинтов не должен превышать 200 мс при штатной нагрузке.",
    type: "non-functional",
    priority: "must",
    status: "in_tz",
    source: "requirements_v2.docx",
    module: "Общее",
  },
  {
    id: "r6",
    title: "Обработка 10 000 SKU",
    description: "Система должна корректно работать с каталогом до 10 000 товарных позиций без деградации производительности.",
    type: "non-functional",
    priority: "must",
    status: "confirmed",
    source: "requirements_v2.docx",
    module: "Общее",
  },
  {
    id: "r7",
    title: "OAuth 2.0 аутентификация",
    description: "Аутентификация пользователей через OAuth 2.0 с поддержкой SSO через корпоративный Keycloak.",
    type: "constraint",
    priority: "must",
    status: "extracted",
    source: "architecture_diagram.pdf",
    module: "Безопасность",
  },
  {
    id: "r8",
    title: "Фотофиксация при приёмке",
    description: "Возможность прикрепления фотографий повреждённого товара к акту приёмки.",
    type: "functional",
    priority: "could",
    status: "extracted",
    source: "meeting_2024-01-15.mp3",
    module: "Приёмка товара",
  },
  {
    id: "r9",
    title: "Уведомления в Telegram",
    description: "Отправка уведомлений о критических событиях (расхождения при приёмке, низкий остаток) в Telegram-бот.",
    type: "functional",
    priority: "could",
    status: "extracted",
    source: "meeting_2024-01-15.mp3",
    module: "Уведомления",
  },
]

const entities: BusinessEntity[] = [
  {
    id: "e1",
    name: "АИС СкладПро",
    description: "Основная автоматизированная информационная система для управления складским учётом.",
    type: "system",
    source: "requirements_v2.docx",
    relatedSections: ["1", "2"],
  },
  {
    id: "e2",
    name: "Модуль приёмки",
    description: "Подсистема регистрации входящих поставок с поддержкой сканирования и фотофиксации.",
    type: "module",
    source: "requirements_v2.docx",
    relatedSections: ["3.1"],
  },
  {
    id: "e3",
    name: "Модуль инвентаризации",
    description: "Подсистема проведения плановых и внеплановых инвентаризаций с мобильным интерфейсом.",
    type: "module",
    source: "meeting_2024-01-15.mp3",
    relatedSections: ["3.2"],
  },
  {
    id: "e4",
    name: "Процесс перезаказа",
    description: "Бизнес-процесс автоматического расчёта необходимости пополнения запасов и формирования заказов.",
    type: "process",
    source: "meeting_2024-01-15.mp3",
    relatedSections: ["3.3"],
  },
  {
    id: "e5",
    name: "Товарная номенклатура",
    description: "Справочник товарных позиций (SKU) с характеристиками, штрих-кодами и привязкой к поставщикам.",
    type: "data",
    source: "requirements_v2.docx",
    relatedSections: ["3.1", "3.2", "3.3"],
  },
  {
    id: "e6",
    name: "1С:Предприятие",
    description: "Внешняя ERP-система заказчика, с которой осуществляется интеграция по REST API.",
    type: "system",
    source: "architecture_diagram.pdf",
    relatedSections: ["4"],
  },
  {
    id: "e7",
    name: "Складская ячейка",
    description: "Адресное хранение: стеллаж, полка, ячейка. Привязка товара к физическому месту.",
    type: "data",
    source: "requirements_v2.docx",
    relatedSections: ["3.1", "3.2"],
  },
]

const glossary: GlossaryTerm[] = [
  {
    id: "g1",
    term: "SKU",
    definition: "Stock Keeping Unit — уникальный идентификатор товарной позиции в складской системе.",
    variants: ["СКЮ", "артикул", "товарная единица"],
    usedInSections: ["3.1", "3.2", "4"],
  },
  {
    id: "g2",
    term: "Safety Stock",
    definition: "Страховой запас — минимальный уровень остатка, ниже которого система инициирует перезаказ.",
    variants: ["страховой запас", "минимальный остаток", "буферный запас"],
    usedInSections: ["3.3"],
  },
  {
    id: "g3",
    term: "Точка перезаказа",
    definition: "Уровень остатка, при достижении которого автоматически формируется заказ поставщику (ROP — Reorder Point).",
    variants: ["ROP", "reorder point", "уровень перезаказа"],
    usedInSections: ["3.3"],
  },
  {
    id: "g4",
    term: "Акт приёмки",
    definition: "Документ, фиксирующий факт приёмки товара на склад с указанием количества, состояния и расхождений.",
    variants: ["приёмочный акт", "акт поступления"],
    usedInSections: ["3.1"],
  },
  {
    id: "g5",
    term: "PWA",
    definition: "Progressive Web App — веб-приложение с возможностями нативного приложения, включая offline-режим.",
    variants: ["прогрессивное веб-приложение"],
    usedInSections: ["3.2"],
  },
  {
    id: "g6",
    term: "SLA",
    definition: "Service Level Agreement — соглашение об уровне обслуживания, определяющее метрики доступности и производительности.",
    variants: ["соглашение об уровне сервиса"],
    usedInSections: ["4"],
  },
]

const stakeholders: Stakeholder[] = [
  {
    id: "st1",
    name: "Иванов А.С.",
    role: "Директор по логистике",
    concerns: [
      "Сокращение операционных затрат на 30%",
      "Полная прозрачность складских остатков",
      "Интеграция с существующей ERP",
    ],
    relatedRequirements: ["r4", "r5", "r6"],
  },
  {
    id: "st2",
    name: "Петрова М.В.",
    role: "Старший кладовщик",
    concerns: [
      "Удобный мобильный интерфейс",
      "Работа без интернета на складе",
      "Быстрое сканирование при приёмке",
    ],
    relatedRequirements: ["r1", "r2", "r8"],
  },
  {
    id: "st3",
    name: "Козлов Д.И.",
    role: "IT-директор",
    concerns: [
      "Безопасность и аутентификация через корпоративный SSO",
      "Масштабируемость при росте номенклатуры",
      "Мониторинг и observability",
    ],
    relatedRequirements: ["r5", "r6", "r7"],
  },
  {
    id: "st4",
    name: "Сидорова Е.А.",
    role: "Менеджер по закупкам",
    concerns: [
      "Автоматизация рутинных заказов",
      "Точные прогнозы потребления",
      "Уведомления о критических остатках",
    ],
    relatedRequirements: ["r3", "r9"],
  },
]

const chatMessages: WorkspaceChatMessage[] = [
  {
    id: 1,
    sender: "user",
    text: "Сгенерируй ТЗ для системы складского учёта на основе загруженных файлов",
    created_at: "2025-01-15T10:00:00Z",
  },
  {
    id: 2,
    sender: "assistant",
    text: "Проанализировал 3 файла и создал черновик ТЗ из 7 разделов. Заполнил разделы 1–4 на основе извлечённых данных. Разделы 5–7 пока пусты — нужна дополнительная информация.",
    created_at: "2025-01-15T10:01:00Z",
  },
  {
    id: 3,
    sender: "user",
    text: "Дополни раздел по безопасности, нужна аутентификация через OAuth и журналирование",
    created_at: "2025-01-15T10:05:00Z",
  },
  {
    id: 4,
    sender: "assistant",
    text: "Добавил в раздел 5 требования по OAuth 2.0 через Keycloak и журналирование действий. Также извлёк из architecture_diagram.pdf информацию об SSO — добавил в требования.",
    created_at: "2025-01-15T10:05:30Z",
  },
]

export const workspaceMockApi = {
  getProject: async (_id: string): Promise<WorkspaceProject> => {
    await delay()
    return project
  },
  getSections: async (_id: string): Promise<DocumentSection[]> => {
    await delay()
    return sections
  },
  getRequirements: async (_id: string): Promise<Requirement[]> => {
    await delay()
    return requirements
  },
  getEntities: async (_id: string): Promise<BusinessEntity[]> => {
    await delay()
    return entities
  },
  getGlossary: async (_id: string): Promise<GlossaryTerm[]> => {
    await delay()
    return glossary
  },
  getStakeholders: async (_id: string): Promise<Stakeholder[]> => {
    await delay()
    return stakeholders
  },
  getChatMessages: async (_id: string): Promise<WorkspaceChatMessage[]> => {
    await delay()
    return chatMessages
  },
}
