"""Persist the latest requested forecast per account and coordinate."""
from alembic import op
import sqlalchemy as sa


revision = "0013_saved_weather_forecasts"
down_revision = "0012_weather_bulletins"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "saved_weather_forecasts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("farmer_id", sa.String(length=36), sa.ForeignKey("farmers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("forecast_json", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("farmer_id", "latitude", "longitude", name="uq_saved_weather_forecast_owner_point"),
        sa.CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_saved_weather_forecast_latitude"),
        sa.CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_saved_weather_forecast_longitude"),
        sa.CheckConstraint("status IN ('available', 'stale')", name="ck_saved_weather_forecast_status"),
    )
    op.create_index("ix_saved_weather_forecasts_farmer_id", "saved_weather_forecasts", ["farmer_id"])
    op.create_index("ix_saved_weather_forecast_retrieved_at", "saved_weather_forecasts", ["retrieved_at"])
    op.create_index("ix_saved_weather_forecast_owner_retrieved", "saved_weather_forecasts", ["farmer_id", "retrieved_at"])


def downgrade():
    op.drop_index("ix_saved_weather_forecast_owner_retrieved", table_name="saved_weather_forecasts")
    op.drop_index("ix_saved_weather_forecast_retrieved_at", table_name="saved_weather_forecasts")
    op.drop_index("ix_saved_weather_forecasts_farmer_id", table_name="saved_weather_forecasts")
    op.drop_table("saved_weather_forecasts")
