# Auto-TZ: генератор технических заданий

Auto-TZ - это full-stack система, которая помогает собирать структурированное ТЗ из диалога пользователя, загруженных файлов и LLM-pipeline с несколькими специализированными behavior-агентами.

Проект включает:

- фронтенд на React + Vite + Tailwind + Tiptap;
- backend API на FastAPI + Dishka + Prisma;
- асинхронные задачи в TaskIQ worker;
- инфраструктуру PostgreSQL/pgvector, Redis, RabbitMQ, SeaweedFS;
- WebSocket-уведомления о ходе генерации и экспорта.

## 1. Архитектура

### 1.1 Основные подсистемы

- Frontend (`frontend`) - UI чата, загрузка файлов, запуск генерации и редактирование секций.
- Backend (`backend/app`) - REST API, авторизация, бизнес-логика, диспатч задач в очередь.
- Worker (`backend/worker`) - парсинг файлов, оркестрация LLM-pipeline, экспорт документов.
- PostgreSQL + pgvector - основное хранилище сущностей, GKG-фактов и секций документа.
- Redis - Pub/Sub канал для WebSocket событий и backend для результатов TaskIQ.
- RabbitMQ - брокер задач TaskIQ.
- SeaweedFS (S3-compatible) - хранение вложений, распарсенных источников и экспортов.

### 1.2 Поток данных (high-level)

1. Пользователь открывает чат во фронтенде.
2. Загружает файлы через API `/chat/files/upload`.
3. Backend ставит задачу `parse_file_task`.
4. Worker парсит файл и сохраняет текстовый транскрипт в S3.
5. Пользователь запускает `/tz/{chat_id}/generate` или `/tz/{chat_id}/update`.
6. Backend отправляет задачу в `orchestrator_tasks`.
7. Worker выполняет LLM-pipeline v3 (router -> behaviors -> persist -> compose).
8. Статусы и финальные ответы отдаются во фронтенд через WebSocket `/chat/ws`.

## 2. LLM Pipeline v3

Пайплайн оркестрируется через LangGraph и работает по принципу fan-out/fan-in.

### 2.1 Behavior-роли

- `IntentRouter` - определяет какие behavior-ветки запускать на текущем запросе.
- `Guardian` - фильтрация нецелевого/вредоносного запроса, возврат пользователя в контекст ТЗ.
- `Harvester` - извлечение фактов из чата и attachment-источников в staging-ноды.
- `GroupingJudge` - дедупликация/разрешение конфликтов, создание GKG-нод и pending conflicts.
- `Consultant` - отвечает на вопросы по текущему проекту, используя GKG и raw sources.
- `Architect` - обновляет секции документа, создает pending actions, учитывает locked/manual блоки.
- `Compose` - финальная сборка ответа в чат.

### 2.2 Где находится код

- Оркестратор: `backend/worker/modules/llm_pipeline/orchestrator`.
- Узлы графа: `backend/worker/modules/llm_pipeline/orchestrator/nodes.py`.
- Конфиг роутера: `backend/worker/modules/llm_pipeline/steps/intent_router/config.py`.
- Behavior-модули: `backend/worker/modules/llm_pipeline/steps/behaviors`.
- TaskIQ задачи: `backend/worker/tasks/orchestrator_tasks.py`.

## 3. Требования

Локальная разработка:

- Python 3.12+
- Node.js 20+
- uv
- Docker + Docker Compose

Для облачного режима LLM:

- ключи провайдера для моделей, указанных в `.env`.

## 4. Переменные окружения

Скопируйте шаблон и заполните значения:

```bash
cp .env.example .env
```

Критично проверить:

- `DATABASE_URL`
- `REDIS_*`
- `RABBITMQ_*`
- `STORAGE_*`
- `LLM_PIPELINE_V3_*` (router/harvester/grouping_judge/consultant/architect)

## 5. Быстрый запуск через Docker Compose

`docker-compose.yml` поднимает весь контур: infra + backend + worker + frontend.

### 5.1 Команда запуска

```bash
docker compose up -d --build
```

### 5.2 Подготовка Prisma схемы (первый запуск)

```bash
docker compose exec backend uv run prisma db push --schema backend/app/infrastructure/persistent/prisma/schema.prisma
```

### 5.3 Доступные endpoints

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- RabbitMQ UI: `http://localhost:15672`
- SeaweedFS master UI: `http://localhost:9333`

### 5.4 Остановка

```bash
docker compose down
```

## 6. Локальный запуск без Docker-контуров приложения

Ниже вариант, когда infra работает в Docker, а backend/worker/frontend запускаются локально.

### 6.1 Поднять только инфраструктуру

```bash
docker compose up -d db redis rabbitmq seaweedfs
```

### 6.2 Установить Python зависимости

```bash
uv sync
uv run prisma generate --schema backend/app/infrastructure/persistent/prisma/schema.prisma
uv run prisma db push --schema backend/app/infrastructure/persistent/prisma/schema.prisma
```

### 6.3 Запустить backend

```bash
uv run python -m backend.app.main
```

### 6.4 Запустить worker

```bash
uv run taskiq worker backend.worker.main:broker --fs-startup
```

### 6.5 Запустить frontend

```bash
cd frontend
npm install
npm run dev
```

## 7. Основные API сценарии

### 7.1 Первичная генерация

- `POST /tz/{chat_id}/generate`
- Тело: `attachment_ids`, `template_type` (опционально), `comment` (опционально)

### 7.2 Обновление ТЗ

- `POST /tz/{chat_id}/update`
- Тело: `new_attachment_ids` и/или `comment`

### 7.3 Перегенерация блока

- `POST /tz/{chat_id}/regenerate-block`

### 7.4 Разрешение конфликта

- `POST /tz/{chat_id}/resolve-conflict`

### 7.5 Экспорт

- `POST /tz/{chat_id}/export`
- Форматы: `markdown`, `word`, `pdf`

## 8. WebSocket события

Канал: `GET /chat/ws`

События:

- `GENERATION_STATUS`
- `LLM_ANSWER`
- `PARSING_STATUS`
- `EXPORT_READY`
- `ERROR`

На фронтенде события фильтруются по `chat_id`.

## 9. Структура репозитория

```text
backend/
	app/
		web/                # FastAPI handlers
		infrastructure/     # config, DI, storage, persistence
	worker/
		tasks/              # TaskIQ tasks
		modules/
			llm_pipeline/     # orchestrator + behaviors
			parser/           # file parsing
			export/           # markdown/docx/pdf export

frontend/
	src/
		pages/
		shared/api/
		shared/ws/

docs/
	architecture/
	economics/
```

## 10. Диаграммы и экономика

В репозитории добавлены отдельные документы:

- `docs/architecture/llm-pipeline.puml` - детальная схема LLM-pipeline.
- `docs/architecture/system-overview.puml` - общая схема проекта.
- `docs/economics/llm-unit-economics.md` - расчет юнит-экономики на 1 запрос.

## 11. Частые проблемы

### 11.1 Worker не видит задачи

Убедитесь, что worker запущен как:

```bash
uv run taskiq worker backend.worker.main:broker --fs-startup
```

### 11.2 Ошибка подключения к БД внутри контейнеров

Проверьте, что `DATABASE_URL` для контейнеров ссылается на `db:5432`, а не на `localhost`.

### 11.3 Пустые ответы из LLM

Проверьте значения `LLM_PIPELINE_V3_*_MODEL`, `*_BASE_URL`, `*_API_KEY` и доступность внешнего провайдера.

### 11.4 Frontend не получает события

Проверьте cookies сессии и подписку на `/chat/ws`, а также состояние Redis Pub/Sub.
