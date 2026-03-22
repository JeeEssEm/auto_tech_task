from prisma import Prisma
from prisma.models import GenerationRun

from backend.app.domain.chat.value_objects.types import GenerationRunStatus


class GenerationRepository:
    def __init__(self, db: Prisma):
        self._db = db

    async def create_run(self, chat_id: int, user_id: int) -> GenerationRun:
        return await self._db.generationrun.create(
            data={
                "chat_id": chat_id,
                "user_id": user_id,
                "status": GenerationRunStatus.PENDING,
                "progress": 0,
            }
        )

    async def update_status(
            self,
            run_id: int,
            status: str,
            step: str | None = None,
            progress: int = 0,
    ) -> GenerationRun:
        return await self._db.generationrun.update(
            where={"id": run_id},
            data={
                "status": status,
                "step": step,
                "progress": progress,
            },
        )

    async def save_state(self, run_id: int, state_json: str) -> None:
        await self._db.generationrun.update(
            where={"id": run_id},
            data={"state_json": state_json},
        )

    async def save_result(self, run_id: int, result_key: str) -> None:
        await self._db.generationrun.update(
            where={"id": run_id},
            data={
                "result_key": result_key,
                "status": GenerationRunStatus.COMPLETED,
                "progress": 100,
            },
        )

    async def mark_failed(self, run_id: int, error: str) -> None:
        await self._db.generationrun.update(
            where={"id": run_id},
            data={
                "status": GenerationRunStatus.FAILED,
                "error": error,
            },
        )

    async def get_latest_run(self, chat_id: int) -> GenerationRun | None:
        return await self._db.generationrun.find_first(
            where={"chat_id": chat_id},
            order={"created_at": "desc"},
        )

    async def has_active_run(self, chat_id: int) -> bool:
        run = await self._db.generationrun.find_first(
            where={
                "chat_id": chat_id,
                "status": {"in": [
                    GenerationRunStatus.PENDING,
                    GenerationRunStatus.INGESTING,
                    GenerationRunStatus.COMPILING,
                ]},
            },
            order={"created_at": "desc"},
        )
        return run is not None

    async def get_completed_runs(self, chat_id: int) -> list[GenerationRun]:
        return await self._db.generationrun.find_many(
            where={"chat_id": chat_id, "status": GenerationRunStatus.COMPLETED},
            order={"created_at": "asc"},
        )

    async def has_result_key_for_chat(self, chat_id: int, result_key: str) -> bool:
        run = await self._db.generationrun.find_first(
            where={
                "chat_id": chat_id,
                "result_key": result_key,
            }
        )
        return run is not None
