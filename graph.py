# graph.py
from langgraph.graph import StateGraph, END
from state import AgentState
from agents import (
    profile_extractor_node, router_node,
    profiler_node, rag_retriever_node, chitchat_node,
    response_generator_node, output_formatter_node, state_updater_node
)

def build_graph():
    graph = StateGraph(AgentState)
    
    # Add all nodes
    graph.add_node("profile_extractor", profile_extractor_node)
    graph.add_node("router",            router_node)
    graph.add_node("profiler",          profiler_node)
    graph.add_node("rag_retriever",     rag_retriever_node)
    graph.add_node("chitchat",          chitchat_node)
    graph.add_node("response_generator",response_generator_node)
    graph.add_node("output_formatter",  output_formatter_node)
    graph.add_node("state_updater",     state_updater_node)
    
    # Entry point
    graph.set_entry_point("profile_extractor")
    
    # Linear edges
    graph.add_edge("profile_extractor", "router")
    
    # Conditional routing
    graph.add_conditional_edges(
        "router",
        lambda state: state["intent"],  # reads the intent field
        {
            "profiling":     "profiler",
            "product_query": "rag_retriever",
            "chitchat":      "chitchat"
        }
    )
    
    # All branches converge
    graph.add_edge("profiler",      "output_formatter")
    graph.add_edge("rag_retriever", "response_generator")
    graph.add_edge("chitchat",      "response_generator")
    graph.add_edge("response_generator", "output_formatter")
    graph.add_edge("output_formatter",   "state_updater")
    graph.add_edge("state_updater",      END)
    
    return graph.compile()

# Singleton
et_graph = build_graph()