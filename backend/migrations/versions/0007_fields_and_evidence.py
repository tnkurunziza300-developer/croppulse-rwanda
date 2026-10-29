"""Add farmer fields and provenance snapshots for crop plans."""
from alembic import op
import sqlalchemy as sa

revision = "0007_fields_and_evidence"
down_revision = "0006_private_messaging"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "farm_fields",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("farm_id", sa.String(36), sa.ForeignKey("farms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("area_ha", sa.Float(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("area_ha IS NULL OR area_ha > 0", name="ck_farm_field_area_positive"),
        sa.CheckConstraint("latitude IS NULL OR latitude BETWEEN -90 AND 90", name="ck_farm_field_latitude"),
        sa.CheckConstraint("longitude IS NULL OR longitude BETWEEN -180 AND 180", name="ck_farm_field_longitude"),
        sa.CheckConstraint("(latitude IS NULL) = (longitude IS NULL)", name="ck_farm_field_coordinate_pair"),
    )
    op.create_index("ix_farm_fields_farm_id", "farm_fields", ["farm_id"])
    with op.batch_alter_table("crop_plans") as batch:
        batch.add_column(sa.Column("field_id", sa.String(36), nullable=True))
        batch.create_foreign_key("fk_crop_plans_field_id_farm_fields", "farm_fields", ["field_id"], ["id"], ondelete="SET NULL")
        batch.create_index("ix_crop_plans_field_id", ["field_id"])
    op.create_table(
        "crop_plan_evidence",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("crop_plan_id", sa.String(36), sa.ForeignKey("crop_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column("crop", sa.String(80), nullable=True),
        sa.Column("geographic_applicability", sa.String(240), nullable=True),
        sa.Column("source_name", sa.String(240), nullable=False),
        sa.Column("source_organization", sa.String(240), nullable=True),
        sa.Column("source_url", sa.String(1000), nullable=True),
        sa.Column("source_identifier", sa.String(240), nullable=True),
        sa.Column("publication_date", sa.Date(), nullable=True),
        sa.Column("retrieval_date", sa.Date(), nullable=True),
        sa.Column("evidence_period", sa.String(120), nullable=True),
        sa.Column("units", sa.String(120), nullable=True),
        sa.Column("confidence", sa.String(120), nullable=True),
        sa.Column("limitations", sa.Text(), nullable=False, server_default=""),
        sa.Column("dataset_version", sa.String(120), nullable=True),
        sa.Column("recommender_version", sa.String(120), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verification_status", sa.String(24), nullable=False, server_default="unverified"),
    )
    op.create_index("ix_crop_plan_evidence_crop_plan_id", "crop_plan_evidence", ["crop_plan_id"])
    op.create_index("ix_crop_plan_evidence_plan_generated", "crop_plan_evidence", ["crop_plan_id", "generated_at"])


def downgrade():
    op.drop_index("ix_crop_plan_evidence_plan_generated", table_name="crop_plan_evidence")
    op.drop_index("ix_crop_plan_evidence_crop_plan_id", table_name="crop_plan_evidence")
    op.drop_table("crop_plan_evidence")
    with op.batch_alter_table("crop_plans") as batch:
        batch.drop_index("ix_crop_plans_field_id")
        batch.drop_constraint("fk_crop_plans_field_id_farm_fields", type_="foreignkey")
        batch.drop_column("field_id")
    op.drop_index("ix_farm_fields_farm_id", table_name="farm_fields")
    op.drop_table("farm_fields")
