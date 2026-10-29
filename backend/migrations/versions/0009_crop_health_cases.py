"""Add private crop-health cases, normalized photos, and reviewer updates."""
from alembic import op
import sqlalchemy as sa


revision = "0009_crop_health_cases"
down_revision = "0008_streamlit_handoff"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "crop_health_cases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("farmer_id", sa.String(36), sa.ForeignKey("farmers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("farm_id", sa.String(36), sa.ForeignKey("farms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("field_id", sa.String(36), sa.ForeignKey("farm_fields.id", ondelete="SET NULL"), nullable=True),
        sa.Column("crop_plan_id", sa.String(36), sa.ForeignKey("crop_plans.id", ondelete="SET NULL"), nullable=True),
        sa.Column("crop", sa.String(80), nullable=False),
        sa.Column("symptoms", sa.Text(), nullable=False),
        sa.Column("observed_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(32), server_default="submitted", nullable=False),
        sa.Column("diagnosis_status", sa.String(32), server_default="unresolved", nullable=False),
        sa.Column("photo_data", sa.LargeBinary(), nullable=False),
        sa.Column("photo_sha256", sa.String(64), nullable=False),
        sa.Column("photo_size_bytes", sa.Integer(), nullable=False),
        sa.Column("photo_width", sa.Integer(), nullable=False),
        sa.Column("photo_height", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('submitted', 'under_review', 'awaiting_farmer', 'resolved')", name="ck_crop_health_case_status"),
        sa.CheckConstraint("diagnosis_status IN ('unresolved', 'provisional_observation')", name="ck_crop_health_diagnosis_status"),
    )
    for name, column in (
        ("ix_crop_health_cases_farmer_id", "farmer_id"),
        ("ix_crop_health_cases_farm_id", "farm_id"),
        ("ix_crop_health_cases_field_id", "field_id"),
        ("ix_crop_health_cases_crop_plan_id", "crop_plan_id"),
        ("ix_crop_health_cases_created_at", "created_at"),
    ):
        op.create_index(name, "crop_health_cases", [column])
    op.create_index("ix_crop_health_case_owner_created", "crop_health_cases", ["farmer_id", "created_at"])
    op.create_index("ix_crop_health_case_farm_status", "crop_health_cases", ["farm_id", "status"])

    op.create_table(
        "crop_health_case_updates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("crop_health_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", sa.String(36), sa.ForeignKey("farmers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("update_type", sa.String(32), nullable=False),
        sa.Column("assessment", sa.String(32), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("assessment IS NULL OR assessment IN ('unresolved', 'provisional_observation')", name="ck_crop_health_update_assessment"),
        sa.CheckConstraint("length(trim(message)) BETWEEN 1 AND 4000", name="ck_crop_health_update_message_length"),
    )
    for name, column in (
        ("ix_crop_health_case_updates_case_id", "case_id"),
        ("ix_crop_health_case_updates_author_id", "author_id"),
        ("ix_crop_health_case_updates_created_at", "created_at"),
    ):
        op.create_index(name, "crop_health_case_updates", [column])
    op.create_index("ix_crop_health_update_case_created", "crop_health_case_updates", ["case_id", "created_at"])


def downgrade():
    op.drop_index("ix_crop_health_update_case_created", table_name="crop_health_case_updates")
    op.drop_index("ix_crop_health_case_updates_created_at", table_name="crop_health_case_updates")
    op.drop_index("ix_crop_health_case_updates_author_id", table_name="crop_health_case_updates")
    op.drop_index("ix_crop_health_case_updates_case_id", table_name="crop_health_case_updates")
    op.drop_table("crop_health_case_updates")
    op.drop_index("ix_crop_health_case_farm_status", table_name="crop_health_cases")
    op.drop_index("ix_crop_health_case_owner_created", table_name="crop_health_cases")
    op.drop_index("ix_crop_health_cases_created_at", table_name="crop_health_cases")
    op.drop_index("ix_crop_health_cases_crop_plan_id", table_name="crop_health_cases")
    op.drop_index("ix_crop_health_cases_field_id", table_name="crop_health_cases")
    op.drop_index("ix_crop_health_cases_farm_id", table_name="crop_health_cases")
    op.drop_index("ix_crop_health_cases_farmer_id", table_name="crop_health_cases")
    op.drop_table("crop_health_cases")
