from typing import Protocol


class TaskDispatcher(Protocol):
    async def dispatch_parse_file(
            self, user_id: int, attachment_id: str, filename: str
    ) -> None: ...

    async def dispatch_generate_tz(
            self, chat_id: int, user_id: int, prompt: str
    ) -> None: ...
