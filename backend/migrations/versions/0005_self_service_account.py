"""Add expiring account-action tokens and preserve reviewer decisions on deletion."""
from alembic import op
import sqlalchemy as sa

revision = "0005_self_service_account"
down_revision = "0004_crop_plan_lifecycle"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "account_action_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("farmer_id", sa.String(36), sa.ForeignKey("farmers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("purpose", sa.String(32), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("target_email", sa.String(254), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_account_action_tokens_farmer_id", "account_action_tokens", ["farmer_id"])
    op.create_index("ix_account_action_tokens_purpose", "account_action_tokens", ["purpose"])
    op.create_index("ix_account_action_tokens_token_hash", "account_action_tokens", ["token_hash"], unique=True)
    op.create_index("ix_account_action_tokens_expires_at", "account_action_tokens", ["expires_at"])

    # Keep immutable reviewer decisions while anonymizing the deleted reviewer's identity.
    with op.batch_alter_table(
        "activity_review_decisions",
        recreate="always",
        naming_convention={"fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"},
    ) as batch_op:
        batch_op.alter_column("reviewer_id", existing_type=sa.String(36), nullable=True)
        batch_op.drop_constraint("fk_activity_review_decisions_reviewer_id_farmers", type_="foreignkey")
        batch_op.create_foreign_key(
            "fk_activity_review_decisions_reviewer_id_farmers", "farmers", ["reviewer_id"], ["id"], ondelete="SET NULL"
        )


def downgrade():
    with op.batch_alter_table(
        "activity_review_decisions",
        recreate="always",
        naming_convention={"fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"},
    ) as batch_op:
        batch_op.alter_column("reviewer_id", existing_type=sa.String(36), nullable=False)
        batch_op.drop_constraint("fk_activity_review_decisions_reviewer_id_farmers", type_="foreignkey")
        batch_op.create_foreign_key(
            "fk_activity_review_decisions_reviewer_id_farmers", "farmers", ["reviewer_id"], ["id"], ondelete="RESTRICT"
        )
    op.drop_index("ix_account_action_tokens_expires_at", table_name="account_action_tokens")
    op.drop_index("ix_account_action_tokens_token_hash", table_name="account_action_tokens")
    op.drop_index("ix_account_action_tokens_purpose", table_name="account_action_tokens")
    op.drop_index("ix_account_action_tokens_farmer_id", table_name="account_action_tokens")
    op.drop_table("account_action_tokens")
