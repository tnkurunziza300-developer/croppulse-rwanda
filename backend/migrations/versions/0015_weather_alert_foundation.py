"""Add field-linked forecasts and opt-in in-app weather alert foundation."""
from alembic import op
import sqlalchemy as sa


revision = "0015_weather_alert_foundation"
down_revision = "0014_weather_bulletin_records"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("saved_weather_forecasts") as batch:
        batch.add_column(sa.Column("field_id", sa.String(length=36), nullable=True))
        batch.add_column(sa.Column("farm_name_snapshot", sa.String(length=120), nullable=True))
        batch.add_column(sa.Column("field_name_snapshot", sa.String(length=120), nullable=True))
        batch.add_column(sa.Column("location_source", sa.String(length=16), server_default="manual", nullable=False))
        batch.create_foreign_key("fk_saved_weather_forecasts_field_id_farm_fields", "farm_fields", ["field_id"], ["id"], ondelete="SET NULL")
        batch.create_check_constraint("ck_saved_weather_forecast_location_source", "location_source IN ('saved_field', 'manual', 'device')")
        batch.create_check_constraint("ck_saved_weather_forecast_field_source", "field_id IS NULL OR location_source = 'saved_field'")
        batch.create_index("ix_saved_weather_forecasts_field_id", ["field_id"])

    op.create_table(
        "weather_alert_preferences",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("farmer_id", sa.String(length=36), sa.ForeignKey("farmers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("field_id", sa.String(length=36), sa.ForeignKey("farm_fields.id", ondelete="CASCADE"), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("farmer_id", "field_id", name="uq_weather_alert_preference_farmer_field"),
    )
    op.create_index("ix_weather_alert_preferences_farmer", "weather_alert_preferences", ["farmer_id"])

    op.create_table(
        "weather_alerts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("recipient_id", sa.String(length=36), sa.ForeignKey("farmers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("farm_id", sa.String(length=36), sa.ForeignKey("farms.id", ondelete="SET NULL"), nullable=True),
        sa.Column("field_id", sa.String(length=36), sa.ForeignKey("farm_fields.id", ondelete="SET NULL"), nullable=True),
        sa.Column("forecast_id", sa.String(length=36), sa.ForeignKey("saved_weather_forecasts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("farm_name_snapshot", sa.String(length=120), nullable=True),
        sa.Column("field_name_snapshot", sa.String(length=120), nullable=True),
        sa.Column("alert_type", sa.String(length=60), nullable=False),
        sa.Column("rule_id", sa.String(length=100), nullable=False),
        sa.Column("rule_version", sa.String(length=40), nullable=False),
        sa.Column("weather_source", sa.String(length=80), nullable=False),
        sa.Column("forecast_retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("evidence_status", sa.String(length=40), nullable=False),
        sa.Column("evidence_snapshot_json", sa.Text(), nullable=False),
        sa.Column("approval_status", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="active", nullable=False),
        sa.Column("dedupe_key", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("dedupe_key", name="uq_weather_alert_dedupe_key"),
        sa.CheckConstraint("status IN ('active', 'acknowledged', 'dismissed')", name="ck_weather_alert_status"),
        sa.CheckConstraint("approval_status IN ('approved', 'inactive')", name="ck_weather_alert_approval_status"),
        sa.CheckConstraint("valid_to >= valid_from", name="ck_weather_alert_valid_period"),
    )
    op.create_index("ix_weather_alerts_recipient_created", "weather_alerts", ["recipient_id", "created_at"])
    op.create_index("ix_weather_alerts_field_period", "weather_alerts", ["field_id", "valid_from", "valid_to"])


def downgrade():
    op.drop_index("ix_weather_alerts_field_period", table_name="weather_alerts")
    op.drop_index("ix_weather_alerts_recipient_created", table_name="weather_alerts")
    op.drop_table("weather_alerts")
    op.drop_index("ix_weather_alert_preferences_farmer", table_name="weather_alert_preferences")
    op.drop_table("weather_alert_preferences")
    with op.batch_alter_table("saved_weather_forecasts") as batch:
        batch.drop_index("ix_saved_weather_forecasts_field_id")
        batch.drop_constraint("ck_saved_weather_forecast_field_source", type_="check")
        batch.drop_constraint("ck_saved_weather_forecast_location_source", type_="check")
        batch.drop_constraint("fk_saved_weather_forecasts_field_id_farm_fields", type_="foreignkey")
        batch.drop_column("location_source")
        batch.drop_column("field_name_snapshot")
        batch.drop_column("farm_name_snapshot")
        batch.drop_column("field_id")
