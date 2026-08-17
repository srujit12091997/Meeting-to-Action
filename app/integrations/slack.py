"""Slack integration: draft (and optionally send) follow-up nudges.

Safety principle: by default we DRAFT nudges and return them for human review.
Actual sending is behind an explicit `send=True` flag.
"""
from __future__ import annotations

from slack_sdk import WebClient

from app.config import get_settings


def draft_nudge(owner: str, task: str, days_stale: int) -> str:
    """Compose a friendly nudge message (does not send)."""
    return (
        f"Hi {owner}, quick nudge on a task from a recent meeting:\n"
        f"> {task}\n"
        f"It's been {days_stale} days with no update. Still on track, or should we adjust?"
    )


def send_nudge(channel: str, text: str) -> dict:
    """Actually send a message to Slack. Call only after human approval."""
    client = WebClient(token=get_settings().slack_bot_token)
    return client.chat_postMessage(channel=channel, text=text)
