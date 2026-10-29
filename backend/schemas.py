from datetime import date, datetime
import json
from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator
from knowledge import CROPS
from utils.geography import normalize_district
from utils.weather import RWANDA_BOUNDS


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    privacy_notice_accepted: bool = False

    @field_validator("password")
    @classmethod
    def password_not_blank(cls, value):
        if value.strip() != value or not value.strip():
            raise ValueError("Password cannot have leading or trailing whitespace.")
        return value

    @field_validator("display_name")
    @classmethod
    def display_name_not_blank(cls, value):
        if value is None: return None
        value = value.strip()
        if not value: raise ValueError("Name cannot be blank.")
        return value


class LoginCredentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class EmailChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_email: EmailStr


class PasswordRecoveryRequest(BaseModel):
    email: EmailStr


class AccountActionTokenInput(BaseModel):
    token: str = Field(min_length=32, max_length=128)


class PasswordResetRequest(BaseModel):
    token: str = Field(min_length=32, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_not_blank(cls, value):
        if value.strip() != value or not value.strip():
            raise ValueError("Password cannot have leading or trailing whitespace.")
        return value


class AccountDeletionRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    confirmation: Literal["DELETE"]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class StreamlitHandoffInput(BaseModel):
    code: str = Field(min_length=32, max_length=128)


class StreamlitHandoffOut(BaseModel):
    redirect_url: str
    expires_in_seconds: int = 300


class FarmerOut(BaseModel):
    id: str
    email: str
    display_name: str
    role: str
    status: str
    model_config = ConfigDict(from_attributes=True)


class AdminFarmerOut(BaseModel):
    id: str
    email: str
    display_name: str
    role: str
    status: str
    created_at: datetime
    farm_count: int
    reviewer_districts: list[str] = Field(default_factory=list)


class FarmerRoleUpdate(BaseModel):
    role: Literal["farmer", "reviewer", "admin"]
    reason: str = Field(min_length=5, max_length=1000)

    @field_validator("reason")
    @classmethod
    def clean_reason(cls, value):
        value = value.strip()
        if len(value) < 5:
            raise ValueError("Provide a reason of at least 5 characters.")
        return value


class FarmerPermissionsUpdate(BaseModel):
    role: Literal["farmer", "reviewer", "admin"]
    districts: list[str] = Field(default_factory=list, max_length=30)
    reason: str = Field(min_length=5, max_length=1000)

    @field_validator("districts")
    @classmethod
    def canonical_districts(cls, values):
        result = []
        for value in values:
            district = normalize_district(value)
            if district is None:
                raise ValueError("Choose only recognized Rwanda districts.")
            if district not in result:
                result.append(district)
        return result

    @field_validator("reason")
    @classmethod
    def clean_reason(cls, value):
        value = value.strip()
        if len(value) < 5:
            raise ValueError("Provide a reason of at least 5 characters.")
        return value


class AgronomyReviewerAuthorizationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["grant", "revoke"]
    reason: str = Field(min_length=8, max_length=1000)

    @field_validator("reason")
    @classmethod
    def clean_reason(cls, value):
        value = value.strip()
        if len(value) < 8:
            raise ValueError("Provide an audit reason of at least 8 characters.")
        return value


class AgronomyEvidenceSourceReference(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: str | None = Field(default=None, max_length=120)
    title: str = Field(min_length=3, max_length=300)
    url: str = Field(min_length=8, max_length=1000)
    source_version: str | None = Field(default=None, max_length=120)
    publication_or_revision_date: date | None = None
    locator: str = Field(min_length=2, max_length=500)
    permission_status: Literal["unknown", "confirmed_for_intended_use", "not_required_with_reason"] = "unknown"

    @field_validator("url")
    @classmethod
    def require_https_source(cls, value):
        value = value.strip()
        if not value.startswith("https://"):
            raise ValueError("Evidence source links must use HTTPS.")
        return value


class AgronomyGeographicScope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["national", "province", "district", "sector", "site", "unknown"]
    scope: list[str] = Field(min_length=1, max_length=40)
    limitations: str = Field(min_length=3, max_length=2000)

    @field_validator("scope")
    @classmethod
    def clean_scope(cls, values):
        result = list(dict.fromkeys(value.strip() for value in values))
        if any(not value for value in result):
            raise ValueError("Geographic scope entries cannot be blank.")
        return result


class AgronomyRuleProposalCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rule_id: str = Field(min_length=3, max_length=120, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]+$")
    version: str = Field(min_length=1, max_length=40)
    title: str = Field(min_length=5, max_length=240)
    category: Literal["crop_suitability", "planting", "soil", "fertilizer", "water", "crop_management", "pest_disease", "other"]
    crop_or_topic: str = Field(min_length=2, max_length=120)
    proposed_claim: str = Field(min_length=10, max_length=4000)
    geographic_scope: AgronomyGeographicScope
    season_scope: list[Literal["A", "B", "C", "not_seasonal"]] = Field(min_length=1, max_length=4)
    units: list[str] = Field(min_length=1, max_length=20)
    assumptions: list[str] = Field(min_length=1, max_length=30)
    limitations: list[str] = Field(min_length=1, max_length=30)
    uncertainty: str = Field(min_length=3, max_length=2000)
    source_references: list[AgronomyEvidenceSourceReference] = Field(default_factory=list, max_length=20)
    revision_of_id: str | None = Field(default=None, max_length=36)

    @field_validator("rule_id", "version", "title", "crop_or_topic", "proposed_claim", "uncertainty")
    @classmethod
    def trim_nonblank(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank.")
        return value

    @field_validator("units", "assumptions", "limitations")
    @classmethod
    def clean_lists(cls, values):
        result = [value.strip() for value in values]
        if any(not value for value in result):
            raise ValueError("List entries cannot be blank.")
        return result


class AgronomyRuleDecisionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["technical_review", "approved", "rejected", "withdrawn", "superseded"]
    rationale: str = Field(min_length=10, max_length=4000)

    @field_validator("rationale")
    @classmethod
    def rationale_not_blank(cls, value):
        value = value.strip()
        if len(value) < 10:
            raise ValueError("Provide a decision rationale of at least 10 characters.")
        return value


class AccountStatusUpdate(BaseModel):
    status: Literal["active", "suspended"]
    reason: str = Field(min_length=5, max_length=1000)

    @field_validator("reason")
    @classmethod
    def clean_reason(cls, value):
        value = value.strip()
        if len(value) < 5:
            raise ValueError("Provide a reason of at least 5 characters.")
        return value


class ReasonInput(BaseModel):
    reason: str = Field(min_length=5, max_length=1000)

    @field_validator("reason")
    @classmethod
    def clean_reason(cls, value):
        value = value.strip()
        if len(value) < 5:
            raise ValueError("Provide a reason of at least 5 characters.")
        return value


class ReviewerDistrictsUpdate(BaseModel):
    districts: list[str] = Field(max_length=30)

    @field_validator("districts")
    @classmethod
    def canonical_districts(cls, values):
        result = []
        for value in values:
            district = normalize_district(value)
            if district is None:
                raise ValueError("Choose only recognized Rwanda districts.")
            if district not in result:
                result.append(district)
        return result


class PrivateMessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    body: str = Field(min_length=1, max_length=4000)

    @field_validator("body")
    @classmethod
    def message_not_blank(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be blank.")
        return value


class PrivateConversationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reviewer_id: str = Field(min_length=36, max_length=36)


class PrivateMessagesRead(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message_ids: list[str] = Field(max_length=100)


class MessagingSettingUpdate(BaseModel):
    farmer_reviewer_enabled: bool
    reason: str = Field(min_length=5, max_length=1000)

    @field_validator("reason")
    @classmethod
    def clean_reason(cls, value):
        value = value.strip()
        if len(value) < 5:
            raise ValueError("Provide a reason of at least 5 characters.")
        return value


class ReviewDecisionInput(BaseModel):
    decision: Literal["approved_as_reviewed", "rejected", "correction_requested"]
    reason: str = Field(min_length=5, max_length=2000)

    @field_validator("reason")
    @classmethod
    def clean_reason(cls, value):
        value = value.strip()
        if len(value) < 5:
            raise ValueError("Provide a reason of at least 5 characters.")
        return value


class FarmCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    district: str = Field(min_length=1, max_length=80)
    sector: str | None = Field(default=None, max_length=80)
    area_ha: float | None = Field(default=None, gt=0, le=100000, allow_inf_nan=False)

    @field_validator("district")
    @classmethod
    def canonical_district(cls, value):
        normalized = normalize_district(value)
        if normalized is None:
            raise ValueError("Choose one of Rwanda's recognized districts.")
        return normalized

    @field_validator("name")
    @classmethod
    def nonblank_name(cls, value):
        value = value.strip()
        if not value: raise ValueError("Farm name cannot be blank.")
        return value


class FarmOut(FarmCreate):
    id: str
    owner_id: str
    model_config = ConfigDict(from_attributes=True)


class FarmUpdate(FarmCreate):
    pass


class FieldCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    area_ha: float | None = Field(default=None, gt=0, le=100000, allow_inf_nan=False)
    latitude: float | None = Field(default=None, ge=-90, le=90, allow_inf_nan=False)
    longitude: float | None = Field(default=None, ge=-180, le=180, allow_inf_nan=False)

    @field_validator("name")
    @classmethod
    def field_name_nonblank(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Field name cannot be blank.")
        return value

    @model_validator(mode="after")
    def coordinates_paired(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Enter both coordinates or leave both blank.")
        if self.latitude is not None:
            south, north, west, east = RWANDA_BOUNDS
            if not (south <= self.latitude <= north and west <= self.longitude <= east):
                raise ValueError("Coordinates are outside the NISR Rwanda bounding extent.")
        return self


class FieldOut(FieldCreate):
    id: str
    farm_id: str
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class WeatherForecastRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)
    save_to_account: bool = Field(default=False)
    field_id: str | None = Field(default=None, min_length=1, max_length=36)
    location_source: Literal["saved_field", "manual", "device"] = "manual"

    @model_validator(mode="after")
    def field_source_consistent(self):
        if self.field_id is not None and self.location_source != "saved_field":
            raise ValueError("A field association requires saved-field coordinates.")
        if self.location_source == "saved_field" and self.field_id is None:
            raise ValueError("Saved-field coordinates require a field identifier.")
        return self


class WeatherAlertPreferenceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool


class WeatherAlertStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["acknowledged", "dismissed"]


class PlanCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    district: str = Field(min_length=1, max_length=80)
    crop: str = Field(min_length=1, max_length=80)
    season: str = Field(pattern="^[ABC]$")
    planting_date: date
    area_ha: float = Field(gt=0, le=100000, allow_inf_nan=False)
    field_id: str | None = None
    plan: dict

    @field_validator("plan")
    @classmethod
    def bounded_json_plan(cls, value):
        try:
            encoded = json.dumps(value, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("Plan must contain valid JSON values.") from exc
        if len(encoded.encode("utf-8")) > 500_000:
            raise ValueError("Plan content is too large.")
        return value

    @field_validator("district")
    @classmethod
    def canonical_district(cls, value):
        normalized = normalize_district(value)
        if normalized is None: raise ValueError("Choose one of Rwanda's recognized districts.")
        return normalized

    @field_validator("crop")
    @classmethod
    def supported_crop(cls, value):
        value = value.strip()
        if value not in CROPS: raise ValueError("Choose a crop supported by this prototype.")
        return value


class CropRecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    district: str = Field(min_length=1, max_length=80)
    season: str = Field(pattern="^[ABC]$")
    elevation_m: float | None = Field(default=None, ge=800, le=4600, allow_inf_nan=False)
    irrigation: Literal["Unknown", "Yes", "No"] = "Unknown"
    water_availability: Literal["Unknown", "Low", "Medium", "High"] = "Unknown"

    @field_validator("district")
    @classmethod
    def known_district(cls, value):
        normalized = normalize_district(value)
        if normalized is None: raise ValueError("Choose one of Rwanda's recognized districts.")
        return normalized


class PlanOut(PlanCreate):
    id: str
    farm_id: str
    verification: str
    status: Literal["draft", "planned", "planted", "monitoring", "harvesting", "completed", "cancelled"]
    actual_planting_date: date | None = None
    evidence: list[dict] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class PlanUpdate(PlanCreate):
    """Full replacement of an editable draft/planned crop plan."""


class PlanStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["planted", "monitoring", "harvesting", "completed", "cancelled"]
    actual_planting_date: date | None = None

    @model_validator(mode="after")
    def require_actual_date_for_planting(self):
        if self.status == "planted" and self.actual_planting_date is None:
            raise ValueError("Record the actual planting date when marking a plan planted.")
        if self.status != "planted" and self.actual_planting_date is not None:
            raise ValueError("Actual planting date can only be supplied when marking a plan planted.")
        return self


HarvestAreaUnit = Literal["ha", "m2", "acre"]
HarvestQuantityUnit = Literal["kg", "g", "t", "lb"]


class HarvestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    crop: str = Field(min_length=1, max_length=80)
    season: Literal["A", "B", "C"]
    harvest_date: date
    field_id: str | None = None
    crop_plan_id: str | None = None
    harvested_area: float = Field(gt=0, le=100000, allow_inf_nan=False)
    area_unit: HarvestAreaUnit
    quantity: float = Field(gt=0, le=1000000000, allow_inf_nan=False)
    quantity_unit: HarvestQuantityUnit
    loss_quantity: float | None = Field(default=None, ge=0, le=1000000000, allow_inf_nan=False)
    post_harvest_observations: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("crop")
    @classmethod
    def supported_harvest_crop(cls, value):
        value = value.strip()
        if value not in CROPS:
            raise ValueError("Choose a crop supported by this prototype.")
        return value

    @field_validator("harvest_date")
    @classmethod
    def harvest_date_not_future(cls, value):
        if value > date.today():
            raise ValueError("Harvest date cannot be in the future.")
        return value

    @field_validator("post_harvest_observations", "notes")
    @classmethod
    def normalize_optional_harvest_text(cls, value):
        if value is None:
            return None
        value = value.strip()
        return value or None

class HarvestOut(HarvestCreate):
    id: str
    farm_id: str
    yield_kg_ha: float | None
    yield_calculation: str | None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


HarvestObservationUnit = Literal["kg", "g", "t", "lb"]


class HarvestObservationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    observed_date: date
    storage_method: str | None = Field(default=None, max_length=160)
    storage_location: str | None = Field(default=None, max_length=240)
    stored_quantity: float | None = Field(default=None, ge=0, le=1000000000, allow_inf_nan=False)
    stored_unit: HarvestObservationUnit | None = None
    lost_quantity: float | None = Field(default=None, ge=0, le=1000000000, allow_inf_nan=False)
    lost_unit: HarvestObservationUnit | None = None
    condition: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=2000)
    follow_up: str | None = Field(default=None, max_length=2000)

    @field_validator("observed_date")
    @classmethod
    def observation_date_not_future(cls, value):
        if value > date.today():
            raise ValueError("Observation date cannot be in the future.")
        return value

    @field_validator("storage_method", "storage_location", "condition", "notes", "follow_up")
    @classmethod
    def normalize_optional_observation_text(cls, value):
        if value is None:
            return None
        value = value.strip()
        return value or None

    @model_validator(mode="after")
    def validate_quantity_units(self):
        if (self.stored_quantity is None) != (self.stored_unit is None):
            raise ValueError("Stored quantity and unit must be provided together.")
        if (self.lost_quantity is None) != (self.lost_unit is None):
            raise ValueError("Lost quantity and unit must be provided together.")
        if (self.stored_quantity is not None and self.lost_quantity is not None
                and self.stored_unit == self.lost_unit and self.lost_quantity > self.stored_quantity):
            raise ValueError("Lost quantity cannot exceed stored quantity when both use the same unit.")
        return self


class HarvestObservationOut(HarvestObservationCreate):
    id: str
    harvest_id: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


SoilNutrientUnit = Literal["mg/kg", "g/kg", "cmol/kg", "%"]
SoilOrganicMatterUnit = Literal["g/kg", "%"]


class SoilObservationCreate(BaseModel):
    """Farmer-entered visible soil observations; not a laboratory assessment."""
    model_config = ConfigDict(extra="forbid")
    field_id: str | None = None
    observation_date: date
    soil_description: str | None = Field(default=None, max_length=500)
    drainage_observation: str | None = Field(default=None, max_length=500)
    erosion_observation: str | None = Field(default=None, max_length=500)
    management_practices: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("observation_date")
    @classmethod
    def soil_observation_not_future(cls, value):
        if value > date.today():
            raise ValueError("Soil observation date cannot be in the future.")
        return value

    @field_validator("soil_description", "drainage_observation", "erosion_observation", "management_practices", "notes")
    @classmethod
    def normalize_soil_observation_text(cls, value):
        if value is None:
            return None
        value = value.strip()
        return value or None


class SoilObservationOut(SoilObservationCreate):
    id: str
    farm_id: str
    verification: Literal["farmer_reported"]
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class SoilTestRecordCreate(BaseModel):
    """Optional farmer-entered transcription of soil-test measurements."""
    model_config = ConfigDict(extra="forbid")
    field_id: str | None = None
    test_date: date
    ph_value: float | None = Field(default=None, ge=0, le=14, allow_inf_nan=False,
                                   description="pH on the conventional unitless 0–14 scale.")
    nitrogen_value: float | None = Field(default=None, ge=0, le=1000000000, allow_inf_nan=False)
    nitrogen_unit: SoilNutrientUnit | None = None
    phosphorus_value: float | None = Field(default=None, ge=0, le=1000000000, allow_inf_nan=False)
    phosphorus_unit: SoilNutrientUnit | None = None
    potassium_value: float | None = Field(default=None, ge=0, le=1000000000, allow_inf_nan=False)
    potassium_unit: SoilNutrientUnit | None = None
    organic_matter_value: float | None = Field(default=None, ge=0, le=1000000000, allow_inf_nan=False)
    organic_matter_unit: SoilOrganicMatterUnit | None = None
    laboratory_name: str | None = Field(default=None, max_length=240)
    report_reference: str | None = Field(default=None, max_length=240)
    source_details: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("test_date")
    @classmethod
    def soil_test_date_not_future(cls, value):
        if value > date.today():
            raise ValueError("Soil test date cannot be in the future.")
        return value

    @field_validator("laboratory_name", "report_reference", "source_details", "notes")
    @classmethod
    def normalize_soil_test_text(cls, value):
        if value is None:
            return None
        value = value.strip()
        return value or None

    @model_validator(mode="after")
    def require_units_for_measured_values(self):
        for value_name, unit_name in (
            ("nitrogen_value", "nitrogen_unit"),
            ("phosphorus_value", "phosphorus_unit"),
            ("potassium_value", "potassium_unit"),
            ("organic_matter_value", "organic_matter_unit"),
        ):
            if (getattr(self, value_name) is None) != (getattr(self, unit_name) is None):
                raise ValueError(f"{value_name.replace('_value', '').replace('_', ' ').capitalize()} value and unit must be provided together.")
        return self


class SoilTestRecordOut(SoilTestRecordCreate):
    id: str
    farm_id: str
    verification: Literal["farmer_reported"]
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


WaterSource = Literal[
    "rainwater", "river", "lake", "pond_reservoir", "well_borehole",
    "piped_supply", "irrigation_scheme", "other", "unknown",
]
IrrigationMethod = Literal[
    "unknown", "manual", "watering_can", "hose", "sprinkler", "drip",
    "furrow", "basin", "other",
]
WaterQuantityUnit = Literal["L", "m3"]
IrrigationDurationUnit = Literal["minutes", "hours"]


class IrrigationRecordCreate(BaseModel):
    """A farmer-entered event record; it does not assess water sufficiency."""
    model_config = ConfigDict(extra="forbid")
    event_date: date
    field_id: str | None = None
    crop_plan_id: str | None = None
    water_source: WaterSource = "unknown"
    water_source_other: str | None = Field(default=None, max_length=160)
    irrigation_method: IrrigationMethod = "unknown"
    irrigation_method_other: str | None = Field(default=None, max_length=160)
    water_quantity: float | None = Field(default=None, ge=0, le=1000000000, allow_inf_nan=False)
    water_quantity_unit: WaterQuantityUnit | None = None
    duration_value: float | None = Field(default=None, ge=0, le=100000, allow_inf_nan=False)
    duration_unit: IrrigationDurationUnit | None = None
    purpose: str | None = Field(default=None, max_length=240)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("event_date")
    @classmethod
    def event_date_not_future(cls, value):
        if value > date.today():
            raise ValueError("Irrigation event date cannot be in the future.")
        return value

    @field_validator("water_source_other", "irrigation_method_other", "purpose", "notes")
    @classmethod
    def normalize_irrigation_text(cls, value):
        if value is None:
            return None
        value = value.strip()
        return value or None

    @model_validator(mode="after")
    def validate_units_and_other_values(self):
        if (self.water_quantity is None) != (self.water_quantity_unit is None):
            raise ValueError("Water quantity and unit must be provided together.")
        if (self.duration_value is None) != (self.duration_unit is None):
            raise ValueError("Duration and unit must be provided together.")
        if (self.water_source == "other") != (self.water_source_other is not None):
            raise ValueError("Describe the water source only when Other is selected.")
        if (self.irrigation_method == "other") != (self.irrigation_method_other is not None):
            raise ValueError("Describe the irrigation method only when Other is selected.")
        return self


class IrrigationRecordOut(IrrigationRecordCreate):
    id: str
    farm_id: str
    verification: Literal["farmer_reported"]
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ActivityCreate(BaseModel):
    district: str = Field(min_length=1, max_length=80)
    crop: str = Field(min_length=1, max_length=80)
    season: str = Field(pattern="^[ABC]$")
    activity_type: str = Field(min_length=1, max_length=60)
    event_date: date
    area_ha: float | None = Field(default=None, ge=0, le=100000, allow_inf_nan=False)
    quantity: float | None = Field(default=None, ge=0, le=1000000000, allow_inf_nan=False)
    unit: str | None = Field(default=None, max_length=30)
    amount_rwf: float | None = Field(default=None, ge=0, le=1000000000000, allow_inf_nan=False)
    notes: str = Field(default="", max_length=2000)
    idempotency_key: str | None = Field(default=None, max_length=80)

    @field_validator("district")
    @classmethod
    def canonical_district(cls, value):
        normalized = normalize_district(value)
        if normalized is None: raise ValueError("Choose one of Rwanda's recognized districts.")
        return normalized

    @field_validator("crop")
    @classmethod
    def supported_crop(cls, value):
        value = value.strip()
        if value not in CROPS: raise ValueError("Choose a crop supported by this prototype.")
        return value

    @field_validator("activity_type")
    @classmethod
    def nonblank_activity_type(cls, value):
        value = value.strip()
        if not value: raise ValueError("Activity type cannot be blank.")
        return value


class ActivityUpdate(BaseModel):
    district: str = Field(min_length=1, max_length=80)
    crop: str = Field(min_length=1, max_length=80)
    season: str = Field(pattern="^[ABC]$")
    activity_type: str = Field(min_length=1, max_length=60)
    event_date: date
    area_ha: float | None = Field(default=None, ge=0, le=100000, allow_inf_nan=False)
    quantity: float | None = Field(default=None, ge=0, le=1000000000, allow_inf_nan=False)
    unit: str | None = Field(default=None, max_length=30)
    amount_rwf: float | None = Field(default=None, ge=0, le=1000000000000, allow_inf_nan=False)
    notes: str = Field(default="", max_length=2000)

    @field_validator("district")
    @classmethod
    def canonical_district(cls, value):
        normalized = normalize_district(value)
        if normalized is None: raise ValueError("Choose one of Rwanda's recognized districts.")
        return normalized

    @field_validator("crop")
    @classmethod
    def supported_crop(cls, value):
        value = value.strip()
        if value not in CROPS: raise ValueError("Choose a crop supported by this prototype.")
        return value

    @field_validator("activity_type")
    @classmethod
    def nonblank_activity_type(cls, value):
        value = value.strip()
        if not value: raise ValueError("Activity type cannot be blank.")
        return value


class ActivityOut(ActivityCreate):
    id: str
    farm_id: str
    verification: str
    review_status: str = "pending"
    model_config = ConfigDict(from_attributes=True)


class FarmTimelineEntryOut(BaseModel):
    id: str
    event_date: date | None
    event_type: Literal[
        "crop_plan_created", "planting_recorded", "activity", "irrigation",
        "soil_observation", "soil_test", "harvest", "post_harvest_observation",
    ]
    farm_id: str
    farm_name: str
    field_id: str | None = None
    field_name: str | None = None
    description: str
    source_label: str
    href: str


class FarmTimelineOut(BaseModel):
    entries: list[FarmTimelineEntryOut]
    has_more: bool


class CropHealthReviewerUpdate(BaseModel):
    action: Literal["start_review", "request_information", "provide_update", "resolve"]
    message: str = Field(min_length=1, max_length=4000)
    assessment: Literal["unresolved", "provisional_observation"] | None = None

    @field_validator("message")
    @classmethod
    def nonblank_message(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Add a note before submitting this review update.")
        return value


class CropHealthFarmerReply(BaseModel):
    message: str = Field(min_length=1, max_length=4000)

    @field_validator("message")
    @classmethod
    def nonblank_message(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Add a reply before submitting.")
        return value
