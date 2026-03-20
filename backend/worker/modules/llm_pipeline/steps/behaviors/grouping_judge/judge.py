import asyncio
import json

from backend.worker.modules.llm_pipeline.abstractions.ports import LLMChatPort
from backend.worker.modules.llm_pipeline.steps.behaviors.grouping_judge.config import GroupingJudgeSettings
from backend.worker.modules.llm_pipeline.steps.behaviors.grouping_judge.grouping.entrypoint import group_and_classify
from backend.worker.modules.llm_pipeline.steps.behaviors.grouping_judge.prompting import build_judge_prompt
from backend.worker.modules.llm_pipeline.steps.behaviors.grouping_judge.schemas import (
    ClusterResult, JudgeResponse,
    GroupingJudgeResult, GKGNode, PendingConflict
)
from backend.worker.modules.llm_pipeline.steps.embedder.schemas import EmbeddedStagingNode


class GroupingJudgeBehavior:
    def __init__(self, chat_port: LLMChatPort, settings: GroupingJudgeSettings):
        self._chat = chat_port
        self._settings = settings

    async def run(self, nodes: list[EmbeddedStagingNode]) -> GroupingJudgeResult:
        """
        Принимает плоский список нод (новые из Harvester + существующие из GKG,
        конвертированные обратно в EmbeddedStagingNode caller-ом).

        Возвращает:
        - gkg_nodes: факты готовые к записи/обновлению в GKG
        - pending_conflicts: конфликты требующие ответа пользователя
        """
        resolved_without_llm, needs_judge = group_and_classify(
            nodes,
            semantic_threshold=self._settings.semantic_threshold,
        )

        judge_results = await self._run_judge_batched(needs_judge)

        all_results = resolved_without_llm + judge_results
        return self._assemble_result(all_results)

    async def _run_judge_batched(
            self,
            clusters: list[list[EmbeddedStagingNode]],
    ) -> list[ClusterResult]:
        """Запускает судью параллельно с ограничением concurrency."""
        semaphore = asyncio.Semaphore(self._settings.judge_concurrency)

        async def judge_one(cluster: list[EmbeddedStagingNode]) -> ClusterResult:
            async with semaphore:
                return await self._call_judge(cluster)

        return list(await asyncio.gather(*[judge_one(c) for c in clusters]))

    async def _call_judge(
            self,
            cluster: list[EmbeddedStagingNode],
    ) -> ClusterResult:
        user_prompt = build_judge_prompt(cluster)
        try:
            response = await self._chat.chat(
                messages=[
                    {"role": "user", "content": user_prompt},
                ],
                model=self._settings.model,
                temperature=self._settings.temperature,
                max_tokens=self._settings.max_tokens,
                response_model=JudgeResponse,
                event_id=f"judge_{cluster[0].node.scope}_{cluster[0].node.property}",
            )
            raw = response.model_dump_json()
        except Exception as e:
            # LLM недоступен — не теряем данные, уходим в UNRESOLVED
            raw = f'{{"verdict": "UNRESOLVED", "rationale": "LLM error: {e}"}}'

        return parse_judge_response(raw, cluster)

    def _assemble_result(self, results: list[ClusterResult]) -> GroupingJudgeResult:
        gkg_nodes: list[GKGNode] = []
        pending_conflicts: list[PendingConflict] = []

        for result in results:
            output = _cluster_result_to_output(result)
            if isinstance(output, list):
                gkg_nodes.extend(output)
            elif isinstance(output, GKGNode):
                gkg_nodes.append(output)
            elif isinstance(output, PendingConflict):
                pending_conflicts.append(output)

        return GroupingJudgeResult(
            gkg_nodes=gkg_nodes,
            pending_conflicts=pending_conflicts,
        )


def parse_judge_response(
        raw_response: str,
        cluster: list[EmbeddedStagingNode],
) -> ClusterResult:
    """
    Парсит JSON от судьи и собирает ClusterResult.
    При невалидном JSON — возвращает UNRESOLVED чтобы не потерять данные.
    """
    all_source_ids = list({n.node.source_id for n in cluster})

    try:
        data = json.loads(raw_response)
        response = JudgeResponse(**data)
    except Exception as e:
        return ClusterResult(
            status="UNRESOLVED",
            conflict_options=cluster,
            all_source_ids=all_source_ids,
            rationale=f"Не удалось распарсить ответ судьи: {e}. Требуется ручное разрешение.",
        )

    if response.verdict == "RESOLVED":
        if response.winning_index is None or response.winning_index >= len(cluster):
            return ClusterResult(
                status="UNRESOLVED",
                conflict_options=cluster,
                all_source_ids=all_source_ids,
                rationale=f"Судья вернул RESOLVED, но winning_index невалиден: {response.winning_index}",
            )
        return ClusterResult(
            status="RESOLVED",
            winning_node=cluster[response.winning_index],
            all_source_ids=all_source_ids,
            rationale=response.rationale,
        )

    if response.verdict == "UNRESOLVED":
        return ClusterResult(
            status="UNRESOLVED",
            conflict_options=cluster,
            all_source_ids=all_source_ids,
            rationale=response.rationale,
        )

    if response.verdict == "SPLIT":
        if not response.split_groups:
            # Судья сказал SPLIT но не дал групп — трактуем как UNRESOLVED
            return ClusterResult(
                status="UNRESOLVED",
                conflict_options=cluster,
                all_source_ids=all_source_ids,
                rationale=f"Судья вернул SPLIT без split_groups. {response.rationale}",
            )

        # Каждая группа — одна нода-победитель (лучшая цитата внутри группы)
        split_nodes: list[EmbeddedStagingNode] = []
        for group_indices in response.split_groups:
            group = [cluster[i] for i in group_indices if i < len(cluster)]
            if group:
                best = max(group, key=lambda n: len(n.node.content_raw))
                split_nodes.append(best)

        return ClusterResult(
            status="SPLIT",
            split_nodes=split_nodes,
            all_source_ids=all_source_ids,
            rationale=response.rationale,
        )

    # Неизвестный verdict — defensive fallback
    return ClusterResult(
        status="UNRESOLVED",
        conflict_options=cluster,
        all_source_ids=all_source_ids,
        rationale=f"Неизвестный verdict от судьи: {response.verdict}",
    )


def _cluster_result_to_output(
        result: ClusterResult,
) -> GKGNode | PendingConflict | list[GKGNode]:
    """
    SPLIT возвращает list[GKGNode] — несколько независимых фактов.
    Остальные возвращают один GKGNode или PendingConflict.
    """
    if result.status == "UNRESOLVED":
        first = result.conflict_options[0].node
        return PendingConflict(
            scope=first.scope,
            property=first.property,
            options=result.conflict_options,
            rationale=result.rationale,
        )

    if result.status == "SPLIT":
        return [
            GKGNode(
                scope=node.node.scope,
                property=node.node.property,
                value=node.node.value,
                content_raw=node.node.content_raw,
                status="NO_CONFLICT",
                source_ids=[node.node.source_id],
                rationale=result.rationale,
                embedding=node.embedding,
            )
            for node in result.split_nodes
        ]

    # NO_CONFLICT, DUPLICATE, RESOLVED — есть winning_node
    winner = result.winning_node
    gkg_status = (
        "NO_CONFLICT" if result.status in ("NO_CONFLICT", "DUPLICATE")
        else "RESOLVED"
    )
    return GKGNode(
        scope=winner.node.scope,
        property=winner.node.property,
        value=winner.node.value,
        content_raw=winner.node.content_raw,
        status=gkg_status,
        source_ids=result.all_source_ids,
        rationale=result.rationale,
        embedding=winner.embedding
    )
