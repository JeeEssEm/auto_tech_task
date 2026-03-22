from dishka import make_async_container
from dishka.integrations.taskiq import setup_dishka
from taskiq import TaskiqEvents, TaskiqState

from backend.worker.broker import broker, config
from backend.app.infrastructure.di.infra_provider import InfraProvider
from backend.app.infrastructure.logging import setup_logging

from backend.worker.tasks.parse_file import * # noqa
from backend.worker.tasks.orchestrator_tasks import * # noqa

from backend.worker.lifespan import create_deps_runtime
from backend.worker.modules.llm_pipeline.orchestrator.orchestrator import Orchestrator

setup_logging(debug=config.debug)

container = make_async_container(InfraProvider(config))

setup_dishka(container, broker)


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def on_startup(state: TaskiqState) -> None:
    deps_runtime = await create_deps_runtime()
    state.deps_runtime = deps_runtime
    state.deps = deps_runtime.deps
    state.orchestrator = Orchestrator(deps_runtime.deps)


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def shutdown_event(state):
    deps_runtime = getattr(state, "deps_runtime", None)
    if deps_runtime is not None:
        await deps_runtime.shutdown()
    await container.close()
