"""Add short-lived, single-use React-to-Streamlit handoff codes."""
from alembic import op
import sqlalchemy as sa

revision = "0008_streamlit_handoff"
down_revision = "0007_fields_and_evidence"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "streamlit_handoffs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("farmer_id", sa.String(36), sa.ForeignKey("farmers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_streamlit_handoffs_farmer_id", "streamlit_handoffs", ["farmer_id"])
    op.create_index("ix_streamlit_handoffs_expires_at", "streamlit_handoffs", ["expires_at"])


def downgrade():
    op.drop_index("ix_streamlit_handoffs_expires_at", table_name="streamlit_handoffs")
    op.drop_index("ix_streamlit_handoffs_farmer_id", table_name="streamlit_handoffs")
    op.drop_table("streamlit_handoffs")
