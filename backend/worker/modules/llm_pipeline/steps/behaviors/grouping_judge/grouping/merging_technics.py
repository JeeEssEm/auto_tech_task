from itertools import combinations

import numpy as np

from backend.worker.modules.llm_pipeline.steps.embedder.schemas import EmbeddedStagingNode


def _cosine_distance(a: list[float], b: list[float]) -> float:
    va, vb = np.array(a), np.array(b)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0:
        return 1.0
    return float(1.0 - np.dot(va, vb) / denom)


def _min_distance_between_clusters(
        cluster_a: list[EmbeddedStagingNode],
        cluster_b: list[EmbeddedStagingNode],
) -> float:
    """
    Минимальное косинусное расстояние между любыми двумя нодами из разных кластеров.
    O(n*m), где n, m — размеры кластеров. На реальных объёмах несущественно.
    """
    return min(
        _cosine_distance(a.embedding, b.embedding)
            for a in cluster_a
            for b in cluster_b
    )


def semantic_merge(
        clusters: dict[tuple[str, str], list[EmbeddedStagingNode]],
        distance_threshold: float = 0.15,
) -> list[list[EmbeddedStagingNode]]:
    """
    Склеивает кластеры с разными (scope, property), но семантически близкими нодами.

    Алгоритм: union-find по парам кластеров, чьё min-расстояние < порога.
    Возвращает список финальных кластеров (уже без ключей — они нам больше не нужны).
    """
    keys = list(clusters.keys())
    # Union-Find
    parent = {k: k for k in keys}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        parent[find(x)] = find(y)

    for ka, kb in combinations(keys, 2):
        dist = _min_distance_between_clusters(clusters[ka], clusters[kb])
        if dist < distance_threshold:
            union(ka, kb)

    # Собираем финальные группы
    merged: dict[tuple, list[EmbeddedStagingNode]] = {}
    for k in keys:
        root = find(k)
        merged.setdefault(root, []).extend(clusters[k])

    return list(merged.values())

