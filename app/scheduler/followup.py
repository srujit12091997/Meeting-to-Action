"""Follow-up checker: find stale tasks and DRAFT nudges (never auto-send in MVP).

Runs on APScheduler locally. In production this same `check_stale_tasks`
function is triggered by a cloud cron job (Railway/Render/Fly.io) instead.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import get_settings
from app.db.database import SessionLocal
from app.db.models import Task
from app.integrations.slack import draft_nudge

logger = logging.getLogger(__name__)


def find_stale_tasks() -> list[Task]:
    """Tasks not Done and untouched longer than the stale threshold."""
    settings = get_settings()
    cutoff = datetime.utcnow() - timedelta(days=settings.stale_after_days)
    with SessionLocal() as db:
        return (
            db.query(Task)
            .filter(Task.status != "Done", Task.created_at < cutoff)
            .all()
        )


def check_stale_tasks() -> list[dict]:
    """Produce drafted nudges for stale tasks. Returns drafts for human review."""
    settings = get_settings()
    drafts: list[dict] = []
    for task in find_stale_tasks():
        days = (datetime.utcnow() - task.created_at).days
        drafts.append(
            {
                "task_id": task.id,
                "owner": task.owner or "team",
                "days_stale": days,
                "draft": draft_nudge(task.owner or "there", task.description, days),
            }
        )
    return drafts


def run_stale_check() -> list[dict]:
    """Scheduled job body: find stale tasks, draft nudges, and log them.

    Safety principle: we DRAFT and log — we never auto-send. A human still
    reviews the drafts (via GET /api/followups) before anything goes out.
    """
    drafts = check_stale_tasks()
    if drafts:
        logger.info("Follow-up check: %d stale task(s) need a nudge.", len(drafts))
        for d in drafts:
            logger.info(
                "  → draft nudge for %s (%d days stale): %s",
                d["owner"], d["days_stale"], d["draft"].splitlines()[0],
            )
    else:
        logger.info("Follow-up check: no stale tasks.")
    return drafts


def start_scheduler(interval_hours: int = 24, run_now: bool = True) -> BackgroundScheduler:
    """Start the recurring stale-task check (logs drafts; never auto-sends).

    ``run_now`` fires one check on startup so the agent is visibly active
    instead of waiting a full interval.
    """
    scheduler = BackgroundScheduler()
    job_kwargs = {"next_run_time": datetime.now()} if run_now else {}
    scheduler.add_job(
        run_stale_check, "interval", hours=interval_hours, id="stale_check", **job_kwargs
    )
    scheduler.start()
    logger.info("Follow-up scheduler started (every %dh, run_now=%s).", interval_hours, run_now)
    return scheduler
