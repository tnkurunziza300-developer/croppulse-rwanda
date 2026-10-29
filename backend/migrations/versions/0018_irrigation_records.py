"""Add farmer-reported irrigation event records."""
from alembic import op
import sqlalchemy as sa


revision = "0018_irrigation_records"
down_revision = "0017_harvest_observations"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "irrigation_records",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("farm_id", sa.String(length=36), sa.ForeignKey("farms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("field_id", sa.String(length=36), sa.ForeignKey("farm_fields.id", ondelete="SET NULL"), nullable=True),
        sa.Column("crop_plan_id", sa.String(length=36), sa.ForeignKey("crop_plans.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("water_source", sa.String(length=32), nullable=False),
        sa.Column("water_source_other", sa.String(length=160), nullable=True),
        sa.Column("irrigation_method", sa.String(length=32), nullable=False, server_default="unknown"),
        sa.Column("irrigation_method_other", sa.String(length=160), nullable=True),
        sa.Column("water_quantity", sa.Float(), nullable=True),
        sa.Column("water_quantity_unit", sa.String(length=8), nullable=True),
        sa.Column("duration_value", sa.Float(), nullable=True),
        sa.Column("duration_unit", sa.String(length=12), nullable=True),
        sa.Column("purpose", sa.String(length=240), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("verification", sa.String(length=24), nullable=False, server_default="farmer_reported"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("water_source IN ('rainwater', 'river', 'lake', 'pond_reservoir', 'well_borehole', 'piped_supply', 'irrigation_scheme', 'other', 'unknown')", name="ck_irrigation_source"),
        sa.CheckConstraint("irrigation_method IN ('unknown', 'manual', 'watering_can', 'hose', 'sprinkler', 'drip', 'furrow', 'basin', 'other')", name="ck_irrigation_method"),
        sa.CheckConstraint("(water_quantity IS NULL) = (water_quantity_unit IS NULL)", name="ck_irrigation_water_pair"),
        sa.CheckConstraint("(duration_value IS NULL) = (duration_unit IS NULL)", name="ck_irrigation_duration_pair"),
        sa.CheckConstraint("water_quantity IS NULL OR water_quantity >= 0", name="ck_irrigation_water_nonnegative"),
        sa.CheckConstraint("duration_value IS NULL OR duration_value >= 0", name="ck_irrigation_duration_nonnegative"),
        sa.CheckConstraint("water_quantity_unit IS NULL OR water_quantity_unit IN ('L', 'm3')", name="ck_irrigation_water_unit"),
        sa.CheckConstraint("duration_unit IS NULL OR duration_unit IN ('minutes', 'hours')", name="ck_irrigation_duration_unit"),
        sa.CheckConstraint("(water_source = 'other') = (water_source_other IS NOT NULL)", name="ck_irrigation_source_other_pair"),
        sa.CheckConstraint("(irrigation_method = 'other') = (irrigation_method_other IS NOT NULL)", name="ck_irrigation_method_other_pair"),
        sa.CheckConstraint("verification = 'farmer_reported'", name="ck_irrigation_verification"),
    )
    op.create_index("ix_irrigation_records_farm_id", "irrigation_records", ["farm_id"])
    op.create_index("ix_irrigation_records_field_id", "irrigation_records", ["field_id"])
    op.create_index("ix_irrigation_records_crop_plan_id", "irrigation_records", ["crop_plan_id"])
    op.create_index("ix_irrigation_records_farm_date", "irrigation_records", ["farm_id", "event_date"])


def downgrade():
    op.drop_index("ix_irrigation_records_farm_date", table_name="irrigation_records")
    op.drop_index("ix_irrigation_records_crop_plan_id", table_name="irrigation_records")
    op.drop_index("ix_irrigation_records_field_id", table_name="irrigation_records")
    op.drop_index("ix_irrigation_records_farm_id", table_name="irrigation_records")
    op.drop_table("irrigation_records")
