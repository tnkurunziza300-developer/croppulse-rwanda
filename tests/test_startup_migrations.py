"""Startup applies Alembic migrations so a fresh deployment database is usable."""
import asyncio

import pytest

import backend.api as api_module


def _fail_if_called():
    pytest.fail("alembic must not be started for this configuration")


def test_startup_migrations_run_by_default(monkeypatch):
    calls = []
    monkeypatch.setattr(api_module, "_run_alembic_upgrade", lambda: (calls.append(1) or (0, "", "")))
    monkeypatch.setenv("CROP_PULSE_ENVIRONMENT", "production")
    monkeypatch.delenv("CROP_PULSE_RUN_MIGRATIONS_ON_START", raising=False)
    api_module._apply_startup_migrations()
    assert len(calls) == 1


def test_startup_migrations_are_skipped_for_tests(monkeypatch):
    monkeypatch.setattr(api_module, "_run_alembic_upgrade", _fail_if_called)
    monkeypatch.setenv("CROP_PULSE_ENVIRONMENT", "test")
    monkeypatch.delenv("CROP_PULSE_RUN_MIGRATIONS_ON_START", raising=False)
    api_module._apply_startup_migrations()


@pytest.mark.parametrize("disabled_value", ["0", "false", "no", "off", "False", "NO"])
def test_startup_migrations_can_be_disabled(monkeypatch, disabled_value):
    monkeypatch.setattr(api_module, "_run_alembic_upgrade", _fail_if_called)
    monkeypatch.setenv("CROP_PULSE_ENVIRONMENT", "production")
    monkeypatch.setenv("CROP_PULSE_RUN_MIGRATIONS_ON_START", disabled_value)
    api_module._apply_startup_migrations()


def test_startup_migration_failure_fails_startup(monkeypatch):
    monkeypatch.setenv(
        "CROP_PULSE_DATABASE_URL",
        "postgresql+psycopg://crop:super-secret-password@db.example.test:5432/crop",
    )
    monkeypatch.setattr(
        api_module, "_run_alembic_upgrade",
        lambda: (1, "", 'connection to postgresql+psycopg://crop:super-secret-password@db.example.test:5432/crop '
                        'failed: relation "farmers" does not exist'),
    )
    monkeypatch.setenv("CROP_PULSE_ENVIRONMENT", "production")
    monkeypatch.delenv("CROP_PULSE_RUN_MIGRATIONS_ON_START", raising=False)
    with pytest.raises(RuntimeError) as excinfo:
        api_module._apply_startup_migrations()
    message = str(excinfo.value)
    assert "could not apply its database migrations" in message
    assert 'relation "farmers" does not exist' in message
    assert "super-secret-password" not in message
    assert "db.example.test" not in message


def test_migration_output_redacts_database_credentials(monkeypatch):
    monkeypatch.setenv(
        "CROP_PULSE_DATABASE_URL",
        "postgresql+psycopg://crop:super-secret-password@db.example.test:5432/crop",
    )
    redacted = api_module._redact_database_details(
        "connection to postgresql+psycopg://crop:super-secret-password@db.example.test:5432/crop failed"
        " for user crop with password super-secret-password"
    )
    assert "super-secret-password" not in redacted
    assert "db.example.test" not in redacted
    assert "<database url>" in redacted


def test_lifespan_applies_startup_migrations(monkeypatch):
    applied = []
    monkeypatch.setattr(api_module, "validate_runtime_config", lambda: None)
    monkeypatch.setattr(api_module, "_temporary_database_diagnostic", lambda: None)
    monkeypatch.setattr(api_module, "_apply_startup_migrations", lambda: applied.append(True))
    monkeypatch.delenv("CROP_PULSE_AUTO_CREATE_SCHEMA", raising=False)

    async def start_api():
        async with api_module.lifespan(api_module.app):
            return "started"

    assert asyncio.run(start_api()) == "started"
    assert applied == [True]
