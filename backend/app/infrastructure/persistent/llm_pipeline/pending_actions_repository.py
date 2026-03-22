from __future__ import annotations

from datetime import UTC, datetime

from prisma import Prisma


class PendingActionsRepository:
    def __init__(self, db: Prisma):
        self._db = db

    async def create_pending_action(
        self,
        project_id: int,
        question: str,
        options: list[str] | None,
    ) -> str:
        row = await self._db.llmpendingaction.create(
            data={
                "project_id": project_id,
                "question": question,
                "options_json": options,
                "status": "WAITING",
            }
        )
        return row.id

    async def get_waiting_questions(self, project_id: int) -> list[str]:
        rows = await self._db.llmpendingaction.find_many(
            where={"project_id": project_id, "status": "WAITING"},
            order={"created_at": "asc"},
        )
        return [row.question for row in rows]

    async def get_waiting_actions(self, project_id: int) -> list[dict]:
        rows = await self._db.llmpendingaction.find_many(
            where={"project_id": project_id, "status": "WAITING"},
            order={"created_at": "asc"},
        )
        out: list[dict] = []
        for row in rows:
            out.append(
                {
                    "id": row.id,
                    "question": row.question,
                    "options": list(row.options_json or []),
                    "status": row.status,
                    "created_at": row.created_at.isoformat(),
                }
            )
        return out

    async def resolve_pending_action(
        self,
        project_id: int,
        action_id: str,
        resolution: str,
    ) -> dict | None:
        row = await self._db.llmpendingaction.find_first(
            where={"id": action_id, "project_id": project_id, "status": "WAITING"},
        )
        if row is None:
            return None

        now = datetime.now(UTC)
        await self._db.llmpendingaction.update(
            where={"id": action_id},
            data={
                "status": "RESOLVED",
                "resolution": resolution,
                "resolved_at": now,
            },
        )
        return {
            "id": row.id,
            "project_id": row.project_id,
            "question": row.question,
            "resolution": resolution,
        }
