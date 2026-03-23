import type { GeneratedTechnicalTask, KnowledgeGraph, ParsedAttachment } from "../lib/types"

const delay = (ms = 400) => new Promise(r => setTimeout(r, ms))

const mockAttachments: ParsedAttachment[] = [
  {
    key: "att-001",
    file_name: "requirements_v2.docx",
    file_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    file_size: 245760,
    transcript:
      "В документе описаны основные требования к системе автоматизации складского учёта. " +
      "Ключевые модули: управление товарными остатками, интеграция с 1С, генерация отчётов по движению товаров. " +
      "Требования к производительности: обработка до 10 000 SKU, время отклика API не более 200 мс. " +
      "Также указаны требования к безопасности: аутентификация через OAuth 2.0, журналирование всех действий.",
  },
  {
    key: "att-002",
    file_name: "meeting_2024-01-15.mp3",
    file_type: "audio/mpeg",
    file_size: 15728640,
    transcript:
      "Участники обсудили приоритеты для MVP. Решено сфокусироваться на трёх основных сценариях: " +
      "приёмка товара, инвентаризация и формирование заказа поставщику. Интеграция с маркетплейсами " +
      "отложена на второй этап. Заказчик подчеркнул важность мобильного интерфейса для кладовщиков. " +
      "Обсуждён вопрос хранения данных — предпочтение отдано PostgreSQL с партиционированием по дате.",
  },
  {
    key: "att-003",
    file_name: "architecture_diagram.pdf",
    file_type: "application/pdf",
    file_size: 1048576,
    transcript:
      "Схема архитектуры включает микросервисную структуру: API Gateway (Kong), сервис авторизации " +
      "(Keycloak), основной бэкенд (Python/FastAPI), очередь сообщений (RabbitMQ), база данных " +
      "PostgreSQL. Фронтенд — React SPA. Деплой через Docker Compose, в перспективе — Kubernetes.",
  },
]

const mockTasks: GeneratedTechnicalTask[] = [
  {
    version: 1,
    name: "ТЗ v1 — Черновик",
    technical_task_template: "it_project",
    content:
      "# Техническое задание\n\n" +
      "## 1. Общие сведения\n" +
      "**Наименование:** Система автоматизации складского учёта\n" +
      "**Заказчик:** ООО «Логистик Про»\n\n" +
      "## 2. Назначение\n" +
      "Система предназначена для автоматизации процессов приёмки, хранения и отгрузки товаров.\n\n" +
      "## 3. Требования к функциональности\n" +
      "- Модуль приёмки товара\n" +
      "- Модуль инвентаризации\n" +
      "- Модуль формирования заказов\n\n" +
      "## 4. Требования к производительности\n" +
      "- Обработка до 10 000 SKU\n" +
      "- Время отклика API ≤ 200 мс",
  },
  {
    version: 2,
    name: "ТЗ v2 — После уточнений",
    technical_task_template: "it_project",
    content:
      "# Техническое задание (v2)\n\n" +
      "## 1. Общие сведения\n" +
      "**Наименование:** Система автоматизации складского учёта «СкладПро»\n" +
      "**Заказчик:** ООО «Логистик Про»\n" +
      "**Исполнитель:** AutoTZ Lab\n\n" +
      "## 2. Назначение и цели\n" +
      "Автоматизация складского документооборота и управления товарными потоками.\n\n" +
      "## 3. Функциональные требования\n" +
      "### 3.1 Приёмка товара\n" +
      "- Сканирование штрих-кодов\n" +
      "- Автоматическое обновление остатков\n" +
      "### 3.2 Инвентаризация\n" +
      "- Плановая и внеплановая\n" +
      "- Мобильный интерфейс для кладовщиков\n" +
      "### 3.3 Заказы поставщикам\n" +
      "- Автоматический расчёт точки перезаказа\n\n" +
      "## 4. Нефункциональные требования\n" +
      "- Доступность 99.5%\n" +
      "- Интеграция с 1С через REST API\n" +
      "- Поддержка до 50 одновременных пользователей",
  },
  {
    version: 3,
    name: "ТЗ v3 — Финальная версия",
    technical_task_template: "it_project",
    content:
      "# Техническое задание (v3 — Финал)\n\n" +
      "## 1. Общие сведения\n" +
      "**Наименование:** АИС «СкладПро»\n" +
      "**Заказчик:** ООО «Логистик Про»\n" +
      "**Исполнитель:** AutoTZ Lab\n" +
      "**Дата:** 15.01.2025\n\n" +
      "## 2. Назначение и цели\n" +
      "Комплексная автоматизация складского документооборота.\n\n" +
      "## 3. Функциональные требования\n" +
      "### 3.1 Приёмка товара\n" +
      "### 3.2 Инвентаризация\n" +
      "### 3.3 Заказы поставщикам\n" +
      "### 3.4 Отчётность и аналитика\n\n" +
      "## 4. Нефункциональные требования\n" +
      "## 5. Требования к безопасности\n" +
      "## 6. Этапы реализации\n" +
      "## 7. Приёмка и тестирование",
  },
]

const mockGraph: KnowledgeGraph = {
  nodes: [
    { id: "scope:system", label: "system", type: "scope" },
    { id: "scope:module", label: "module", type: "scope" },
    { id: "property:system:name", label: "name", type: "property" },
    { id: "property:system:latency", label: "latency", type: "property" },
    { id: "property:module:inventory", label: "inventory", type: "property" },
    { id: "value:1", label: "СкладПро", type: "value" },
    { id: "value:2", label: "API ≤ 200 мс", type: "value" },
    { id: "value:3", label: "Инвентаризация", type: "value" },
  ],
  edges: [
    { from: "scope:system", to: "property:system:name", label: "имеет" },
    { from: "scope:system", to: "property:system:latency", label: "имеет" },
    { from: "scope:module", to: "property:module:inventory", label: "имеет" },
    { from: "property:system:name", to: "value:1", label: "значение" },
    { from: "property:system:latency", to: "value:2", label: "значение" },
    { from: "property:module:inventory", to: "value:3", label: "значение" },
  ],
}

export const panelMockApi = {
  getParsedAttachments: async (_chatId: string): Promise<ParsedAttachment[]> => {
    await delay()
    return mockAttachments
  },

  getGeneratedTasks: async (_chatId: string): Promise<GeneratedTechnicalTask[]> => {
    await delay()
    return mockTasks
  },

  getKnowledgeGraph: async (_chatId: string): Promise<KnowledgeGraph> => {
    await delay(600)
    return mockGraph
  },
}
