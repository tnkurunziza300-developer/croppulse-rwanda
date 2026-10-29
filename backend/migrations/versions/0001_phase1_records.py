"""Create farmer, farm, crop plan and activity tables."""
from alembic import op
import sqlalchemy as sa

revision = "0001_phase1_records"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("farmers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("password_hash", sa.String(512), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("privacy_notice_version", sa.String(32), nullable=False),
        sa.Column("privacy_accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_farmers_email", "farmers", ["email"], unique=True)
    op.create_table("farms",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("farmers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False), sa.Column("district", sa.String(80), nullable=False),
        sa.Column("sector", sa.String(80)), sa.Column("area_ha", sa.Float),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_farms_owner_id", "farms", ["owner_id"])
    op.create_table("crop_plans",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("farm_id", sa.String(36), sa.ForeignKey("farms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("district", sa.String(80), nullable=False),
        sa.Column("crop", sa.String(80), nullable=False), sa.Column("season", sa.String(1), nullable=False),
        sa.Column("planting_date", sa.Date(), nullable=False), sa.Column("area_ha", sa.Float(), nullable=False),
        sa.Column("plan_json", sa.Text(), nullable=False), sa.Column("verification", sa.String(24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_crop_plans_farm_id", "crop_plans", ["farm_id"])
    op.create_table("farm_activities",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("farm_id", sa.String(36), sa.ForeignKey("farms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("district", sa.String(80), nullable=False), sa.Column("crop", sa.String(80), nullable=False),
        sa.Column("season", sa.String(1), nullable=False), sa.Column("activity_type", sa.String(60), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False), sa.Column("area_ha", sa.Float()),
        sa.Column("quantity", sa.Float()), sa.Column("unit", sa.String(30)), sa.Column("amount_rwf", sa.Float()),
        sa.Column("notes", sa.Text(), nullable=False), sa.Column("verification", sa.String(24), nullable=False),
        sa.Column("idempotency_key", sa.String(80)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("farm_id", "idempotency_key", name="uq_activity_idempotency"))
    op.create_index("ix_farm_activities_farm_id", "farm_activities", ["farm_id"])

def downgrade():
    op.drop_index("ix_farm_activities_farm_id", table_name="farm_activities")
    op.drop_table("farm_activities")
    op.drop_index("ix_crop_plans_farm_id", table_name="crop_plans")
    op.drop_table("crop_plans")
    op.drop_index("ix_farms_owner_id", table_name="farms")
    op.drop_table("farms")
    op.drop_index("ix_farmers_email", table_name="farmers")
    op.drop_table("farmers")
