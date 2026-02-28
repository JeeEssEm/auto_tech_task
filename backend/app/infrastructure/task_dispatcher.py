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
        from backend.worker.tasks.stupid_answer_task import generate_tz_task

        logger.info(
            "dispatching_generate_tz",
            chat_id=chat_id,
            user_id=user_id,
            prompt_length=len(prompt),
        )
        await generate_tz_task.kiq(
            chat_id=chat_id, user_id=user_id, prompt=prompt
        )