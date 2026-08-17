"""Email + calendar (.ics) features — offline (no real SMTP, no network)."""
from fastapi.testclient import TestClient

from app.integrations.calendar import build_ics
from app.integrations.email import EmailNotConfigured
from app.main import app

client = TestClient(app)

ITEMS = [
    {"task": "Prepare Q3 budget", "owner": "Sarah", "deadline": "2026-08-21",
     "owner_status": "resolved", "source_quote": "q"},
    {"task": "Brainstorm ideas", "owner": None, "deadline": None,
     "owner_status": "ambiguous", "source_quote": "q"},
]


def test_build_ics_only_dated_tasks():
    ics, count = build_ics(ITEMS, "Weekly Sync")
    assert count == 1                      # only the task with a deadline
    assert "BEGIN:VCALENDAR" in ics and "END:VCALENDAR" in ics
    assert "BEGIN:VALARM" in ics           # reminder attached
    assert "Prepare Q3 budget" in ics
    assert "Brainstorm ideas" not in ics   # no deadline -> skipped


def test_calendar_ics_endpoint():
    resp = client.post("/api/calendar-ics",
                       json={"action_items": ITEMS, "meeting_title": "Weekly Sync"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["events"] == 1
    assert body["ics"].startswith("BEGIN:VCALENDAR")


def test_email_summary_sends(monkeypatch):
    import app.integrations.email as email_mod
    monkeypatch.setattr(email_mod, "send_summary_email", lambda r, s, h: len(r))
    resp = client.post("/api/email-summary",
                       json={"recipients": ["a@x.com", "b@y.com"], "subject": "s", "html": "<p>hi</p>"})
    assert resp.status_code == 200
    assert resp.json() == {"sent": 2}


def test_email_summary_not_configured(monkeypatch):
    import app.integrations.email as email_mod

    def _raise(recipients, subject, html):
        raise EmailNotConfigured("SMTP not configured.")

    monkeypatch.setattr(email_mod, "send_summary_email", _raise)
    resp = client.post("/api/email-summary",
                       json={"recipients": ["a@x.com"], "subject": "s", "html": "<p>x</p>"})
    assert resp.status_code == 400
    assert "SMTP" in resp.json()["detail"]
