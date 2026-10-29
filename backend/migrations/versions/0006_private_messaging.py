"""Add private farmer-to-reviewer messaging and administrator setting."""
from alembic import op
import sqlalchemy as sa

revision = "0006_private_messaging"
down_revision = "0005_self_service_account"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "messaging_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("farmer_reviewer_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_messaging_settings_singleton"),
    )
    op.execute("INSERT INTO messaging_settings (id, farmer_reviewer_enabled, updated_at) VALUES (1, FALSE, CURRENT_TIMESTAMP)")
    op.create_table(
        "private_conversations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("farmer_id", sa.String(36), sa.ForeignKey("farmers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reviewer_id", sa.String(36), sa.ForeignKey("farmers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("farmer_id", "reviewer_id", name="uq_private_conversation_pair"),
        sa.CheckConstraint("farmer_id <> reviewer_id", name="ck_private_conversation_distinct_participants"),
    )
    op.create_index("ix_private_conversations_farmer_id", "private_conversations", ["farmer_id"])
    op.create_index("ix_private_conversations_reviewer_id", "private_conversations", ["reviewer_id"])
    op.create_table(
        "private_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("conversation_id", sa.String(36), sa.ForeignKey("private_conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sender_id", sa.String(36), sa.ForeignKey("farmers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("length(trim(body)) BETWEEN 1 AND 4000", name="ck_private_message_body_length"),
    )
    op.create_index("ix_private_messages_conversation_id", "private_messages", ["conversation_id"])
    op.create_index("ix_private_messages_sender_id", "private_messages", ["sender_id"])
    op.create_index("ix_private_messages_created_at", "private_messages", ["created_at"])
    op.create_index("ix_private_message_history", "private_messages", ["conversation_id", "created_at", "id"])


def downgrade():
    op.drop_index("ix_private_message_history", table_name="private_messages")
    op.drop_index("ix_private_messages_created_at", table_name="private_messages")
    op.drop_index("ix_private_messages_sender_id", table_name="private_messages")
    op.drop_index("ix_private_messages_conversation_id", table_name="private_messages")
    op.drop_table("private_messages")
    op.drop_index("ix_private_conversations_reviewer_id", table_name="private_conversations")
    op.drop_index("ix_private_conversations_farmer_id", table_name="private_conversations")
    op.drop_table("private_conversations")
    op.drop_table("messaging_settings")
