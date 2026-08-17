"""Shared state that flows through the LangGraph pipeline."""
from __future__ import annotations

from typing import Optional, TypedDict

from app.schemas.models import MeetingExtraction


class PipelineState(TypedDict, total=False):
    # Inputs
    transcript: str
    meeting_title: Optional[str]
    meeting_date: Optional[str]
    known_owners: list[str]          # roster used for owner resolution

    # Produced by nodes
    extraction: MeetingExtraction    # from the extraction node
    needs_review: bool               # True if any owner is ambiguous/unresolved
    pushed_task_ids: list[str]       # Notion page ids after sync
    errors: list[str]
