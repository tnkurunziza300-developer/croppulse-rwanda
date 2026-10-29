from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config

from backend.diagnostics import inspect_database


ROOT = Path(__file__).resolve().parent.parent


def _sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


def test_missing_sqlite_target_is_not_created_and_connection_is_not_attempted(tmp_path):
    missing = tmp_path / f"missing-{uuid4().hex}.sqlite3"

    result = inspect_database(_sqlite_url(missing))

    assert result["backend"] == "sqlite"
    assert result["exists"] is False
    assert result["connection"].startswith("not checked")
    assert not missing.exists()


def test_relative_sqlite_target_resolves_from_current_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    expected = (tmp_path / "data" / "relative.sqlite3").resolve()

    result = inspect_database("sqlite:///./data/relative.sqlite3")

    assert result["path"] == str(expected)
    assert result["exists"] is False
    assert not expected.exists()


def test_sqlite_diagnostics_are_read_only_and_report_migration_head(tmp_path, monkeypatch):
    database = (tmp_path / f"diagnostic-{uuid4().hex}.sqlite3").resolve()
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", _sqlite_url(database))
    monkeypatch.setenv("CROP_PULSE_DATABASE_URL", _sqlite_url(database))
    command.upgrade(config, "head")
    before = database.stat()

    result = inspect_database(_sqlite_url(database))

    after = database.stat()
    assert result["backend"] == "sqlite"
    assert result["path"] == str(database)
    assert result["connection"] == "ok"
    assert result["revision"] == "0020_agronomy_review_workflow"
    assert result["revision_matches_source"] is True
    assert result["integrity"] == "ok"
    assert result["foreign_key_violations"] == 0
    assert (after.st_size, after.st_mtime_ns) == (before.st_size, before.st_mtime_ns)
