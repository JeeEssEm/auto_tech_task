import asyncio

from fastembed import TextEmbedding

from backend.worker.modules.llm_pipeline.abstractions.ports import EmbeddingPort


class FastEmbedEmbeddingPort(EmbeddingPort):
    def __init__(self, model_name: str = "intfloat/multilingual-e5-large"):
        self._model = TextEmbedding(model_name)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        loop = asyncio.get_running_loop()
        tasks = await loop.run_in_executor(None, lambda: self._model.embed(texts))

        return [res.tolist() for res in tasks]
