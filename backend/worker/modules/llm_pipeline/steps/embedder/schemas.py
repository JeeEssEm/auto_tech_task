from pydantic import BaseModel

from backend.worker.modules.llm_pipeline.steps.behaviors.harvester.staging import StagingNode


class EmbeddedStagingNode(BaseModel):
    node: StagingNode
    embedding: list[float]
