from typing import Protocol


class TaskDispatcher(Protocol):
    async def dispatch_parse_file(
            self, user_id: int, attachment_id: str, filename: str
    ) -> None: ...

    async def dispatch_generate_tz(
            self, chat_id: int, user_id: int, prompt: str
    ) -> None: ...

    async def dispatch_run_full_pipeline(
            self, chat_id: int,
            user_id: int,
            parsed_files: list[dict[str, str]],
            template_type: str,
            comment: str | None = None,
    ) -> None:
        ...

    async def dispatch_update_tz(
            self, chat_id: int,
            user_id: int,
            new_parsed_files: list[dict[str, str]] | None = None,
            comment: str | None = None
    ) -> None:
        ...

    async def dispatch_regenerate_block(
            self, chat_id: int,
            user_id: int,
            block_id: str,
            instruction: str | None = None
    ) -> None:
        ...

    async def dispatch_resolve_conflict(
            self,
            chat_id: int,
            user_id: int,
            action_id: str,
            resolution: str,
    ) -> None:
        ...

    async def dispatch_generate_custom_block(
            self,
            chat_id: int,
            user_id: int,
            field_path: str,
            custom_topic: str,
    ) -> None:
        ...

    async def dispatch_export_tz(
            self,
            chat_id: int,
            user_id: int,
            result_key: str,
            format: str,
    ) -> None:
        ...
