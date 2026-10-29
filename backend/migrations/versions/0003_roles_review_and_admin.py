"""Additive roles, reviewer scope, review history and admin audit."""
from alembic import op
import sqlalchemy as sa

revision = "0003_roles_review_and_admin"
down_revision = "0002_revocable_sessions"
branch_labels = None
depends_on = None


def upgrade():
    # Existing rows receive the least-privileged role and active status.
    op.add_column("farmers", sa.Column("role", sa.String(24), nullable=False, server_default="farmer"))
    op.add_column("farmers", sa.Column("status", sa.String(24), nullable=False, server_default="active"))
    op.create_index("ix_farmers_role", "farmers", ["role"])
    op.create_index("ix_farmers_status", "farmers", ["status"])

    op.create_table(
        "reviewer_districts",
        sa.Column("reviewer_id", sa.String(36), sa.ForeignKey("farmers.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("district", sa.String(80), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "admin_audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("farmers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("target_farmer_id", sa.String(36), sa.ForeignKey("farmers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("target_type", sa.String(40), nullable=False),
        sa.Column("target_id", sa.String(80), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("result", sa.String(24), nullable=False, server_default="success"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_admin_audit_events_actor_id", "admin_audit_events", ["actor_id"])
    op.create_index("ix_admin_audit_events_target_farmer_id", "admin_audit_events", ["target_farmer_id"])
    op.create_table(
        "activity_review_decisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("activity_id", sa.String(36), sa.ForeignKey("farm_activities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reviewer_id", sa.String(36), sa.ForeignKey("farmers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_activity_review_decisions_activity_id", "activity_review_decisions", ["activity_id"])
    op.create_index("ix_activity_review_decisions_reviewer_id", "activity_review_decisions", ["reviewer_id"])
    op.create_table(
        "auth_attempts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("bucket_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_auth_attempts_bucket_hash", "auth_attempts", ["bucket_hash"])
    op.create_index("ix_auth_attempts_created_at", "auth_attempts", ["created_at"])


def downgrade():
    op.drop_index("ix_auth_attempts_created_at", table_name="auth_attempts")
    op.drop_index("ix_auth_attempts_bucket_hash", table_name="auth_attempts")
    op.drop_table("auth_attempts")
    op.drop_index("ix_activity_review_decisions_reviewer_id", table_name="activity_review_decisions")
    op.drop_index("ix_activity_review_decisions_activity_id", table_name="activity_review_decisions")
    op.drop_table("activity_review_decisions")
    op.drop_index("ix_admin_audit_events_target_farmer_id", table_name="admin_audit_events")
    op.drop_index("ix_admin_audit_events_actor_id", table_name="admin_audit_events")
    op.drop_table("admin_audit_events")
    op.drop_table("reviewer_districts")
    op.drop_index("ix_farmers_status", table_name="farmers")
    op.drop_index("ix_farmers_role", table_name="farmers")
    op.drop_column("farmers", "status")
    op.drop_column("farmers", "role")
