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
# Import task callables directly to force decorator side effects during broker module import.
from backend.worker.tasks.orchestrator_tasks import (  # noqa: F401,E402
    create_tz_from_template_task as _create_tz_from_template_task,
    lock_block_task as _lock_block_task,
    process_message_task as _process_message_task,
    regenerate_block_task as _regenerate_block_task,
    resolve_conflict_task as _resolve_conflict_task,
    update_tz_with_sources_task as _update_tz_with_sources_task,
)
from backend.worker.tasks.parse_file import parse_file_task as _parse_file_task  # noqa: F401,E402
