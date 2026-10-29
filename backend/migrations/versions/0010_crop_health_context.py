"""Add optional field-part and spread context to crop-health reports."""
from alembic import op
import sqlalchemy as sa


revision = "0010_crop_health_context"
down_revision = "0009_crop_health_cases"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("crop_health_cases", sa.Column("plant_parts_affected", sa.Text(), nullable=True))
    op.add_column("crop_health_cases", sa.Column("spreading", sa.Boolean(), nullable=True))


def downgrade():
    op.drop_column("crop_health_cases", "spreading")
    op.drop_column("crop_health_cases", "plant_parts_affected")
