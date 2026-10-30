from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config

from scripts.staging_preflight import check_target


ROOT = Path(__file__).resolve().parent.parent


def _url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


def test_preflight_accepts_exact_revision_on_disposable_database_without_mutating_it(tmp_path, monkeypatch):
    database = (tmp_path / "staging-preflight.sqlite3").resolve()
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", _url(database))
    monkeypatch.setenv("CROP_PULSE_DATABASE_URL", _url(database))
    command.upgrade(config, "head")
    before = database.stat()

    result = check_target("0020_agronomy_review_workflow", _url(database))

    after = database.stat()
    assert result["preflight_passed"] is True
    assert result["revision"] == "0020_agronomy_review_workflow"
    assert (after.st_size, after.st_mtime_ns) == (before.st_size, before.st_mtime_ns)


def test_preflight_rejects_wrong_revision_without_applying_upgrade(tmp_path, monkeypatch):
    database = (tmp_path / "prior-revision.sqlite3").resolve()
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", _url(database))
    monkeypatch.setenv("CROP_PULSE_DATABASE_URL", _url(database))
    command.upgrade(config, "0019_soil_records")
    before = database.stat()

    result = check_target("0018_irrigation_records", _url(database))
    after = database.stat()

    assert result["preflight_passed"] is False
    assert result["revision"] == "0019_soil_records"
    assert (after.st_size, after.st_mtime_ns) == (before.st_size, before.st_mtime_ns)


def test_preflight_does_not_create_a_missing_sqlite_target(tmp_path):
    database = (tmp_path / "must-not-be-created.sqlite3").resolve()

    result = check_target("0019_soil_records", _url(database))

    assert result["preflight_passed"] is False
    assert not database.exists()


def test_preflight_rejects_unreadable_sqlite_file_without_changing_it(tmp_path):
    database = (tmp_path / f"unreadable-{uuid4().hex}.sqlite3").resolve()
    database.write_bytes(b"not a SQLite database")
    before = database.stat()

    result = check_target("0019_soil_records", _url(database))

    after = database.stat()
    assert result["preflight_passed"] is False
    assert result["connection"] == "failed; details omitted"
    assert result["revision"] == "unknown"
    assert (after.st_size, after.st_mtime_ns) == (before.st_size, before.st_mtime_ns)


def test_preflight_invalid_database_url_fails_closed_without_echoing_it():
    result = check_target("0019_soil_records", "")

    assert result["preflight_passed"] is False
    assert result["connection"] == "failed; details omitted"
    assert result["revision"] == "unknown"
