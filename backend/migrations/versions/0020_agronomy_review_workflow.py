"""Add authenticated agronomic rule proposal and review history."""
from alembic import op
import sqlalchemy as sa


revision = "0020_agronomy_review_workflow"
down_revision = "0019_soil_records"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "agronomy_review_authorization_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("reviewer_id", sa.String(length=36), sa.ForeignKey("farmers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_id", sa.String(length=36), sa.ForeignKey("farmers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(length=12), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("action IN ('grant', 'revoke')", name="ck_agronomy_review_auth_action"),
    )
    op.create_index("ix_agronomy_review_authorization_events_reviewer_id", "agronomy_review_authorization_events", ["reviewer_id"])
    op.create_index("ix_agronomy_review_authorization_events_actor_id", "agronomy_review_authorization_events", ["actor_id"])
    op.create_index("ix_agronomy_review_auth_reviewer_created", "agronomy_review_authorization_events", ["reviewer_id", "created_at"])

    op.create_table(
        "agronomy_rule_proposals",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("rule_id", sa.String(length=120), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("crop_or_topic", sa.String(length=120), nullable=False),
        sa.Column("proposed_claim", sa.Text(), nullable=False),
        sa.Column("geographic_scope", sa.JSON(), nullable=False),
        sa.Column("season_scope", sa.JSON(), nullable=False),
        sa.Column("units", sa.JSON(), nullable=False),
        sa.Column("assumptions", sa.JSON(), nullable=False),
        sa.Column("limitations", sa.JSON(), nullable=False),
        sa.Column("uncertainty", sa.Text(), nullable=False),
        sa.Column("source_references", sa.JSON(), nullable=False),
        sa.Column("proposed_by", sa.String(length=36), sa.ForeignKey("farmers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("revision_of_id", sa.String(length=36), sa.ForeignKey("agronomy_rule_proposals.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("rule_id", "version", name="uq_agronomy_rule_proposal_version"),
    )
    op.create_index("ix_agronomy_rule_proposals_rule_id", "agronomy_rule_proposals", ["rule_id"])
    op.create_index("ix_agronomy_rule_proposals_proposed_by", "agronomy_rule_proposals", ["proposed_by"])
    op.create_index("ix_agronomy_rule_proposals_revision_of_id", "agronomy_rule_proposals", ["revision_of_id"])
    op.create_index("ix_agronomy_rule_proposals_created", "agronomy_rule_proposals", ["created_at"])

    op.create_table(
        "agronomy_rule_decisions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("proposal_id", sa.String(length=36), sa.ForeignKey("agronomy_rule_proposals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reviewer_id", sa.String(length=36), sa.ForeignKey("farmers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("decision", sa.String(length=24), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("decision IN ('technical_review', 'approved', 'rejected', 'withdrawn', 'superseded')",
                           name="ck_agronomy_rule_decision"),
    )
    op.create_index("ix_agronomy_rule_decisions_proposal_id", "agronomy_rule_decisions", ["proposal_id"])
    op.create_index("ix_agronomy_rule_decisions_reviewer_id", "agronomy_rule_decisions", ["reviewer_id"])
    op.create_index("ix_agronomy_rule_decisions_proposal_created", "agronomy_rule_decisions", ["proposal_id", "created_at"])


def downgrade():
    op.drop_index("ix_agronomy_rule_decisions_proposal_created", table_name="agronomy_rule_decisions")
    op.drop_index("ix_agronomy_rule_decisions_reviewer_id", table_name="agronomy_rule_decisions")
    op.drop_index("ix_agronomy_rule_decisions_proposal_id", table_name="agronomy_rule_decisions")
    op.drop_table("agronomy_rule_decisions")
    op.drop_index("ix_agronomy_rule_proposals_created", table_name="agronomy_rule_proposals")
    op.drop_index("ix_agronomy_rule_proposals_revision_of_id", table_name="agronomy_rule_proposals")
    op.drop_index("ix_agronomy_rule_proposals_proposed_by", table_name="agronomy_rule_proposals")
    op.drop_index("ix_agronomy_rule_proposals_rule_id", table_name="agronomy_rule_proposals")
    op.drop_table("agronomy_rule_proposals")
    op.drop_index("ix_agronomy_review_auth_reviewer_created", table_name="agronomy_review_authorization_events")
    op.drop_index("ix_agronomy_review_authorization_events_actor_id", table_name="agronomy_review_authorization_events")
    op.drop_index("ix_agronomy_review_authorization_events_reviewer_id", table_name="agronomy_review_authorization_events")
    op.drop_table("agronomy_review_authorization_events")
