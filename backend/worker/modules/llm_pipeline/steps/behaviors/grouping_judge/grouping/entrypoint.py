from backend.worker.modules.llm_pipeline.steps.behaviors.grouping_judge.grouping.classifier import classify_cluster
from backend.worker.modules.llm_pipeline.steps.behaviors.grouping_judge.grouping.grouping import group_by_exact
from backend.worker.modules.llm_pipeline.steps.behaviors.grouping_judge.grouping.merging_technics import semantic_merge
from backend.worker.modules.llm_pipeline.steps.behaviors.grouping_judge.schemas import ClusterResult
from backend.worker.modules.llm_pipeline.steps.embedder.schemas import EmbeddedStagingNode


def group_and_classify(
        nodes: list[EmbeddedStagingNode],
        semantic_threshold: float = 0.05,
) -> tuple[list[ClusterResult], list[list[EmbeddedStagingNode]]]:
    """
    Возвращает:
    - resolved: кластеры, решённые без LLM
    - needs_judge: кластеры, которые нужно передать судье
    """
    exact_clusters = group_by_exact(nodes)
    merged_clusters = semantic_merge(exact_clusters, distance_threshold=semantic_threshold)

    resolved: list[ClusterResult] = []
    needs_judge: list[list[EmbeddedStagingNode]] = []

    for cluster in merged_clusters:
        result = classify_cluster(cluster)
        if result is not None:
            resolved.append(result)
        else:
            needs_judge.append(cluster)

    return resolved, needs_judge
