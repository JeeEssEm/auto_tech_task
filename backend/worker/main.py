from dishka import make_async_container
from dishka.integrations.taskiq import setup_dishka

from backend.worker.broker import broker, config
from backend.app.infrastructure.di.infra_provider import InfraProvider
from backend.app.infrastructure.logging import setup_logging

import backend.worker.tasks.generate_tz_task  # noqa
import backend.worker.tasks.parse_file  # noqa
import backend.worker.tasks.tz_pipeline_tasks  # noqa

setup_logging(debug=config.debug)

container = make_async_container(InfraProvider(config))

setup_dishka(container, broker)


@broker.on_event("shutdown")
async def shutdown_event(state):
    await container.close()
