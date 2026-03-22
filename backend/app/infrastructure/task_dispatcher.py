import structlog

from backend.app.domain.ports import TaskDispatcher

logger = structlog.get_logger(__name__)


class TaskiqDispatcher(TaskDispatcher):
    @staticmethod
    def _build_attachments(parsed_files: list[dict[str, str]] | None) -> list[dict[str, str]]:
        if not parsed_files:
            return []

        attachments: list[dict[str, str]] = []
        for item in parsed_files:
            source_id = str(item.get("id") or "")
            text = str(item.get("content") or "")
            name = str(item.get("name") or item.get("type") or source_id or "source")

            if not source_id or not text:
                continue

            attachments.append(
                {
                    "source_id": source_id,
                    "text": text,
                    "name": name,
                }
            )
        return attachments

    async def dispatch_parse_file(
        self, user_id: int, attachment_id: str, filename: str
    ) -> None:
        from backend.worker.tasks.parse_file import parse_file_task

        logger.info(
            "dispatching_parse_file",
            user_id=user_id,
            attachment_id=attachment_id,
            filename=filename,
        )
        await parse_file_task.kiq(
            user_id=user_id, attachment_id=attachment_id, filename=filename
        )

    async def dispatch_generate_tz(
        self, chat_id: int, user_id: int, prompt: str
    ) -> None:
        from backend.worker.tasks.orchestrator_tasks import process_message_task

        logger.info(
            "dispatching_generate_tz",
            chat_id=chat_id,
            user_id=user_id,
            prompt_length=len(prompt),
        )
        await process_message_task.kiq(
            project_id=chat_id,
            user_id=user_id,
            user_input=prompt,
            attachments=[],
        )

    async def dispatch_run_full_pipeline(
            self, chat_id: int,
            user_id: int,
            parsed_files: list[dict[str, str]],
            template_type: str,
            comment: str | None = None,
    ) -> None:
        from backend.worker.tasks.orchestrator_tasks import create_tz_from_template_task

        attachments = self._build_attachments(parsed_files)

        await create_tz_from_template_task.kiq(
            project_id=chat_id,
            user_id=user_id,
            template_type=template_type,
            attachments=attachments,
            comment=comment,
        )

    async def dispatch_update_tz(
            self, chat_id: int,
            user_id: int,
            new_parsed_files: list[dict[str, str]] | None = None,
            comment: str | None = None
    ) -> None:
        from backend.worker.tasks.orchestrator_tasks import update_tz_with_sources_task

        attachments = self._build_attachments(new_parsed_files)

        await update_tz_with_sources_task.kiq(
            project_id=chat_id,
            user_id=user_id,
            attachments=attachments,
            comment=comment,
        )

    async def dispatch_regenerate_block(
            self, chat_id: int,
            user_id: int,
            block_id: str,
            instruction: str | None = None
    ) -> None:
        from backend.worker.tasks.orchestrator_tasks import regenerate_block_task

        trigger_reason = "explicit_regen_request"
        if instruction:
            trigger_reason = f"explicit_regen_request:{instruction}"

        await regenerate_block_task.kiq(
            project_id=chat_id,
            block_id=block_id,
            trigger_reason=trigger_reason,
        )

    async def dispatch_resolve_conflict(
            self,
            chat_id: int,
            user_id: int,
            action_id: str,
            resolution: str,
    ) -> None:
        from backend.worker.tasks.orchestrator_tasks import resolve_conflict_task

        await resolve_conflict_task.kiq(
            project_id=chat_id,
            action_id=action_id,
            resolution=resolution,
        )

    async def dispatch_generate_custom_block(
            self,
            chat_id: int,
            user_id: int,
            field_path: str,
            custom_topic: str,
    ) -> None:
        from backend.worker.tasks.orchestrator_tasks import process_message_task

        prompt = (
            f"Generate or update block '{field_path}'. "
            f"Topic: {custom_topic}."
        )
        await process_message_task.kiq(
            project_id=chat_id,
            user_id=user_id,
            user_input=prompt,
            attachments=[],
        )

    async def dispatch_export_tz(
            self,
            chat_id: int,
            user_id: int,
            result_key: str,
            format: str,
    ) -> None:
        raise NotImplementedError("Export task is not implemented for orchestrator pipeline")