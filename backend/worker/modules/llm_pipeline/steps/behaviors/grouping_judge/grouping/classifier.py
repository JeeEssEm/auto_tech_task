from itertools import combinations

from backend.worker.modules.llm_pipeline.steps.behaviors.grouping_judge.grouping.merging_technics import _cosine_distance
from backend.worker.modules.llm_pipeline.steps.behaviors.grouping_judge.schemas import ClusterResult
from backend.worker.modules.llm_pipeline.steps.embedder.schemas import EmbeddedStagingNode


def _are_values_equivalent(a: EmbeddedStagingNode, b: EmbeddedStagingNode) -> bool:
    """Считаем значения эквивалентными если эмбеддинги достаточно близки."""
    return _cosine_distance(a.embedding, b.embedding) < 0.15


def _pick_best(nodes: list[EmbeddedStagingNode]) -> EmbeddedStagingNode:
    # нам же пофиг на то, какая конкретно нода выбрана, если они все одинаковые? Значит делаем по-тупому, но хотя бы как-то :)
    return max(nodes, key=lambda n: len(n.node.content_raw))


def classify_cluster(cluster: list[EmbeddedStagingNode]) -> ClusterResult | None:
    """
    Быстрые правила без LLM. Возвращает None если нужен судья.

    Порядок проверок важен:
    1. Одна нода — сразу NO_CONFLICT.
    2. Все ноды из одного источника → CONFLICT между чанками.
    3. Все значения эквивалентны → DUPLICATE.
    4. Иначе → None (судья).
    """
    unique_sources = {n.node.source_id for n in cluster}
    all_source_ids = list(unique_sources)
    if len(cluster) == 1:
        return ClusterResult(
            status="NO_CONFLICT",
            winning_node=cluster[0],
            rationale="Единственная нода в кластере.",
            all_source_ids=all_source_ids
        )

    if len(unique_sources) == 1:
        # Один источник — конфликт между чанками. Побеждает последний чанк.
        winner = max(cluster, key=lambda n: n.node.chunk_index)
        return ClusterResult(
            status="RESOLVED",
            winning_node=winner,
            rationale=(
                f"Все ноды из источника '{winner.node.source_id}'. "
                f"Выбран чанк {winner.node.chunk_index} как наиболее поздний."
            ),
            all_source_ids=all_source_ids
        )

    # Проверяем эквивалентность всех пар значений
    # all_equivalent = all(
    #     _are_values_equivalent(a, b)
    #         for a, b in combinations(cluster, 2)
    # )
    # if all_equivalent:
    #     winner = _pick_best(cluster)
    #     return ClusterResult(
    #         status="DUPLICATE",
    #         winning_node=winner,
    #         rationale="Все значения семантически эквивалентны. Выбрана нода с наибольшим авторитетом.",
    #         all_source_ids=all_source_ids
    #     )

    return None  # нужен LLM-судья
