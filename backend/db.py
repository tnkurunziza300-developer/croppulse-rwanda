"""Central PostgreSQL database configuration with an explicit isolated-test SQLite adapter."""
import os
from pathlib import Path
from functools import lru_cache

from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


def database_url() -> str:
    configured = os.environ.get("CROP_PULSE_DATABASE_URL", "").strip()
    environment = os.environ.get("CROP_PULSE_ENVIRONMENT", "development").strip().lower()
    if not configured:
        raise RuntimeError("CROP_PULSE_DATABASE_URL must point to PostgreSQL; no SQLite fallback is configured.")
    try:
        parsed = make_url(configured)
    except Exception:
        raise RuntimeError("CROP_PULSE_DATABASE_URL is invalid; database details are omitted.") from None

    if parsed.get_backend_name() == "sqlite":
        test_sqlite_enabled = (
            environment == "test"
            and os.environ.get("CROP_PULSE_ALLOW_SQLITE_TEST_DATABASE", "").strip() == "1"
        )
        if not test_sqlite_enabled:
            raise RuntimeError("SQLite is disabled for application runtime; isolated tests require explicit test opt-in.")
        if parsed.database not in {None, "", ":memory:"}:
            database_path = Path(parsed.database)
            if not database_path.is_absolute():
                database_path = Path.cwd() / database_path
            historical_data = (Path(__file__).resolve().parent.parent / "data").resolve()
            try:
                database_path.resolve().relative_to(historical_data)
            except ValueError:
                pass
            else:
                raise RuntimeError("SQLite test databases cannot use the historical data directory.")
        return configured

    if parsed.get_backend_name() != "postgresql":
        raise RuntimeError("CROP_PULSE_DATABASE_URL must use PostgreSQL; SQLite and other backends are disabled.")
    if parsed.drivername == "postgresql":
        # requirements.txt installs psycopg 3, not psycopg2.
        parsed = parsed.set(drivername="postgresql+psycopg")
    elif parsed.drivername != "postgresql+psycopg":
        raise RuntimeError("PostgreSQL URLs must use the installed psycopg driver.")
    return parsed.render_as_string(hide_password=False)


@lru_cache(maxsize=4)
def _engine(url: str):
    is_sqlite = make_url(url).get_backend_name() == "sqlite"
    connect_args = {"check_same_thread": False} if is_sqlite else {}
    engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)
    if is_sqlite:
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
