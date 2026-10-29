"""Store revocable, expiring farmer API sessions."""
from alembic import op
import sqlalchemy as sa

revision = "0002_revocable_sessions"
down_revision = "0001_phase1_records"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("farmer_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("farmer_id", sa.String(36), sa.ForeignKey("farmers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_farmer_sessions_farmer_id", "farmer_sessions", ["farmer_id"])
    op.create_index("ix_farmer_sessions_expires_at", "farmer_sessions", ["expires_at"])


def downgrade():
    op.drop_index("ix_farmer_sessions_expires_at", table_name="farmer_sessions")
    op.drop_index("ix_farmer_sessions_farmer_id", table_name="farmer_sessions")
    op.drop_table("farmer_sessions")
