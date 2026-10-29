"""Add farmer-reported post-harvest observations."""
from alembic import op
import sqlalchemy as sa


revision = "0017_harvest_observations"
down_revision = "0016_farm_harvests"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "harvest_observations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("harvest_id", sa.String(length=36), sa.ForeignKey("farm_harvests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("observed_date", sa.Date(), nullable=False),
        sa.Column("storage_method", sa.String(length=160), nullable=True),
        sa.Column("storage_location", sa.String(length=240), nullable=True),
        sa.Column("stored_quantity", sa.Float(), nullable=True),
        sa.Column("stored_unit", sa.String(length=8), nullable=True),
        sa.Column("lost_quantity", sa.Float(), nullable=True),
        sa.Column("lost_unit", sa.String(length=8), nullable=True),
        sa.Column("condition", sa.String(length=1000), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("follow_up", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("stored_quantity IS NULL OR stored_quantity >= 0", name="ck_harvest_observation_stored_nonnegative"),
        sa.CheckConstraint("lost_quantity IS NULL OR lost_quantity >= 0", name="ck_harvest_observation_loss_nonnegative"),
        sa.CheckConstraint("(stored_quantity IS NULL) = (stored_unit IS NULL)", name="ck_harvest_observation_stored_pair"),
        sa.CheckConstraint("(lost_quantity IS NULL) = (lost_unit IS NULL)", name="ck_harvest_observation_loss_pair"),
        sa.CheckConstraint("stored_unit IS NULL OR stored_unit IN ('kg', 'g', 't', 'lb')", name="ck_harvest_observation_stored_unit"),
        sa.CheckConstraint("lost_unit IS NULL OR lost_unit IN ('kg', 'g', 't', 'lb')", name="ck_harvest_observation_loss_unit"),
    )
    op.create_index("ix_harvest_observations_harvest_id", "harvest_observations", ["harvest_id"])
    op.create_index("ix_harvest_observations_harvest_date", "harvest_observations", ["harvest_id", "observed_date"])


def downgrade():
    op.drop_index("ix_harvest_observations_harvest_date", table_name="harvest_observations")
    op.drop_index("ix_harvest_observations_harvest_id", table_name="harvest_observations")
    op.drop_table("harvest_observations")
