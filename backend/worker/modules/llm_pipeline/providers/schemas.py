from dataclasses import dataclass


@dataclass
class ChatResult:
    content: str
    model: str
    latency_ms: int
    prompt_tokens: int
    completion_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


