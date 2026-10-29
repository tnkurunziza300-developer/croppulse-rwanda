from pathlib import Path
from uuid import uuid4
from datetime import date, datetime, timedelta, timezone

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from backend.models import Farmer, Farm, FarmHarvest, HarvestObservation, IrrigationRecord, SoilObservation, SoilTestRecord


def test_harvest_migration_is_additive_and_reversible_on_disposable_database(monkeypatch):
    root = Path(__file__).resolve().parent.parent
    work = root / ".test-runtime" / "harvest-migrations"
    work.mkdir(parents=True, exist_ok=True)
    database = (work / f"harvest-migration-{uuid4().hex}.sqlite3").resolve()
    url = f"sqlite:///{database.as_posix()}"
    monkeypatch.setenv("CROP_PULSE_DATABASE_URL", url)
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url)
    engine = create_engine(url)
    try:
        command.upgrade(config, "0015_weather_alert_foundation")
        existing_tables = set(inspect(engine).get_table_names())
        command.upgrade(config, "0017_harvest_observations")
        with Session(engine) as session:
            farmer = Farmer(id="irrigation-migration-farmer", email="migration@example.test",
                            password_hash="synthetic-only", display_name="Synthetic",
                            privacy_notice_version="test", privacy_accepted_at=datetime.now(timezone.utc))
            farm = Farm(id="irrigation-migration-farm", owner=farmer, name="Synthetic farm", district="Huye")
            harvest = FarmHarvest(id="irrigation-migration-harvest", farm=farm, crop="Beans", season="B",
                                  harvest_date=date.today() - timedelta(days=3), harvested_area=0.5,
                                  area_unit="ha", quantity=42, quantity_unit="kg")
            observation = HarvestObservation(id="irrigation-migration-observation", harvest=harvest,
                                             observed_date=date.today() - timedelta(days=2), condition="Synthetic")
            session.add_all([farmer, farm, harvest, observation])
            session.commit()
        command.upgrade(config, "0018_irrigation_records")
        with Session(engine) as session:
            farm = session.get(Farm, "irrigation-migration-farm")
            irrigation = IrrigationRecord(id="migration-irrigation-record", farm=farm,
                                          event_date=date.today(), water_source="unknown")
            session.add(irrigation)
            session.commit()
        command.upgrade(config, "head")
        with Session(engine) as session:
            farm = session.get(Farm, "irrigation-migration-farm")
            soil_observation = SoilObservation(id="migration-soil-observation", farm=farm,
                                               observation_date=date.today(), soil_description="Synthetic observation")
            soil_test = SoilTestRecord(id="migration-soil-test", farm=farm, test_date=date.today(),
                                       ph_value=0, nitrogen_value=0, nitrogen_unit="mg/kg")
            session.add_all([soil_observation, soil_test])
            session.commit()
        with Session(engine) as session:
            preserved_harvest = session.get(FarmHarvest, "irrigation-migration-harvest")
            preserved_observation = session.get(HarvestObservation, "irrigation-migration-observation")
            assert preserved_harvest is not None and preserved_harvest.quantity == 42
            assert preserved_observation is not None and preserved_observation.condition == "Synthetic"
            assert session.get(IrrigationRecord, "migration-irrigation-record").water_source == "unknown"
            assert session.get(SoilObservation, "migration-soil-observation").soil_description == "Synthetic observation"
            assert session.get(SoilTestRecord, "migration-soil-test").ph_value == 0
        inspector = inspect(engine)
        assert "farm_harvests" in inspector.get_table_names()
        assert {"crop", "season", "harvest_date", "harvested_area", "area_unit",
                "quantity", "quantity_unit", "loss_quantity", "created_at", "updated_at"} <= {
            column["name"] for column in inspector.get_columns("farm_harvests")
        }
        assert {fk["referred_table"] for fk in inspector.get_foreign_keys("farm_harvests")} >= {
            "farms", "farm_fields", "crop_plans",
        }
        observation_columns = {column["name"] for column in inspect(engine).get_columns("harvest_observations")}
        assert {"harvest_id", "observed_date", "stored_quantity", "stored_unit", "lost_quantity",
                "lost_unit", "condition", "follow_up", "created_at", "updated_at"} <= observation_columns
        assert "farm_harvests" in {fk["referred_table"] for fk in inspect(engine).get_foreign_keys("harvest_observations")}
        irrigation_columns = {column["name"] for column in inspector.get_columns("irrigation_records")}
        assert {"farm_id", "field_id", "crop_plan_id", "event_date", "water_source",
                "irrigation_method", "water_quantity", "water_quantity_unit", "duration_value",
                "duration_unit", "verification", "created_at", "updated_at"} <= irrigation_columns
        irrigation_fks = {fk["referred_table"] for fk in inspector.get_foreign_keys("irrigation_records")}
        assert {"farms", "farm_fields", "crop_plans"} <= irrigation_fks
        assert {"soil_observations", "soil_test_records"} <= set(inspector.get_table_names())
        soil_observation_columns = {column["name"] for column in inspector.get_columns("soil_observations")}
        assert {"farm_id", "field_id", "observation_date", "soil_description", "drainage_observation",
                "erosion_observation", "management_practices", "verification"} <= soil_observation_columns
        soil_test_columns = {column["name"] for column in inspector.get_columns("soil_test_records")}
        assert {"farm_id", "field_id", "test_date", "ph_value", "nitrogen_value", "nitrogen_unit",
                "phosphorus_value", "phosphorus_unit", "potassium_value", "potassium_unit",
                "organic_matter_value", "organic_matter_unit", "laboratory_name", "report_reference"} <= soil_test_columns
        command.downgrade(config, "0018_irrigation_records")
        assert "soil_observations" not in inspect(engine).get_table_names()
        assert "soil_test_records" not in inspect(engine).get_table_names()
        with Session(engine) as session:
            assert session.get(IrrigationRecord, "migration-irrigation-record") is not None
            assert session.get(FarmHarvest, "irrigation-migration-harvest").quantity == 42
            assert session.get(HarvestObservation, "irrigation-migration-observation").condition == "Synthetic"
        command.downgrade(config, "0017_harvest_observations")
        assert "irrigation_records" not in inspect(engine).get_table_names()
        assert "harvest_observations" in inspect(engine).get_table_names()
        with Session(engine) as session:
            assert session.get(FarmHarvest, "irrigation-migration-harvest").quantity == 42
            assert session.get(HarvestObservation, "irrigation-migration-observation").condition == "Synthetic"
        command.downgrade(config, "0016_farm_harvests")
        assert "harvest_observations" not in inspect(engine).get_table_names()
        assert "farm_harvests" in inspect(engine).get_table_names()
        command.downgrade(config, "0015_weather_alert_foundation")
        assert "farm_harvests" not in inspect(engine).get_table_names()
        assert existing_tables <= set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
        for suffix in ("", "-wal", "-shm"):
            candidate = Path(f"{database}{suffix}")
            if candidate.exists():
                candidate.unlink()
