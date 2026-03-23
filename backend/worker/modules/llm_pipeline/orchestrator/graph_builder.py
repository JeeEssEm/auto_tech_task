from langgraph.constants import END
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph

from backend.worker.modules.llm_pipeline.orchestrator.nodes import (
    OrchestratorDeps, make_route_node,
    make_guardian_node, make_consultant_node, make_harvester_node, make_grouping_judge_node, make_persist_gkg_node,
    make_architect_node, make_compose_node, fan_out, make_architect_gate
)
from backend.worker.modules.llm_pipeline.orchestrator.state import OrchestratorState


def build_graph(deps: OrchestratorDeps) -> "CompiledStateGraph":
    """
    Фабрика графа. Принимает зависимости → возвращает скомпилированный граф.

    Вызывается один раз при старте приложения.
    Скомпилированный граф thread-safe и переиспользуется для всех запросов.
    """
    builder = StateGraph(OrchestratorState)

    # ------------------------------------------------------------------ #
    #  Регистрация узлов                                                  #
    # ------------------------------------------------------------------ #
    builder.add_node("route_node", make_route_node(deps))
    builder.add_node("guardian_node", make_guardian_node(deps))
    builder.add_node("consultant_node", make_consultant_node(deps))
    builder.add_node("harvester_node", make_harvester_node(deps))
    builder.add_node("grouping_judge_node", make_grouping_judge_node(deps))
    builder.add_node("persist_gkg_node", make_persist_gkg_node(deps))
    builder.add_node("architect_node", make_architect_node(deps))
    builder.add_node("compose_node", make_compose_node(deps))

    # ------------------------------------------------------------------ #
    #  Рёбра                                                              #
    # ------------------------------------------------------------------ #

    builder.set_entry_point("route_node")

    builder.add_conditional_edges(
        "route_node",
        fan_out,
        [
            "guardian_node",
            "consultant_node",
            "harvester_node",
            "compose_node"
        ],
    )

    # harvester → judge → persist → architect_gate (последовательная цепочка)
    builder.add_edge("harvester_node", "grouping_judge_node")
    builder.add_edge("grouping_judge_node", "persist_gkg_node")

    # persist_gkg → architect_gate (conditional: Send() per affected section)
    builder.add_conditional_edges(
        "persist_gkg_node",
        make_architect_gate(deps),
        ["architect_node", "compose_node"],
    )

    # Все конечные узлы сходятся в compose
    builder.add_edge("guardian_node", "compose_node")
    builder.add_edge("consultant_node", "compose_node")
    builder.add_edge("architect_node", "compose_node")

    builder.add_edge("compose_node", END)

    return builder.compile()
