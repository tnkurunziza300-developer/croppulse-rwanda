from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def test_agronomy_review_migration_is_additive_and_reversible_on_disposable_sqlite(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parent.parent
    db_path = tmp_path / f"agronomy-review-{uuid4().hex}.sqlite3"
    url = f"sqlite:///{db_path.as_posix()}"
    monkeypatch.setenv("CROP_PULSE_DATABASE_URL", url)
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url)
    engine = create_engine(url)
    try:
        command.upgrade(config, "0019_soil_records")
        now = datetime.now(timezone.utc).isoformat()
        with engine.begin() as connection:
            connection.execute(text("""INSERT INTO farmers
                (id,email,password_hash,display_name,privacy_notice_version,privacy_accepted_at,created_at)
                VALUES ('review-migration-farmer','migration@example.test','hash','Migration','v1',:now,:now)"""),
                {"now": now})
        command.upgrade(config, "head")
        inspector = inspect(engine)
        assert {"agronomy_review_authorization_events", "agronomy_rule_proposals", "agronomy_rule_decisions"} <= set(inspector.get_table_names())
        assert {"farms", "crop_plans", "farm_harvests", "irrigation_records", "soil_observations", "soil_test_records"} <= set(inspector.get_table_names())
        with engine.begin() as connection:
            connection.execute(text("""INSERT INTO agronomy_review_authorization_events
                (id,reviewer_id,actor_id,action,reason,created_at)
                VALUES ('grant-1','review-migration-farmer','review-migration-farmer','grant','Disposable migration test',:now)"""), {"now": now})
            connection.execute(text("""INSERT INTO agronomy_rule_proposals
                (id,rule_id,version,title,category,crop_or_topic,proposed_claim,geographic_scope,season_scope,units,
                 assumptions,limitations,uncertainty,source_references,proposed_by,revision_of_id,created_at)
                VALUES ('proposal-1','fixture.rule','1','Fixture proposal','other','TEST','No guidance.',
                        '{"type":"unknown","scope":["unknown"],"limitations":"test"}', '["A"]', '["none"]',
                        '["test"]', '["test"]', 'test', '[]', 'review-migration-farmer', NULL, :now)"""), {"now": now})
            connection.execute(text("""INSERT INTO agronomy_rule_decisions
                (id,proposal_id,reviewer_id,decision,rationale,created_at)
                VALUES ('decision-1','proposal-1','review-migration-farmer','technical_review','Test-only decision history',:now)"""), {"now": now})
            assert connection.execute(text("SELECT count(*) FROM farmers WHERE id='review-migration-farmer'")).scalar_one() == 1
        command.downgrade(config, "0019_soil_records")
        tables = set(inspect(engine).get_table_names())
        assert not {"agronomy_review_authorization_events", "agronomy_rule_proposals", "agronomy_rule_decisions"} & tables
        assert {"farmers", "farms", "crop_plans", "farm_harvests", "irrigation_records", "soil_observations", "soil_test_records"} <= tables
        with engine.connect() as connection:
            assert connection.execute(text("SELECT id FROM farmers WHERE id='review-migration-farmer'")).scalar_one() == "review-migration-farmer"
    finally:
        engine.dispose()
