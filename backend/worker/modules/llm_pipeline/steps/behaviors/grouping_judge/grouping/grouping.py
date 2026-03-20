from backend.worker.modules.llm_pipeline.steps.embedder.schemas import EmbeddedStagingNode


def group_by_exact(
    nodes: list[EmbeddedStagingNode],
) -> dict[tuple[str, str], list[EmbeddedStagingNode]]:
    """
    Группирует ноды по точному совпадению (scope, property).
    Ключ нормализуется: lowercase + strip, чтобы 'DB' и 'db' не дали два кластера.
    """
    clusters: dict[tuple[str, str], list[EmbeddedStagingNode]] = {}
    for enode in nodes:
        key = (
            enode.node.scope.strip().lower(),
            enode.node.property.strip().lower(),
        )
        clusters.setdefault(key, []).append(enode)
    return clusters
