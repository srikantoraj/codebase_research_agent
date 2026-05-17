from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from apps.agent.nodes.answer_writer import answer_writer_node
from apps.agent.nodes.load_context import load_context_node
from apps.agent.nodes.planner import planner_node
from apps.agent.nodes.researcher import researcher_node
from apps.agent.state import ResearchAgentState


def build_research_graph():
    graph = StateGraph(ResearchAgentState)

    graph.add_node("load_context", load_context_node)
    graph.add_node("plan", planner_node)
    graph.add_node("research", researcher_node)
    graph.add_node("answer", answer_writer_node)

    graph.add_edge(START, "load_context")
    graph.add_edge("load_context", "plan")
    graph.add_edge("plan", "research")
    graph.add_edge("research", "answer")
    graph.add_edge("answer", END)

    return graph.compile()
