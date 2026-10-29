"""Store source-linked rainfall outlook values from METEO RWANDA PDFs."""
from alembic import op
import sqlalchemy as sa


revision = "0014_weather_bulletin_records"
down_revision = "0013_saved_weather_forecasts"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "weather_bulletin_records",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("bulletin_id", sa.String(length=36), sa.ForeignKey("weather_bulletins.id", ondelete="CASCADE"), nullable=False),
        sa.Column("record_key", sa.String(length=100), nullable=False),
        sa.Column("record_type", sa.String(length=24), nullable=False),
        sa.Column("variable", sa.String(length=32), nullable=False),
        sa.Column("geography_type", sa.String(length=24), nullable=False),
        sa.Column("geography_label", sa.String(length=600), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=False),
        sa.Column("period_label", sa.String(length=80), nullable=False),
        sa.Column("value_min", sa.Float(), nullable=True),
        sa.Column("value_max", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=24), nullable=False),
        sa.Column("normal_min", sa.Float(), nullable=True),
        sa.Column("normal_max", sa.Float(), nullable=True),
        sa.Column("anomaly_label", sa.String(length=80), nullable=True),
        sa.Column("source_page", sa.Integer(), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("transcription_status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("record_type IN ('monthly_outlook', 'seasonal_outlook')", name="ck_weather_record_type"),
        sa.CheckConstraint("variable = 'rainfall_total'", name="ck_weather_record_variable"),
        sa.CheckConstraint("geography_type IN ('national', 'named_area')", name="ck_weather_record_geography_type"),
        sa.CheckConstraint("value_min IS NULL OR value_max IS NULL OR value_min <= value_max", name="ck_weather_record_value_order"),
        sa.CheckConstraint("source_page >= 1", name="ck_weather_record_source_page"),
        sa.UniqueConstraint("bulletin_id", "record_key", name="uq_weather_bulletin_record_key"),
    )
    op.create_index("ix_weather_bulletin_records_type_period", "weather_bulletin_records", ["record_type", "valid_from"])
    op.create_index("ix_weather_bulletin_records_geography", "weather_bulletin_records", ["geography_type", "valid_from"])


def downgrade():
    op.drop_index("ix_weather_bulletin_records_geography", table_name="weather_bulletin_records")
    op.drop_index("ix_weather_bulletin_records_type_period", table_name="weather_bulletin_records")
    op.drop_table("weather_bulletin_records")
