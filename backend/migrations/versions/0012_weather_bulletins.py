"""Add source-preserving METEO RWANDA bulletin archive."""
from alembic import op
import sqlalchemy as sa


revision = "0012_weather_bulletins"
down_revision = "0011_crop_health_ai_screening"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "weather_bulletins",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("document_key", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("category", sa.String(length=24), nullable=False),
        sa.Column("publisher", sa.String(length=160), nullable=False),
        sa.Column("issued_at", sa.Date(), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=False),
        sa.Column("provenance_status", sa.String(length=80), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("content_type", sa.String(length=80), nullable=False),
        sa.Column("document_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("document_key", name="uq_weather_bulletin_document_key"),
        sa.UniqueConstraint("sha256", name="uq_weather_bulletins_sha256"),
    )
    op.create_index("ix_weather_bulletins_document_key", "weather_bulletins", ["document_key"])
    op.create_index("ix_weather_bulletins_category", "weather_bulletins", ["category"])


def downgrade():
    op.drop_index("ix_weather_bulletins_category", table_name="weather_bulletins")
    op.drop_index("ix_weather_bulletins_document_key", table_name="weather_bulletins")
    op.drop_table("weather_bulletins")
