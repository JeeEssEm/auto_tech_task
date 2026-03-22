from taskiq_aio_pika import AioPikaBroker
from taskiq_redis import RedisAsyncResultBackend

from backend.app.infrastructure.config import AppSettings

config = AppSettings()

result_backend = RedisAsyncResultBackend(redis_url=config.redis.connection_url)

broker = AioPikaBroker(
    url=config.rabbitmq.connection_url,
    queue_name=config.task_queue.queue_name
).with_result_backend(result_backend)

# Ensure tasks are registered even when worker starts via `backend.worker.broker:broker`.
from backend.worker.tasks import orchestrator_tasks as _orchestrator_tasks  # noqa: F401,E402
from backend.worker.tasks import parse_file as _parse_file_tasks  # noqa: F401,E402
