"""Follow-up scheduler job body (offline — no DB, no real time waiting)."""
from datetime import datetime, timedelta

import app.scheduler.followup as followup


class _FakeTask:
    id = 99
    owner = "Raj"
    description = "Update the staging environment"
    created_at = datetime.utcnow() - timedelta(days=6)


def test_run_stale_check_drafts_nudge(monkeypatch):
    monkeypatch.setattr(followup, "find_stale_tasks", lambda: [_FakeTask()])
    drafts = followup.run_stale_check()
    assert len(drafts) == 1
    assert drafts[0]["owner"] == "Raj"
    assert drafts[0]["days_stale"] >= 5
    assert "Raj" in drafts[0]["draft"]  # a real, human-readable nudge


def test_run_stale_check_no_stale_tasks(monkeypatch):
    monkeypatch.setattr(followup, "find_stale_tasks", lambda: [])
    assert followup.run_stale_check() == []
