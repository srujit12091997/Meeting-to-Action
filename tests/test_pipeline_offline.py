"""End-to-end pipeline test with the LLM mocked out (runs offline, no API key).

Proves the LangGraph wiring (extract -> resolve_owners) works and that
owner review flagging propagates, without spending LLM/API tokens.
"""
from datetime import date

import app.graph.nodes as nodes
from app.graph.build import build_pipeline
from app.schemas.models import ActionItem, MeetingExtraction, OwnerStatus


def test_pipeline_runs_and_flags_review(monkeypatch):
    fake = MeetingExtraction(
        meeting_title="Standup",
        meeting_date=date(2026, 8, 7),
        summary="Discussed the login bug and demo.",
        decisions=["Ship demo Friday regardless of CSV export."],
        action_items=[
            ActionItem(task="Fix OAuth 500", owner="Raj",
                       owner_status=OwnerStatus.RESOLVED, source_quote="I'll dig into it",
                       confidence=0.95),
            ActionItem(task="Own the frontend date filter", owner=None,
                       owner_status=OwnerStatus.AMBIGUOUS,
                       source_quote="not sure who owns the frontend", confidence=0.6),
        ],
    )
    # Patch the LLM call so the extract node returns our fixture.
    monkeypatch.setattr(nodes, "extract_meeting", lambda **kw: fake)

    pipeline = build_pipeline()
    result = pipeline.invoke(
        {"transcript": "irrelevant", "known_owners": ["Raj", "Priya"]}
    )

    ext = result["extraction"]
    assert len(ext.action_items) == 2
    assert ext.action_items[0].owner == "Raj"
    # The ambiguous item must force human review.
    assert result["needs_review"] is True
