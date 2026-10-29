"""Store optional experimental model-screening results on private reports."""
from alembic import op
import sqlalchemy as sa


revision = "0011_crop_health_ai_screening"
down_revision = "0010_crop_health_context"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("crop_health_cases", sa.Column(
        "ai_screening_status", sa.String(length=32), nullable=False, server_default="not_run"))
    op.add_column("crop_health_cases", sa.Column("ai_screening_json", sa.Text(), nullable=True))
    op.add_column("crop_health_cases", sa.Column("ai_model_name", sa.String(length=120), nullable=True))
    op.add_column("crop_health_cases", sa.Column("ai_model_version", sa.String(length=64), nullable=True))
    op.add_column("crop_health_cases", sa.Column("ai_screened_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column("crop_health_cases", "ai_screened_at")
    op.drop_column("crop_health_cases", "ai_model_version")
    op.drop_column("crop_health_cases", "ai_model_name")
    op.drop_column("crop_health_cases", "ai_screening_json")
    op.drop_column("crop_health_cases", "ai_screening_status")
