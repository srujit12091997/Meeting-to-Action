"""Assemble the LangGraph pipeline.

MVP graph (the part that runs before human review):

    transcript --> [extract] --> [resolve_owners] --> END
                                                       |
                              (human confirms in the UI, THEN we call task sync)

Task sync and follow-up are intentionally OUTSIDE this graph because they must
only run after explicit human confirmation (safety principle). They're invoked
by the API/UI, not automatically by the graph.
"""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.graph.nodes import extract_node, resolve_owners_node
from app.graph.state import PipelineState


def build_pipeline():
    graph = StateGraph(PipelineState)
    graph.add_node("extract", extract_node)
    graph.add_node("resolve_owners", resolve_owners_node)

    graph.set_entry_point("extract")
    graph.add_edge("extract", "resolve_owners")
    graph.add_edge("resolve_owners", END)

    return graph.compile()


# Module-level singleton so we compile the graph once.
pipeline = build_pipeline()
