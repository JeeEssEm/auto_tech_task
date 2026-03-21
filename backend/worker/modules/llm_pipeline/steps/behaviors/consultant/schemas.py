from typing import Literal, Annotated, Union

from pydantic import BaseModel, Field


class ToolCallOutput(BaseModel):
    is_final: Literal[False] = False
    tool_name: Literal["search_gkg", "get_gkg_node_detail", "search_raw_sources"]
    tool_args: dict
    reasoning: str


class FinalAnswerOutput(BaseModel):
    is_final: Literal[True] = True
    answer: str
    source_refs: list[str] = Field(default_factory=list)


ConsultantLLMOutput = Annotated[
    Union[ToolCallOutput, FinalAnswerOutput],
    Field(discriminator="is_final"),
]


class ConsultantResponse(BaseModel):
    answer: str
    used_tool_calls: int
    source_refs: list[str]
    was_truncated: bool = False
