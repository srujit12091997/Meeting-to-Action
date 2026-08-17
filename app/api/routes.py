"""REST API surface. The Streamlit UI (and later Next.js) call these.

Flow enforced here mirrors the safety principle:
  /extract   -> run LLM pipeline, return items for review (NO external write)
  /confirm   -> human-approved items get pushed to Notion + saved to DB
  /followups -> return drafted nudges for stale tasks (NO auto-send)
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel

from app.agents.extraction import ExtractionError
from app.db.database import SessionLocal
from app.db.models import Meeting, Task
from app.graph.build import pipeline
from app.integrations.notion import push_confirmed_items
from app.scheduler.followup import check_stale_tasks
from app.schemas.models import ActionItem, MeetingExtraction

router = APIRouter()


def _persist_confirmed(
    items: list[ActionItem], page_ids: list[str], meeting_label: str
) -> None:
    """Save confirmed tasks locally so the follow-up checker can reason about them.

    Without this, tasks would live only in Notion and the stale-task check
    (which reads the local DB) would never see them.
    """
    with SessionLocal() as db:
        meeting = None
        if meeting_label:
            meeting = Meeting(title=meeting_label)
            db.add(meeting)
            db.flush()
        for item, page_id in zip(items, page_ids):
            db.add(
                Task(
                    meeting_id=meeting.id if meeting else None,
                    description=item.task,
                    owner=item.owner,
                    owner_status=item.owner_status.value,
                    deadline=item.deadline,
                    source_quote=item.source_quote,
                    notion_page_id=page_id,
                )
            )
        db.commit()


class ExtractRequest(BaseModel):
    transcript: str
    meeting_title: str | None = None
    meeting_date: str | None = None
    known_owners: list[str] = []


class ExtractResponse(BaseModel):
    extraction: MeetingExtraction
    needs_review: bool


@router.post("/extract", response_model=ExtractResponse)
def extract(req: ExtractRequest) -> ExtractResponse:
    try:
        result = pipeline.invoke(
            {
                "transcript": req.transcript,
                "meeting_title": req.meeting_title,
                "meeting_date": req.meeting_date,
                "known_owners": req.known_owners,
            }
        )
    except ExtractionError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    return ExtractResponse(
        extraction=result["extraction"],
        needs_review=result.get("needs_review", False),
    )


class ConfirmRequest(BaseModel):
    items: list[ActionItem]
    meeting_label: str = ""


@router.post("/confirm")
def confirm(req: ConfirmRequest) -> dict:
    """Push human-confirmed items to Notion, then persist them locally."""
    page_ids = push_confirmed_items(req.items, req.meeting_label)
    _persist_confirmed(req.items, page_ids, req.meeting_label)
    return {"pushed": len(page_ids), "notion_page_ids": page_ids}


@router.post("/transcribe")
async def transcribe(audio: UploadFile) -> dict:
    """Voice input: accept a recorded/uploaded audio file, return its transcript.

    The transcript then feeds the normal /extract flow — voice and text share
    the exact same pipeline downstream.
    """
    from app.stt.transcriber import transcribe_bytes

    text = transcribe_bytes(await audio.read())
    return {"transcript": text}


class AskRequest(BaseModel):
    transcript: str
    question: str


class AskResponse(BaseModel):
    answer: str


@router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    """Answer a question grounded in the meeting transcript."""
    from app.agents.qa import answer_question

    return AskResponse(answer=answer_question(req.transcript, req.question))


@router.get("/history")
def history() -> dict:
    """Past confirmed tasks (most recent first) for the History view."""
    with SessionLocal() as db:
        rows = db.query(Task).order_by(Task.created_at.desc()).all()
        tasks = [
            {
                "id": t.id,
                "task": t.description,
                "owner": t.owner,
                "owner_status": t.owner_status,
                "deadline": t.deadline.isoformat() if t.deadline else None,
                "status": t.status,
                "meeting": t.meeting.title if t.meeting else None,
                "created_at": t.created_at.isoformat(),
            }
            for t in rows
        ]
    return {"tasks": tasks}


class EmailRequest(BaseModel):
    recipients: list[str]
    subject: str
    html: str


@router.post("/email-summary")
def email_summary(req: EmailRequest) -> dict:
    """Email the meeting summary to recipients via SMTP."""
    from app.integrations.email import EmailNotConfigured, send_summary_email

    try:
        sent = send_summary_email(req.recipients, req.subject, req.html)
    except EmailNotConfigured as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # SMTP auth/connection errors -> clean message
        raise HTTPException(status_code=502, detail=f"Email send failed: {e}") from e
    return {"sent": sent}


class CalendarRequest(BaseModel):
    action_items: list[dict] = []
    meeting_title: str | None = None


@router.post("/calendar-ics")
def calendar_ics(req: CalendarRequest) -> dict:
    """Build an .ics calendar file (events + reminders) from action items."""
    from app.integrations.calendar import build_ics

    ics, events = build_ics(req.action_items, req.meeting_title)
    return {"ics": ics, "events": events}


@router.get("/followups")
def followups() -> dict:
    """Drafted nudges for stale tasks (human reviews before any send)."""
    return {"drafts": check_stale_tasks()}
