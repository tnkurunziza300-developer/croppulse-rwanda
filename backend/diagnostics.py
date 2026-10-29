"""Read-only runtime/database diagnostics for the current command invocation.

This module deliberately does not import the FastAPI application or SQLAlchemy
models. It never creates a missing SQLite database and never runs migrations.
It cannot inspect another process's environment or prove which database a
separately running API has opened.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

from backend.db import database_url


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def migration_heads() -> list[str]:
    """Return source migration heads without connecting to a database."""
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "backend" / "migrations"))
    return sorted(ScriptDirectory.from_config(config).get_heads())


def _sqlite_path(url: Any) -> Path:
    database = url.database
    if not database or database == ":memory:":
        raise ValueError("A file-backed SQLite database is required for identity checks.")
    path = Path(database)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve(strict=False)


def _inspect_sqlite(url: Any, heads: list[str]) -> dict[str, Any]:
    path = _sqlite_path(url)
    result: dict[str, Any] = {
        "backend": "sqlite",
        "path": str(path),
        "exists": path.is_file(),
        "connection": "not checked",
        "revision": "unknown",
        "revision_check": "not checked",
        "expected_heads": heads,
        "revision_matches_source": False,
        "integrity": "not checked",
        "foreign_key_violations": "not checked",
    }
    if not result["exists"]:
        result["connection"] = "not checked; file does not exist (no file created)"
        return result

    # A read-only SQLite open can still need WAL/SHM sidecars. Fail closed if
    # they exist, so a diagnostic cannot create or alter sidecar state.
    if Path(f"{path}-wal").exists() or Path(f"{path}-shm").exists():
        result["connection"] = "not checked; SQLite sidecar files exist"
        return result

    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=2)
        connection.execute("PRAGMA query_only=ON")
        connection.execute("SELECT 1").fetchone()
        result["connection"] = "ok"
        result["integrity"] = connection.execute("PRAGMA integrity_check").fetchone()[0]
        result["foreign_key_violations"] = sum(
            1 for _ in connection.execute("PRAGMA foreign_key_check")
        )
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        if "alembic_version" in tables:
            rows = [row[0] for row in connection.execute(
                "SELECT version_num FROM alembic_version"
            )]
            result["revision"] = ",".join(sorted(rows)) if rows else "empty"
        else:
            result["revision"] = "not present"
        result["revision_matches_source"] = sorted(
            result["revision"].split(",")
        ) == heads
        result["revision_check"] = "ok" if result["revision"] != "not present" else "revision table missing"
    except (OSError, sqlite3.Error):
        # Driver messages may contain file paths or SQL. Keep diagnostics safe.
        result["connection"] = "failed; details omitted"
    finally:
        if connection is not None:
            connection.close()
    return result


def _inspect_server_database(url: Any, heads: list[str]) -> dict[str, Any]:
    """Perform read-only checks for PostgreSQL without rendering its URL."""
    from sqlalchemy import create_engine, text

    safe_identity = url.set(username=None, password=None, query={}).render_as_string(
        hide_password=True
    )
    identity = hashlib.sha256(safe_identity.encode("utf-8")).hexdigest()[:16]
    result: dict[str, Any] = {
        "backend": url.get_backend_name(),
        "identity_fingerprint": identity,
        "connection": "not checked",
        "revision": "unknown",
        "revision_check": "not checked",
        "expected_heads": heads,
        "revision_matches_source": False,
        "integrity": "not applicable",
        "foreign_key_violations": "not applicable",
    }
    engine = None
    try:
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as connection:
            with connection.begin():
                if url.get_backend_name() == "postgresql":
                    connection.execute(text("SET TRANSACTION READ ONLY"))
                connection.execute(text("SELECT 1")).scalar_one()
                result["connection"] = "ok"
                try:
                    revision = connection.execute(
                        text("SELECT version_num FROM alembic_version")
                    ).scalars().all()
                    result["revision"] = ",".join(sorted(revision)) if revision else "empty"
                    result["revision_matches_source"] = sorted(
                        result["revision"].split(",")
                    ) == heads
                    result["revision_check"] = "ok"
                except SQLAlchemyError:
                    result["revision"] = "unavailable"
                    result["revision_check"] = "failed; details omitted"
    except Exception:
        result["connection"] = "failed; details omitted"
    finally:
        if engine is not None:
            engine.dispose()
    return result


def inspect_database(configured_url: str | None = None) -> dict[str, Any]:
    """Inspect an explicitly supplied or current-invocation URL read-only."""
    raw_url = configured_url if configured_url is not None else database_url()
    url = make_url(raw_url)
    heads = migration_heads()
    if url.get_backend_name() == "sqlite":
        return _inspect_sqlite(url, heads)
    if url.get_backend_name() == "postgresql":
        return _inspect_server_database(url, heads)
    return {
        "backend": url.get_backend_name(),
        "connection": "not checked; backend is not supported by this diagnostic",
        "revision": "unknown",
        "revision_check": "not checked",
        "expected_heads": heads,
        "revision_matches_source": False,
        "integrity": "not checked",
        "foreign_key_violations": "not checked",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only diagnostics for this command's configured CropPulse database."
    )
    parser.parse_args()
    print("Scope: current command invocation; this does not inspect a running API process.")
    print(f"Python executable: {sys.executable}")
    print(f"Working directory: {Path.cwd()}")
    print(f"API source entry point (repository): {PROJECT_ROOT / 'backend' / 'api.py'}")
    environment = os.environ.get("CROP_PULSE_ENVIRONMENT", "unset").strip().lower()
    if environment not in {"development", "test", "staging", "production", "prod"}:
        environment = "unset or unrecognized"
    print(f"Runtime environment: {environment}")
    try:
        result = inspect_database()
    except Exception:
        print("Database configuration: invalid or unavailable; details omitted")
        return 2
    for key, value in result.items():
        print(f"{key}: {value}")
    if result["connection"] != "ok":
        return 2
    if not result["revision_matches_source"]:
        return 3
    if result["integrity"] not in {"ok", "not applicable"}:
        return 4
    if result["foreign_key_violations"] not in {0, "not applicable"}:
        return 5
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
