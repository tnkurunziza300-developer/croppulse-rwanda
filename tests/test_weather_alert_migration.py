from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def test_weather_alert_migration_preserves_existing_saved_forecasts(monkeypatch):
    root = Path(__file__).resolve().parent.parent
    work = root / ".test-runtime" / "weather-alert-migrations"
    work.mkdir(parents=True, exist_ok=True)
    db_path = work / f"migration-{uuid4().hex}.sqlite3"
    url = f"sqlite:///{db_path.as_posix()}"
    monkeypatch.setenv("CROP_PULSE_DATABASE_URL", url)
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url)
    engine = create_engine(url)
    try:
        command.upgrade(config, "0014_weather_bulletin_records")
        with engine.begin() as connection:
            connection.execute(text("""INSERT INTO farmers
                (id,email,password_hash,display_name,privacy_notice_version,privacy_accepted_at,created_at)
                VALUES ('legacy-farmer','legacy@example.test','hash','Legacy','v1',:now,:now)"""),
                {"now": datetime.now(timezone.utc).isoformat()})
            connection.execute(text("""INSERT INTO saved_weather_forecasts
                (id,farmer_id,latitude,longitude,status,retrieved_at,forecast_json,updated_at)
                VALUES ('legacy-forecast','legacy-farmer',-2.5,29.9,'available',:now,'{}',:now)"""),
                {"now": datetime.now(timezone.utc).isoformat()})
        command.upgrade(config, "head")
        columns = {column["name"] for column in inspect(engine).get_columns("saved_weather_forecasts")}
        assert {"field_id", "location_source", "farm_name_snapshot", "field_name_snapshot"} <= columns
        with engine.connect() as connection:
            saved = connection.execute(text("SELECT field_id, location_source FROM saved_weather_forecasts WHERE id='legacy-forecast'")).one()
            assert saved == (None, "manual")
        tables = set(inspect(engine).get_table_names())
        assert {"weather_alert_preferences", "weather_alerts"} <= tables
        command.downgrade(config, "0014_weather_bulletin_records")
        tables = set(inspect(engine).get_table_names())
        assert "weather_alert_preferences" not in tables and "weather_alerts" not in tables
        with engine.connect() as connection:
            assert "legacy-forecast" in connection.execute(text("SELECT id FROM saved_weather_forecasts")).scalars().all()
    finally:
        engine.dispose()
        for suffix in ("", "-wal", "-shm"):
            candidate = Path(f"{db_path}{suffix}")
            if candidate.exists():
                candidate.unlink()
