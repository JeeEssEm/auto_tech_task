import asyncio

from backend.worker.modules.llm_pipeline.abstractions.ports import EmbeddingPort
from backend.worker.modules.llm_pipeline.providers.configs.embedder_settings import EmbedderSettings
from backend.worker.modules.llm_pipeline.steps.behaviors.harvester.staging import StagingNode
from backend.worker.modules.llm_pipeline.steps.embedder.schemas import EmbeddedStagingNode


class NodeEmbedder:
    def __init__(self, embedder: EmbeddingPort, settings: EmbedderSettings):
        self._embedder = embedder
        self._settings = settings

    async def execute(self, nodes: list[StagingNode]) -> list[EmbeddedStagingNode]:
        texts = [_node_to_text(node) for node in nodes]

        batches: list[tuple[int, list[str]]] = [
            (start, texts[start: start + self._settings.batch_size])
            for start in range(0, len(texts), self._settings.batch_size)
        ]

        semaphore = asyncio.Semaphore(self._settings.concurrency)
        results: list[list[float]] = [[] for _ in nodes]

        async def process_batch(start_idx: int, batch_texts: list[str]) -> None:
            async with semaphore:
                embeddings = await self._embedder.embed(batch_texts)
                for i, emb in enumerate(embeddings):
                    results[start_idx + i] = emb

        await asyncio.gather(*[process_batch(s, b) for s, b in batches])

        return [
            EmbeddedStagingNode(node=node, embedding=emb)
            for node, emb in zip(nodes, results)
        ]


def _node_to_text(node: StagingNode) -> str:
    """
    scope + property + value + обрезанная цитата.
    fastembed сам добавит нужный prefix для e5.
    """
    parts = [
        f"{node.scope}.",
        f"{node.property}: {node.value}.",
    ]
    if node.content_raw:
        parts.append(f"Цитата: {node.content_raw[:200]}")
    return " ".join(parts)
