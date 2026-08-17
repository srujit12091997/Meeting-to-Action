"""The data contract: the structured shape the LLM must produce and the
rest of the pipeline consumes. This is the single source of truth for
"what an extracted meeting looks like."
"""
from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class OwnerStatus(str, Enum):
    RESOLVED = "resolved"        # matched to a known team member
    UNRESOLVED = "unresolved"    # a name was said but we couldn't match it
    AMBIGUOUS = "ambiguous"      # unclear who owns it -> must be human-reviewed
    NONE = "none"                # no owner mentioned at all


class ActionItem(BaseModel):
    """A single committed task extracted from the transcript."""
    task: str = Field(..., description="The concrete action to be done.")
    owner: Optional[str] = Field(
        None, description="Person responsible, or null if unclear."
    )
    owner_status: OwnerStatus = Field(
        OwnerStatus.NONE,
        description="How confident we are about ownership. AMBIGUOUS is flagged, never guessed.",
    )
    deadline: Optional[date] = Field(
        None, description="Due date if stated or clearly implied, else null."
    )
    source_quote: str = Field(
        ..., description="The exact transcript line this was derived from (traceability)."
    )
    confidence: float = Field(
        0.0, ge=0.0, le=1.0, description="Model confidence this is a real action item."
    )


class MeetingExtraction(BaseModel):
    """The full structured output for one meeting."""
    meeting_title: Optional[str] = None
    meeting_date: Optional[date] = None
    summary: str = Field(
        ...,
        description=(
            "A thorough plain-language recap of the WHOLE meeting: what was "
            "discussed, the context, and how it concluded. Several sentences to a "
            "short paragraph — enough that someone who missed it understands it."
        ),
    )
    decisions: list[str] = Field(
        default_factory=list, description="Key decisions actually made in the meeting."
    )
    proposed_solutions: list[str] = Field(
        default_factory=list,
        description=(
            "Solutions, approaches, or ideas proposed to address problems raised — "
            "even if not yet decided on. Each a short phrase."
        ),
    )
    action_items: list[ActionItem] = Field(default_factory=list)
    open_questions: list[str] = Field(
        default_factory=list,
        description="Unresolved threads worth surfacing but not yet tasks.",
    )
