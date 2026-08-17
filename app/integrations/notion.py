"""Notion integration: push confirmed action items into the Tasks database.

Property names here MUST match the columns in your database:
Task (title), Owner (text), Due Date (date), Status (status),
Source Quote (text), Meeting (text).
"""
from __future__ import annotations

from notion_client import Client

from app.config import get_settings
from app.schemas.models import ActionItem


# Pin the API version this code was written against. notion-client 3.x defaults
# to 2025-09-03, which replaces "databases" with "data_sources" and breaks the
# database_id parent / databases.query calls below.
NOTION_API_VERSION = "2022-06-28"


def _client() -> Client:
    return Client(auth=get_settings().notion_api_key, notion_version=NOTION_API_VERSION)


def push_action_item(item: ActionItem, meeting_label: str = "") -> str:
    """Create one task in the Notion database. Returns the new page id."""
    settings = get_settings()
    props: dict = {
        "Task": {"title": [{"text": {"content": item.task}}]},
        "Status": {"status": {"name": "Not started"}},
        "Source Quote": {
            "rich_text": [{"text": {"content": item.source_quote[:2000]}}]
        },
        "Meeting": {"rich_text": [{"text": {"content": meeting_label}}]},
    }
    if item.owner:
        props["Owner"] = {"rich_text": [{"text": {"content": item.owner}}]}
    if item.deadline:
        props["Due Date"] = {"date": {"start": item.deadline.isoformat()}}

    page = _client().pages.create(
        parent={"database_id": settings.notion_database_id},
        properties=props,
    )
    return page["id"]


def push_confirmed_items(items: list[ActionItem], meeting_label: str = "") -> list[str]:
    """Push a batch of human-confirmed items. Returns created page ids."""
    return [push_action_item(i, meeting_label) for i in items]


def list_open_tasks() -> list[dict]:
    """Fetch tasks that aren't Done — used by the follow-up checker."""
    settings = get_settings()
    resp = _client().databases.query(
        database_id=settings.notion_database_id,
        filter={"property": "Status", "status": {"does_not_equal": "Done"}},
    )
    return resp.get("results", [])
