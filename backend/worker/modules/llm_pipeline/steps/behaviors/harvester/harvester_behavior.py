from backend.worker.modules.llm_pipeline.abstractions.ports import LLMChatPort
from backend.worker.modules.llm_pipeline.steps.behaviors.harvester.active_working_memory.chunker import (
    chunk_document,
    Chunk
)
from backend.worker.modules.llm_pipeline.steps.behaviors.harvester.active_working_memory.manager import AWMManager
from backend.worker.modules.llm_pipeline.steps.behaviors.harvester.active_working_memory.schemas import Evidence
from backend.worker.modules.llm_pipeline.steps.behaviors.harvester.config import HarvesterSettings
from backend.worker.modules.llm_pipeline.steps.behaviors.harvester.llm_response_commands import (
    ResolveCommand,
    HarvesterLLMOutput
)
from backend.worker.modules.llm_pipeline.steps.behaviors.harvester.prompting import (
    build_harvester_user_prompt,
    build_harvester_system_prompt
)
from backend.worker.modules.llm_pipeline.steps.behaviors.harvester.staging import StagingNode


class HarvesterBehavior:
    def __init__(self, chat_port: LLMChatPort, settings: HarvesterSettings):
        self._chat = chat_port
        self._settings = settings

    async def process_source(
            self,
            source_id: str,
            text: str,
            source_meta: str,
    ) -> list[StagingNode]:

        chunks = chunk_document(text, source_meta)
        staging: list[StagingNode] = []
        awm = AWMManager(eviction_max_open_topics=self._settings.eviction_max_open_topics)
        on_resolved = self._build_on_resolved(source_id=source_id, staging=staging)

        tail_context = ""

        for chunk in chunks:
            await self._process_chunk(
                chunk=chunk,
                awm=awm,
                tail_context=tail_context,
                on_resolved=on_resolved,
            )
            tail_context = chunk.text[-800:]  # ~300 токенов

        for topic in list(awm.state.active_topics):
            on_resolved(
                topic, ResolveCommand(
                    topic_id=topic.topic_id,
                    final_value=topic.current_value,
                    evidence=topic.evidence_backlog[-1] if topic.evidence_backlog else Evidence(
                        chunk_index=len(chunks) - 1,
                        quote="[END OF DOCUMENT: topic not fully resolved]",
                    ),
                )
            )

        return staging

    @staticmethod
    def _build_on_resolved(source_id: str, staging: list[StagingNode]):
        def on_resolved(topic, cmd: ResolveCommand) -> None:
            staging.append(
                StagingNode(
                    source_id=source_id,
                    scope=topic.scope,
                    property=topic.property,
                    value=cmd.final_value,
                    content_raw=cmd.evidence.quote,
                    author=cmd.evidence.author,
                    timestamp=cmd.evidence.timestamp,
                    chunk_index=cmd.evidence.chunk_index,
                )
            )

        return on_resolved

    async def _process_chunk(
            self,
            chunk: Chunk,
            awm: AWMManager,
            tail_context: str,
            on_resolved,
    ) -> None:
        retries = 0
        while True:
            output = await self._call_llm(chunk, awm, tail_context)
            awm.apply(output, chunk.index, on_resolved)

            # self-correction loop
            if output.has_remaining_facts and retries < self._settings.max_self_correction_retries:
                retries += 1
                # передаём обновлённый AWM, тот же чанк
                continue
            break

    async def _call_llm(
            self,
            chunk: Chunk,
            awm: AWMManager,
            tail_context: str,
    ) -> HarvesterLLMOutput:
        user_prompt = build_harvester_user_prompt(
            source_context=chunk.source_context,
            awm_rendered=awm.render_for_prompt(),
            tail_context=tail_context,
            current_chunk=chunk.text,
            chunk_index=chunk.index,
        )
        return await self._chat.chat(
            model=self._settings.model,
            max_tokens=self._settings.max_tokens,
            temperature=0.1,
            messages=[
                {"role": "system", "content": build_harvester_system_prompt()},
                {"role": "user", "content": user_prompt},
            ],
            response_model=HarvesterLLMOutput,
        )
