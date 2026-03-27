from langgraph.graph import END, StateGraph

from .agents import (
    chitchat_node,
    output_formatter_node,
    profile_extractor_node,
    profiler_node,
    rag_retriever_node,
    response_generator_node,
    router_node,
    state_updater_node,
)
from .state import AgentState


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("profile_extractor", profile_extractor_node)
    graph.add_node("router", router_node)
    graph.add_node("profiler", profiler_node)
    graph.add_node("rag_retriever", rag_retriever_node)
    graph.add_node("chitchat", chitchat_node)
    graph.add_node("response_generator", response_generator_node)
    graph.add_node("output_formatter", output_formatter_node)
    graph.add_node("state_updater", state_updater_node)

    graph.set_entry_point("profile_extractor")
    graph.add_edge("profile_extractor", "router")
    graph.add_conditional_edges(
        "router",
        lambda state: state["intent"],
        {
            "profiling": "profiler",
            "product_query": "rag_retriever",
            "chitchat": "chitchat",
        },
    )
    graph.add_edge("profiler", "output_formatter")
    graph.add_edge("rag_retriever", "response_generator")
    graph.add_edge("chitchat", "response_generator")
    graph.add_edge("response_generator", "output_formatter")
    graph.add_edge("output_formatter", "state_updater")
    graph.add_edge("state_updater", END)

    return graph.compile()


et_graph = build_graph()
