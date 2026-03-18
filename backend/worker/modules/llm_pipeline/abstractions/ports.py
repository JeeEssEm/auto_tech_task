from abc import ABC, abstractmethod
from typing import Any, TypeVar, Type
from pydantic import BaseModel

ResponseT = TypeVar('ResponseT', bound=BaseModel)


class LLMChatPort(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        response_model: Type[ResponseT],
        event_id: str | None = None,
    ) -> ResponseT:
        """Chat with LLM and parse response as Pydantic model.
        
        Args:
            messages: List of messages with role and content
            model: Model name/identifier
            temperature: Temperature for generation
            max_tokens: Max tokens in response
            response_model: Pydantic model to parse response into
            event_id: Optional event ID for tracing
            
        Returns:
            Parsed and validated Pydantic model instance
            
        Raises:
            ValueError: If unable to parse valid response after max retries
        """
        raise NotImplementedError


class EmbeddingPort(ABC):
    @abstractmethod
    async def embed(self, texts: list[str], model: str) -> list[list[float]]:
        raise NotImplementedError


class ModerationPort(ABC):
    @abstractmethod
    async def moderate(self, text: str) -> dict[str, Any]:
        raise NotImplementedError
