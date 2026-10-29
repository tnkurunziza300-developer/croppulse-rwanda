"""Add persisted crop-plan status and actual planting date."""
from alembic import op
import sqlalchemy as sa

revision = "0004_crop_plan_lifecycle"
down_revision = "0003_roles_review_and_admin"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("crop_plans", sa.Column("status", sa.String(24), nullable=False, server_default="planned"))
    op.add_column("crop_plans", sa.Column("actual_planting_date", sa.Date(), nullable=True))


def downgrade():
    op.drop_column("crop_plans", "actual_planting_date")
    op.drop_column("crop_plans", "status")
