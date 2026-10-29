"""Database configuration for SQLite local development and PostgreSQL deployments."""
import os
from functools import lru_cache

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


def database_url() -> str:
    return os.environ.get("CROP_PULSE_DATABASE_URL", "sqlite:///./data/croppulse_phase1.sqlite3")


@lru_cache(maxsize=4)
def _engine(url: str):
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def enable_foreign_keys(dbapi_connection, _):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    return engine


def get_engine():
    return _engine(database_url())


def get_session_factory():
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_db():
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()
