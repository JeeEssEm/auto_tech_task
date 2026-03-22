import os
from pathlib import Path
from dataclasses import dataclass
from typing import Awaitable, Callable

from backend.worker.modules.llm_pipeline.orchestrator.backend_deps_factory import create_backend_runtime
from backend.worker.modules.llm_pipeline.orchestrator.deps_factory import create_local_runtime
from backend.worker.modules.llm_pipeline.orchestrator.nodes import OrchestratorDeps

_deps: OrchestratorDeps | None = None


@dataclass
class WorkerDepsRuntime:
    deps: OrchestratorDeps
    shutdown: Callable[[], Awaitable[None]]


async def create_deps_runtime() -> WorkerDepsRuntime:
    mode = os.getenv("LLM_PIPELINE_V3_DEPS_MODE", "postgres").lower().strip()

    if mode == "local":
        state_path = Path(
            os.getenv("LLM_PIPELINE_V3_STATE_PATH", "artifacts/orchestrator_worker_state.json")
        )
        local_runtime = await create_local_runtime(state_path)

        async def _noop_shutdown() -> None:
            return

        return WorkerDepsRuntime(deps=local_runtime.deps, shutdown=_noop_shutdown)

    backend_runtime = await create_backend_runtime()
    return WorkerDepsRuntime(deps=backend_runtime.deps, shutdown=backend_runtime.shutdown)
