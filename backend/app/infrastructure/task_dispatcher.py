import structlog

from backend.app.domain.ports import TaskDispatcher

logger = structlog.get_logger(__name__)


class TaskiqDispatcher(TaskDispatcher):
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
        from backend.worker.tasks.generate_tz_task import generate_tz_task

        logger.info(
            "dispatching_generate_tz",
            chat_id=chat_id,
            user_id=user_id,
            prompt_length=len(prompt),
        )
        await generate_tz_task.kiq(
            chat_id=chat_id, user_id=user_id, prompt=prompt
        )

    async def dispatch_run_full_pipeline(
            self, chat_id: int,
            user_id: int,
            parsed_files: list[dict[str, str]], ) -> None:
        from backend.worker.tasks.tz_pipeline_tasks import full_pipeline_task

        await full_pipeline_task.kiq(
            chat_id=chat_id,
            user_id=user_id,
            parsed_files=parsed_files
        )

    async def dispatch_update_tz(
            self, chat_id: int,
            user_id: int,
            new_parsed_files: list[dict[str, str]] | None = None,
            comment: str | None = None
    ) -> None:
        from backend.worker.tasks.tz_pipeline_tasks import update_tz_task

        await update_tz_task.kiq(
            chat_id=chat_id,
            user_id=user_id,
            new_parsed_files=new_parsed_files,
            comment=comment
        )

    async def dispatch_regenerate_block(
            self, chat_id: int,
            user_id: int,
            field_path: str,
            instruction: str | None = None
    ) -> None:
        from backend.worker.tasks.tz_pipeline_tasks import regenerate_block_task

        await regenerate_block_task.kiq(
            chat_id=chat_id,
            user_id=user_id,
            field_path=field_path,
            instruction=instruction
        )

    async def dispatch_generate_custom_block(
            self,
            chat_id: int,
            user_id: int,
            field_path: str,
            custom_topic: str,
    ) -> None:
        from backend.worker.tasks.tz_pipeline_tasks import generate_custom_block_task

        await generate_custom_block_task.kiq(
            chat_id=chat_id,
            user_id=user_id,
            field_path=field_path,
            custom_topic=custom_topic
        )

    async def dispatch_export_tz(
            self,
            chat_id: int,
            user_id: int,
            result_key: str,
            format: str,
    ) -> None:
        from backend.worker.tasks.tz_pipeline_tasks import export_tz_task

        await export_tz_task.kiq(
            chat_id=chat_id,
            user_id=user_id,
            result_key=result_key,
            export_format=format,
        )
