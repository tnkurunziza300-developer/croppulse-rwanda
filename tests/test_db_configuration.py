from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from backend import api, db
from backend.runtime_config import _cookie_secure, _cookie_samesite, validate_runtime_config


@pytest.mark.parametrize(
    ("environment", "secure_setting", "expected_secure", "expected_samesite"),
    [
        ("development", None, False, "lax"),
        ("development", "0", False, "lax"),
        ("staging", None, True, "none"),
        ("production", "0", True, "none"),
    ],
)
def test_cookie_samesite_never_uses_none_without_secure(
    monkeypatch, environment, secure_setting, expected_secure, expected_samesite
):
    monkeypatch.setenv("CROP_PULSE_ENVIRONMENT", environment)
    if secure_setting is None:
        monkeypatch.delenv("CROP_PULSE_COOKIE_SECURE", raising=False)
    else:
        monkeypatch.setenv("CROP_PULSE_COOKIE_SECURE", secure_setting)

    assert _cookie_secure() is expected_secure
    assert _cookie_samesite() == expected_samesite


@pytest.mark.parametrize("environment", ["development", "staging", "production"])
def test_runtime_requires_explicit_postgresql_url(monkeypatch, environment):
    monkeypatch.setenv("CROP_PULSE_ENVIRONMENT", environment)
    monkeypatch.delenv("CROP_PULSE_DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="CROP_PULSE_DATABASE_URL"):
        db.database_url()


@pytest.mark.parametrize("environment", ["development", "staging", "production"])
def test_application_runtime_rejects_sqlite_without_opening_it(monkeypatch, environment):
    monkeypatch.setenv("CROP_PULSE_ENVIRONMENT", environment)
    monkeypatch.setenv("CROP_PULSE_DATABASE_URL", "sqlite:///./must-not-open.sqlite3")
    monkeypatch.setenv("CROP_PULSE_ALLOW_SQLITE_TEST_DATABASE", "1")

    with pytest.raises(RuntimeError, match="SQLite is disabled"):
        db.get_engine()


def test_only_explicit_isolated_test_runtime_can_use_sqlite(tmp_path, monkeypatch):
    database = tmp_path / "synthetic-only.sqlite3"
    monkeypatch.setenv("CROP_PULSE_ENVIRONMENT", "test")
    monkeypatch.setenv("CROP_PULSE_DATABASE_URL", f"sqlite:///{database.as_posix()}")
    monkeypatch.delenv("CROP_PULSE_ALLOW_SQLITE_TEST_DATABASE", raising=False)
    with pytest.raises(RuntimeError, match="SQLite is disabled"):
        db.get_engine()

    monkeypatch.setenv("CROP_PULSE_ALLOW_SQLITE_TEST_DATABASE", "1")
    engine = db.get_engine()
    try:
        assert engine.dialect.name == "sqlite"
        assert not database.exists()
    finally:
        engine.dispose()
        db._engine.cache_clear()


def test_test_sqlite_cannot_point_at_historical_data_directory(monkeypatch):
    root = Path(__file__).resolve().parent.parent
    historical = root / "data" / "croppulse_phase1.sqlite3"
    monkeypatch.setenv("CROP_PULSE_ENVIRONMENT", "test")
    monkeypatch.setenv("CROP_PULSE_ALLOW_SQLITE_TEST_DATABASE", "1")
    monkeypatch.setenv("CROP_PULSE_DATABASE_URL", f"sqlite:///{historical.as_posix()}")

    with pytest.raises(RuntimeError, match="historical data directory"):
        db.database_url()


@pytest.mark.parametrize("environment", ["development", "staging", "production"])
def test_runtime_url_rejects_non_postgresql_backend(monkeypatch, environment):
    monkeypatch.setenv("CROP_PULSE_ENVIRONMENT", environment)
    monkeypatch.setenv("CROP_PULSE_DATABASE_URL", "mysql://synthetic-user:synthetic-password@localhost/synthetic_db")

    with pytest.raises(RuntimeError, match="must use PostgreSQL"):
        db.database_url()


def test_staging_runtime_validation_requires_database_before_startup(monkeypatch):
    monkeypatch.setenv("CROP_PULSE_ENVIRONMENT", "staging")
    monkeypatch.setenv("CROP_PULSE_SECRET_KEY", "synthetic-staging-signing-secret-48391")
    monkeypatch.setenv("CROP_PULSE_CORS_ORIGINS", "https://staging.example.test")
    monkeypatch.setenv("CROP_PULSE_COOKIE_SECURE", "1")
    monkeypatch.setenv("CROP_PULSE_AUTO_CREATE_SCHEMA", "0")
    monkeypatch.delenv("CROP_PULSE_DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="CROP_PULSE_DATABASE_URL"):
        validate_runtime_config()


def test_development_runtime_validation_also_requires_postgresql(monkeypatch):
    monkeypatch.setenv("CROP_PULSE_ENVIRONMENT", "development")
    monkeypatch.setenv("CROP_PULSE_SECRET_KEY", "synthetic-development-signing-secret-738291")
    monkeypatch.delenv("CROP_PULSE_DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="CROP_PULSE_DATABASE_URL"):
        validate_runtime_config()


def test_development_runtime_requires_reviewed_migrations_not_auto_create(monkeypatch):
    monkeypatch.setenv("CROP_PULSE_ENVIRONMENT", "development")
    monkeypatch.setenv("CROP_PULSE_SECRET_KEY", "synthetic-development-signing-secret-738291")
    monkeypatch.setenv(
        "CROP_PULSE_DATABASE_URL",
        "postgresql+psycopg://synthetic-user:synthetic-password@localhost:5432/synthetic_db",
    )
    monkeypatch.setenv("CROP_PULSE_AUTO_CREATE_SCHEMA", "1")

    with pytest.raises(RuntimeError, match="reviewed Alembic migrations"):
        validate_runtime_config()


def test_deployment_accepts_postgresql_driver_url_without_connecting(monkeypatch):
    url = "postgresql+psycopg://synthetic-user:synthetic-password@localhost:5432/synthetic_db"
    monkeypatch.setenv("CROP_PULSE_ENVIRONMENT", "staging")
    monkeypatch.setenv("CROP_PULSE_DATABASE_URL", url)

    assert db.database_url() == url
    engine = db.get_engine()
    try:
        assert engine.dialect.name == "postgresql"
        assert db.get_engine() is engine
    finally:
        engine.dispose()
        db._engine.cache_clear()


def test_standard_postgresql_url_selects_installed_psycopg3_driver(monkeypatch):
    monkeypatch.setenv("CROP_PULSE_ENVIRONMENT", "staging")
    monkeypatch.setenv(
        "CROP_PULSE_DATABASE_URL",
        "postgresql://synthetic-user:synthetic-password@localhost:5432/synthetic_db",
    )

    assert db.database_url().startswith("postgresql+psycopg://")


def test_api_startup_fails_when_postgresql_cannot_be_reached(monkeypatch):
    monkeypatch.setenv("CROP_PULSE_ENVIRONMENT", "development")
    monkeypatch.setenv("CROP_PULSE_SECRET_KEY", "synthetic-development-signing-secret-738291")
    monkeypatch.setenv(
        "CROP_PULSE_DATABASE_URL",
        "postgresql+psycopg://synthetic-user:synthetic-password@localhost:5432/synthetic_db",
    )
    monkeypatch.setenv("CROP_PULSE_AUTO_CREATE_SCHEMA", "0")

    class UnavailableEngine:
        def connect(self):
            raise SQLAlchemyError("synthetic connection failure")

    monkeypatch.setattr(api, "get_engine", lambda: UnavailableEngine())
    with pytest.raises(SQLAlchemyError):
        with TestClient(api.app):
            pytest.fail("API startup should not complete without database connectivity")


@pytest.mark.parametrize(
    ("configured_url", "expected_error"),
    [
        (None, "CROP_PULSE_DATABASE_URL"),
        ("not-a-valid-database-url", "invalid"),
        ("sqlite:///./must-not-open-operationally.sqlite3", "SQLite is disabled"),
    ],
)
def test_operational_api_startup_fails_closed_for_missing_or_invalid_database(
    tmp_path, monkeypatch, configured_url, expected_error
):
    monkeypatch.setenv("CROP_PULSE_ENVIRONMENT", "development")
    monkeypatch.setenv("CROP_PULSE_SECRET_KEY", "synthetic-development-signing-secret-738291")
    monkeypatch.setenv("CROP_PULSE_AUTO_CREATE_SCHEMA", "0")
    monkeypatch.setenv("CROP_PULSE_ALLOW_SQLITE_TEST_DATABASE", "1")
    sqlite_path = tmp_path / "must-not-open-operationally.sqlite3"
    if configured_url is None:
        monkeypatch.delenv("CROP_PULSE_DATABASE_URL", raising=False)
    elif configured_url.startswith("sqlite:"):
        monkeypatch.setenv("CROP_PULSE_DATABASE_URL", f"sqlite:///{sqlite_path.as_posix()}")
    else:
        monkeypatch.setenv("CROP_PULSE_DATABASE_URL", configured_url)

    with pytest.raises(RuntimeError, match=expected_error):
        with TestClient(api.app):
            pytest.fail("API startup must reject missing or invalid operational database configuration")

    assert not sqlite_path.exists()
