"""Database models: meeting + task history.

Kept intentionally lean for the MVP — enough to store what we extracted and
track what we pushed, so the follow-up checker has something to reason about.
"""
from __future__ import annotations

from datetime import datetime, date

from sqlalchemy import DateTime, Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str | None] = mapped_column(String(255))
    meeting_date: Mapped[date | None] = mapped_column(Date)
    summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    tasks: Mapped[list["Task"]] = relationship(back_populates="meeting")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int | None] = mapped_column(ForeignKey("meetings.id"))
    description: Mapped[str] = mapped_column(Text)
    owner: Mapped[str | None] = mapped_column(String(255))
    owner_status: Mapped[str] = mapped_column(String(32), default="none")
    deadline: Mapped[date | None] = mapped_column(Date)
    source_quote: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="Not started")
    notion_page_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_nudged_at: Mapped[datetime | None] = mapped_column(DateTime)

    meeting: Mapped["Meeting"] = relationship(back_populates="tasks")
