"""SQLAlchemy engine/session setup.

The only thing that changes for the production swap (SQLite -> Supabase Postgres)
is DATABASE_URL in .env. Everything else stays the same.
"""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

settings = get_settings()

# check_same_thread is a SQLite-only quirk; harmless to guard on the URL.
connect_args = (
    {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    """Create tables. Called on app startup for the MVP."""
    from app.db import models  # noqa: F401  (register models)

    Base.metadata.create_all(bind=engine)
