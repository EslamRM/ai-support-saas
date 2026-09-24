"""
Module: agent
File responsibility (graph.py): graph definition -- nodes, edges,
conditional routing. This file should read like the flowchart it
implements:

    START -> classify_intent -> (needs_retrieval?)
                                   yes -> retrieve_knowledge -> generate_answer
                                   no  -----------------------> generate_answer
             generate_answer -> quality_check -> END

build_agent_graph() is a FACTORY, not a module-level compiled singleton:
production code calls it with no arguments and gets real Qdrant +
OpenAI-backed nodes; tests inject a fake VectorStore/ChatModel so the
whole graph runs offline and deterministically. Node implementations
live in nodes/, kept out of this file so the control flow stays readable
on its own -- see docs/agent.md.
"""
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.core.ai.vector_store import VectorStore
from app.modules.agent.llm import ChatModel
from app.modules.agent.nodes.classify import classify_intent
from app.modules.agent.nodes.generate import make_generate_answer
from app.modules.agent.nodes.quality_check import quality_check
from app.modules.agent.nodes.retrieve import make_retrieve_knowledge
from app.modules.agent.state import AgentState


def _route_after_classify(state: AgentState) -> str:
    return "retrieve_knowledge" if state.get("needs_retrieval") else "generate_answer"


def build_agent_graph(
    *,
    vector_store: VectorStore | None = None,
    chat_model: ChatModel | None = None,
) -> CompiledStateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("classify_intent", classify_intent)
    graph.add_node("retrieve_knowledge", make_retrieve_knowledge(vector_store))
    graph.add_node("generate_answer", make_generate_answer(chat_model))
    graph.add_node("quality_check", quality_check)

    graph.add_edge(START, "classify_intent")
    graph.add_conditional_edges(
        "classify_intent",
        _route_after_classify,
        {"retrieve_knowledge": "retrieve_knowledge", "generate_answer": "generate_answer"},
    )
    graph.add_edge("retrieve_knowledge", "generate_answer")
    graph.add_edge("generate_answer", "quality_check")
    graph.add_edge("quality_check", END)

    return graph.compile()
