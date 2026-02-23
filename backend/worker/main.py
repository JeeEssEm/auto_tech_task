from dishka import make_async_container
from dishka.integrations.taskiq import setup_dishka

from backend.worker.broker import broker, config
from backend.app.infrastructure.di.infra_provider import InfraProvider

import backend.worker.tasks.stupid_answer_task # noqa

container = make_async_container(InfraProvider(config))

setup_dishka(container, broker)


@broker.on_event("shutdown")
async def shutdown_event(state):
    await state.container.close()
