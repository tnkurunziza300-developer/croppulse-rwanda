from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from pathlib import Path
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parent.parent


def test_existing_crop_plans_receive_planned_status_on_upgrade(tmp_path, monkeypatch):
    database = tmp_path / "upgrade.sqlite3"
    database_url = f"sqlite:///{database.as_posix()}"
    monkeypatch.setenv("CROP_PULSE_DATABASE_URL", database_url)
    config = Config(str(ROOT / "alembic.ini"))

    command.upgrade(config, "0003_roles_review_and_admin")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text("""INSERT INTO farmers
            (id,email,password_hash,display_name,privacy_notice_version,privacy_accepted_at,created_at,role,status)
            VALUES ('farmer-1','farmer@example.com','hash','Farmer','v1','2026-01-01','2026-01-01','farmer','active')"""))
        connection.execute(text("""INSERT INTO farms (id,owner_id,name,district,created_at)
            VALUES ('farm-1','farmer-1','Farm','Huye','2026-01-01')"""))
        connection.execute(text("""INSERT INTO crop_plans
            (id,farm_id,district,crop,season,planting_date,area_ha,plan_json,verification,created_at)
            VALUES ('plan-1','farm-1','Huye','Maize','A','2026-02-01',1.0,'{}','provisional','2026-01-01')"""))
    engine.dispose()

    command.upgrade(config, "head")
    engine = create_engine(database_url)
    with engine.connect() as connection:
        row = connection.execute(text("SELECT status, actual_planting_date FROM crop_plans WHERE id='plan-1'")).one()
        assert row.status == "planned" and row.actual_planting_date is None
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == ScriptDirectory.from_config(config).get_current_head()
    engine.dispose()


def test_account_action_migration_preserves_review_decision_when_reviewer_is_deleted(tmp_path, monkeypatch):
    database = tmp_path / "account-actions.sqlite3"
    database_url = f"sqlite:///{database.as_posix()}"
    monkeypatch.setenv("CROP_PULSE_DATABASE_URL", database_url)
    config = Config(str(ROOT / "alembic.ini"))
    command.upgrade(config, "0004_crop_plan_lifecycle")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        for identifier, email in (("owner", "owner@example.com"), ("reviewer", "reviewer@example.com")):
            connection.execute(text("""INSERT INTO farmers
                (id,email,password_hash,display_name,privacy_notice_version,privacy_accepted_at,created_at,role,status)
                VALUES (:id,:email,'hash','Farmer','v1','2026-01-01','2026-01-01','farmer','active')"""),
                {"id": identifier, "email": email})
        connection.execute(text("INSERT INTO farms (id,owner_id,name,district,created_at) VALUES ('farm','owner','Farm','Huye','2026-01-01')"))
        connection.execute(text("""INSERT INTO farm_activities
            (id,farm_id,district,crop,season,activity_type,event_date,notes,verification,created_at,updated_at)
            VALUES ('activity','farm','Huye','Maize','A','Harvest','2026-01-01','','user_reported','2026-01-01','2026-01-01')"""))
        connection.execute(text("""INSERT INTO activity_review_decisions
            (id,activity_id,reviewer_id,decision,reason,created_at)
            VALUES ('decision','activity','reviewer','approved_as_reviewed','Reviewed','2026-01-02')"""))
    engine.dispose()

    command.upgrade(config, "head")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        connection.execute(text("DELETE FROM farmers WHERE id='reviewer'"))
        decision = connection.execute(text("SELECT reviewer_id FROM activity_review_decisions WHERE id='decision'")).scalar_one()
        assert decision is None
        assert connection.execute(text("SELECT count(*) FROM account_action_tokens")).scalar_one() == 0
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == ScriptDirectory.from_config(config).get_current_head()
    engine.dispose()


def test_private_messaging_migration_upgrade_and_downgrade_are_additive(tmp_path, monkeypatch):
    database = tmp_path / "private-messaging.sqlite3"
    database_url = f"sqlite:///{database.as_posix()}"
    monkeypatch.setenv("CROP_PULSE_DATABASE_URL", database_url)
    config = Config(str(ROOT / "alembic.ini"))
    command.upgrade(config, "0005_self_service_account")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text("""INSERT INTO farmers
            (id,email,password_hash,display_name,privacy_notice_version,privacy_accepted_at,created_at,role,status)
            VALUES ('farmer','farmer@example.com','hash','Farmer','v1','2026-01-01','2026-01-01','farmer','active')"""))
    engine.dispose()
    command.upgrade(config, "head")
    engine = create_engine(database_url)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT farmer_reviewer_enabled FROM messaging_settings WHERE id=1")).scalar_one() in (0, False)
        assert connection.execute(text("SELECT email FROM farmers WHERE id='farmer'")).scalar_one() == "farmer@example.com"
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == ScriptDirectory.from_config(config).get_current_head()
    engine.dispose()
    command.downgrade(config, "0005_self_service_account")
    engine = create_engine(database_url)
    with engine.connect() as connection:
        tables = {row[0] for row in connection.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}
        assert "private_messages" not in tables and "private_conversations" not in tables and "messaging_settings" not in tables
        assert connection.execute(text("SELECT email FROM farmers WHERE id='farmer'")).scalar_one() == "farmer@example.com"
    engine.dispose()


def test_field_and_evidence_migration_preserves_plans_and_is_reversible(tmp_path, monkeypatch):
    database = tmp_path / "fields-evidence.sqlite3"
    database_url = f"sqlite:///{database.as_posix()}"
    monkeypatch.setenv("CROP_PULSE_DATABASE_URL", database_url)
    config = Config(str(ROOT / "alembic.ini"))
    command.upgrade(config, "0006_private_messaging")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text("""INSERT INTO farmers
            (id,email,password_hash,display_name,privacy_notice_version,privacy_accepted_at,created_at,role,status)
            VALUES ('owner','owner@example.com','hash','Farmer','v1','2026-01-01','2026-01-01','farmer','active')"""))
        connection.execute(text("INSERT INTO farms (id,owner_id,name,district,created_at) VALUES ('farm','owner','Farm','Huye','2026-01-01')"))
        connection.execute(text("""INSERT INTO crop_plans
            (id,farm_id,district,crop,season,planting_date,area_ha,plan_json,verification,status,created_at)
            VALUES ('plan','farm','Huye','Maize','A','2026-02-01',1.0,'{}','provisional','monitoring','2026-01-01')"""))
    engine.dispose()
    command.upgrade(config, "head")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        plan = connection.execute(text("SELECT field_id,status,plan_json FROM crop_plans WHERE id='plan'")).one()
        assert plan.field_id is None and plan.status == "monitoring" and plan.plan_json == "{}"
        connection.execute(text("""INSERT INTO farm_fields
            (id,farm_id,name,area_ha,latitude,longitude,archived_at,created_at,updated_at)
            VALUES ('field','farm','North plot',NULL,NULL,NULL,NULL,'2026-01-02','2026-01-02')"""))
        connection.execute(text("UPDATE crop_plans SET field_id='field' WHERE id='plan'"))
        assert connection.execute(text("SELECT count(*) FROM crop_plans WHERE field_id='field'")).scalar_one() == 1
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == ScriptDirectory.from_config(config).get_current_head()
    engine.dispose()
    command.downgrade(config, "0006_private_messaging")
    engine = create_engine(database_url)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT email FROM farmers WHERE id='owner'")).scalar_one() == "owner@example.com"
        assert connection.execute(text("SELECT status FROM crop_plans WHERE id='plan'")).scalar_one() == "monitoring"
        tables = {row[0] for row in connection.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}
        assert "farm_fields" not in tables and "crop_plan_evidence" not in tables
    engine.dispose()


def test_crop_health_context_migration_preserves_existing_reports_and_is_reversible(tmp_path, monkeypatch):
    database = tmp_path / "crop-health-context.sqlite3"
    database_url = f"sqlite:///{database.as_posix()}"
    monkeypatch.setenv("CROP_PULSE_DATABASE_URL", database_url)
    config = Config(str(ROOT / "alembic.ini"))
    command.upgrade(config, "0009_crop_health_cases")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text("""INSERT INTO farmers
            (id,email,password_hash,display_name,privacy_notice_version,privacy_accepted_at,created_at,role,status)
            VALUES ('farmer','farmer@example.com','hash','Farmer','v1','2026-01-01','2026-01-01','farmer','active')"""))
        connection.execute(text("INSERT INTO farms (id,owner_id,name,district,created_at) VALUES ('farm','farmer','Farm','Huye','2026-01-01')"))
        connection.execute(text("""INSERT INTO crop_health_cases
            (id,farmer_id,farm_id,crop,symptoms,observed_date,status,diagnosis_status,photo_data,photo_sha256,
             photo_size_bytes,photo_width,photo_height,created_at,updated_at)
            VALUES ('case','farmer','farm','Maize','Yellow patches',NULL,'submitted','unresolved',:photo,'hash',4,32,32,'2026-01-01','2026-01-01')"""),
            {"photo": b"test"})
    engine.dispose()

    command.upgrade(config, "head")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        report = connection.execute(text("SELECT symptoms,plant_parts_affected,spreading,ai_screening_status,ai_screening_json FROM crop_health_cases WHERE id='case'")).one()
        assert report.symptoms == "Yellow patches" and report.plant_parts_affected is None and report.spreading is None
        assert report.ai_screening_status == "not_run" and report.ai_screening_json is None
        connection.execute(text("UPDATE crop_health_cases SET plant_parts_affected='lower leaves',spreading=1 WHERE id='case'"))
        assert connection.execute(text("SELECT spreading FROM crop_health_cases WHERE id='case'")).scalar_one() == 1
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == ScriptDirectory.from_config(config).get_current_head()
    engine.dispose()

    command.downgrade(config, "0009_crop_health_cases")
    engine = create_engine(database_url)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT symptoms FROM crop_health_cases WHERE id='case'")).scalar_one() == "Yellow patches"
        columns = {row[1] for row in connection.execute(text("PRAGMA table_info(crop_health_cases)"))}
        assert "plant_parts_affected" not in columns and "spreading" not in columns
        assert "ai_screening_status" not in columns and "ai_screening_json" not in columns
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0009_crop_health_cases"

