"""Individual nodes of the LangGraph pipeline.

Each node is a pure-ish function: takes state, returns a partial state update.
Keeping them small makes the graph easy to test and to trace in Langfuse.
"""
from __future__ import annotations

from app.agents.extraction import extract_meeting
from app.graph.state import PipelineState
from app.schemas.models import OwnerStatus


def extract_node(state: PipelineState) -> PipelineState:
    """Transcript -> structured MeetingExtraction via the configured LLM (Gemini/Claude)."""
    extraction = extract_meeting(
        transcript=state["transcript"],
        meeting_title=state.get("meeting_title"),
        meeting_date=state.get("meeting_date"),
    )
    return {"extraction": extraction}


def resolve_owners_node(state: PipelineState) -> PipelineState:
    """Match owners against the known roster; flag anything unresolved/ambiguous.

    We deliberately do NOT auto-guess owners. If we can't confidently match,
    we mark it for human review (the core safety principle of the project).
    """
    extraction = state["extraction"]
    roster = {n.lower(): n for n in state.get("known_owners", [])}
    needs_review = False

    for item in extraction.action_items:
        if item.owner_status == OwnerStatus.AMBIGUOUS or item.owner is None:
            needs_review = True
            continue
        match = roster.get(item.owner.lower())
        if match:
            item.owner = match
            item.owner_status = OwnerStatus.RESOLVED
        else:
            item.owner_status = OwnerStatus.UNRESOLVED
            needs_review = True

    return {"extraction": extraction, "needs_review": needs_review}
