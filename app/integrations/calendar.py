"""Calendar integration: turn action items with deadlines into an iCalendar
(.ics) file — importable by Google/Outlook/Apple Calendar, with a reminder.

Stdlib only. Each task with a deadline becomes an all-day event on its due date
with a 1-day-before pop-up reminder (VALARM).
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta


def _esc(text: str) -> str:
    """Escape per RFC 5545 (commas, semicolons, backslashes, newlines)."""
    return (
        text.replace("\\", "\\\\").replace(";", "\\;")
        .replace(",", "\\,").replace("\n", "\\n")
    )


def build_ics(action_items: list[dict], meeting_title: str | None = None) -> tuple[str, int]:
    """Build an .ics document from action items that have deadlines.

    Returns (ics_text, event_count). Tasks without a deadline are skipped.
    """
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    label = meeting_title or "Meeting"
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Meeting-to-Action Agent//EN",
        "CALSCALE:GREGORIAN",
    ]
    count = 0
    for it in action_items:
        deadline = it.get("deadline")
        if not deadline:
            continue
        try:
            due = date.fromisoformat(deadline)
        except (ValueError, TypeError):
            continue
        owner = it.get("owner") or "Unassigned"
        summary = f"{it.get('task', 'Task')} - {owner}"
        lines += [
            "BEGIN:VEVENT",
            f"UID:{uuid.uuid4()}",
            f"DTSTAMP:{stamp}",
            f"DTSTART;VALUE=DATE:{due.strftime('%Y%m%d')}",
            f"DTEND;VALUE=DATE:{(due + timedelta(days=1)).strftime('%Y%m%d')}",
            f"SUMMARY:{_esc(summary)}",
            f"DESCRIPTION:{_esc(f'Action item from: {label}')}",
            "BEGIN:VALARM",
            "TRIGGER:-P1D",
            "ACTION:DISPLAY",
            "DESCRIPTION:Reminder",
            "END:VALARM",
            "END:VEVENT",
        ]
        count += 1
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines), count
