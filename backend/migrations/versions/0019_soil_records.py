"""Add farmer-reported soil observations and soil-test records."""
from alembic import op
import sqlalchemy as sa


revision = "0019_soil_records"
down_revision = "0018_irrigation_records"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "soil_observations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("farm_id", sa.String(length=36), sa.ForeignKey("farms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("field_id", sa.String(length=36), sa.ForeignKey("farm_fields.id", ondelete="SET NULL"), nullable=True),
        sa.Column("observation_date", sa.Date(), nullable=False),
        sa.Column("soil_description", sa.String(length=500), nullable=True),
        sa.Column("drainage_observation", sa.String(length=500), nullable=True),
        sa.Column("erosion_observation", sa.String(length=500), nullable=True),
        sa.Column("management_practices", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("verification", sa.String(length=24), nullable=False, server_default="farmer_reported"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("verification = 'farmer_reported'", name="ck_soil_observation_verification"),
    )
    op.create_index("ix_soil_observations_farm_id", "soil_observations", ["farm_id"])
    op.create_index("ix_soil_observations_field_id", "soil_observations", ["field_id"])
    op.create_index("ix_soil_observations_farm_date", "soil_observations", ["farm_id", "observation_date"])

    op.create_table(
        "soil_test_records",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("farm_id", sa.String(length=36), sa.ForeignKey("farms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("field_id", sa.String(length=36), sa.ForeignKey("farm_fields.id", ondelete="SET NULL"), nullable=True),
        sa.Column("test_date", sa.Date(), nullable=False),
        sa.Column("ph_value", sa.Float(), nullable=True),
        sa.Column("nitrogen_value", sa.Float(), nullable=True),
        sa.Column("nitrogen_unit", sa.String(length=12), nullable=True),
        sa.Column("phosphorus_value", sa.Float(), nullable=True),
        sa.Column("phosphorus_unit", sa.String(length=12), nullable=True),
        sa.Column("potassium_value", sa.Float(), nullable=True),
        sa.Column("potassium_unit", sa.String(length=12), nullable=True),
        sa.Column("organic_matter_value", sa.Float(), nullable=True),
        sa.Column("organic_matter_unit", sa.String(length=12), nullable=True),
        sa.Column("laboratory_name", sa.String(length=240), nullable=True),
        sa.Column("report_reference", sa.String(length=240), nullable=True),
        sa.Column("source_details", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("verification", sa.String(length=24), nullable=False, server_default="farmer_reported"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("ph_value IS NULL OR (ph_value >= 0 AND ph_value <= 14)", name="ck_soil_test_ph_range"),
        sa.CheckConstraint("nitrogen_value IS NULL OR nitrogen_value >= 0", name="ck_soil_test_nitrogen_nonnegative"),
        sa.CheckConstraint("phosphorus_value IS NULL OR phosphorus_value >= 0", name="ck_soil_test_phosphorus_nonnegative"),
        sa.CheckConstraint("potassium_value IS NULL OR potassium_value >= 0", name="ck_soil_test_potassium_nonnegative"),
        sa.CheckConstraint("organic_matter_value IS NULL OR organic_matter_value >= 0", name="ck_soil_test_organic_matter_nonnegative"),
        sa.CheckConstraint("(nitrogen_value IS NULL) = (nitrogen_unit IS NULL)", name="ck_soil_test_nitrogen_pair"),
        sa.CheckConstraint("(phosphorus_value IS NULL) = (phosphorus_unit IS NULL)", name="ck_soil_test_phosphorus_pair"),
        sa.CheckConstraint("(potassium_value IS NULL) = (potassium_unit IS NULL)", name="ck_soil_test_potassium_pair"),
        sa.CheckConstraint("(organic_matter_value IS NULL) = (organic_matter_unit IS NULL)", name="ck_soil_test_organic_matter_pair"),
        sa.CheckConstraint("nitrogen_unit IS NULL OR nitrogen_unit IN ('mg/kg', 'g/kg', 'cmol/kg', '%')", name="ck_soil_test_nitrogen_unit"),
        sa.CheckConstraint("phosphorus_unit IS NULL OR phosphorus_unit IN ('mg/kg', 'g/kg', 'cmol/kg', '%')", name="ck_soil_test_phosphorus_unit"),
        sa.CheckConstraint("potassium_unit IS NULL OR potassium_unit IN ('mg/kg', 'g/kg', 'cmol/kg', '%')", name="ck_soil_test_potassium_unit"),
        sa.CheckConstraint("organic_matter_unit IS NULL OR organic_matter_unit IN ('g/kg', '%')", name="ck_soil_test_organic_matter_unit"),
        sa.CheckConstraint("verification = 'farmer_reported'", name="ck_soil_test_verification"),
    )
    op.create_index("ix_soil_test_records_farm_id", "soil_test_records", ["farm_id"])
    op.create_index("ix_soil_test_records_field_id", "soil_test_records", ["field_id"])
    op.create_index("ix_soil_test_records_farm_date", "soil_test_records", ["farm_id", "test_date"])


def downgrade():
    op.drop_index("ix_soil_test_records_farm_date", table_name="soil_test_records")
    op.drop_index("ix_soil_test_records_field_id", table_name="soil_test_records")
    op.drop_index("ix_soil_test_records_farm_id", table_name="soil_test_records")
    op.drop_table("soil_test_records")
    op.drop_index("ix_soil_observations_farm_date", table_name="soil_observations")
    op.drop_index("ix_soil_observations_field_id", table_name="soil_observations")
    op.drop_index("ix_soil_observations_farm_id", table_name="soil_observations")
    op.drop_table("soil_observations")
