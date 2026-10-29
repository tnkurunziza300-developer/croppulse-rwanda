"""Add owner-scoped farm harvest outcome records."""
from alembic import op
import sqlalchemy as sa


revision = "0016_farm_harvests"
down_revision = "0015_weather_alert_foundation"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "farm_harvests",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("farm_id", sa.String(length=36), sa.ForeignKey("farms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("field_id", sa.String(length=36), sa.ForeignKey("farm_fields.id", ondelete="SET NULL"), nullable=True),
        sa.Column("crop_plan_id", sa.String(length=36), sa.ForeignKey("crop_plans.id", ondelete="SET NULL"), nullable=True),
        sa.Column("crop", sa.String(length=80), nullable=False),
        sa.Column("season", sa.String(length=1), nullable=False),
        sa.Column("harvest_date", sa.Date(), nullable=False),
        sa.Column("harvested_area", sa.Float(), nullable=False),
        sa.Column("area_unit", sa.String(length=8), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("quantity_unit", sa.String(length=8), nullable=False),
        sa.Column("loss_quantity", sa.Float(), nullable=True),
        sa.Column("post_harvest_observations", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("season IN ('A', 'B', 'C')", name="ck_farm_harvest_season"),
        sa.CheckConstraint("harvested_area > 0", name="ck_farm_harvest_area_positive"),
        sa.CheckConstraint("quantity > 0", name="ck_farm_harvest_quantity_positive"),
        sa.CheckConstraint("loss_quantity IS NULL OR loss_quantity >= 0", name="ck_farm_harvest_loss_nonnegative"),
        sa.CheckConstraint("area_unit IN ('ha', 'm2', 'acre')", name="ck_farm_harvest_area_unit"),
        sa.CheckConstraint("quantity_unit IN ('kg', 'g', 't', 'lb')", name="ck_farm_harvest_quantity_unit"),
    )
    op.create_index("ix_farm_harvests_farm_id", "farm_harvests", ["farm_id"])
    op.create_index("ix_farm_harvests_field_id", "farm_harvests", ["field_id"])
    op.create_index("ix_farm_harvests_crop_plan_id", "farm_harvests", ["crop_plan_id"])
    op.create_index("ix_farm_harvests_farm_date", "farm_harvests", ["farm_id", "harvest_date"])


def downgrade():
    op.drop_index("ix_farm_harvests_farm_date", table_name="farm_harvests")
    op.drop_index("ix_farm_harvests_crop_plan_id", table_name="farm_harvests")
    op.drop_index("ix_farm_harvests_field_id", table_name="farm_harvests")
    op.drop_index("ix_farm_harvests_farm_id", table_name="farm_harvests")
    op.drop_table("farm_harvests")
