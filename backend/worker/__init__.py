from taskiq import AsyncBroker
from taskiq_aio_pika import AioPikaBroker
from taskiq_redis import RedisAsyncResultBackend

from backend.app.infrastructure.config import AppSettings
from backend.worker.example.heavy_task import heavy_task


tasks = [heavy_task]


def register_tasks(broker: AsyncBroker):
    for task in tasks:
        broker.register_task(task, task_name=task.__name__)


def create_broker_from_config(config: AppSettings):
    return AioPikaBroker(
        url=config.rabbitmq.connection_url,
        queue_name=config.task_queue.queue_name
    ).with_result_backend(
        RedisAsyncResultBackend(
            redis_url=config.redis.connection_url
        )
    )
