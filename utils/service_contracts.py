"""Typed domain contracts shared by the Streamlit workflows and backend integrations."""
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Literal, Protocol


Verification = Literal["verified", "provisional", "user_reported", "illustrative", "unavailable"]


@dataclass
class EvidenceReference:
    source_name: str
    source_url: str | None = None
    published_on: date | None = None
    reviewed_on: date | None = None
    verification: Verification = "provisional"
    reviewer_id: str | None = None
    confidence: str = "Low"
    rationale: str = ""
    limitations: list[str] = field(default_factory=list)


@dataclass
class PlanningRequest:
    district: str
    crop: str
    season: Literal["A", "B", "C"]
    planting_date: date
    area_ha: float
    sector: str | None = None
    water_availability: str = "Unknown"
    irrigation: str = "Unknown"
    soil_notes: str | None = None
    objective: str | None = None


@dataclass
class PlannedActivity:
    id: str
    stage: str
    timing: str
    action: str
    rationale: str
    conditions: str
    warnings: list[str] = field(default_factory=list)
    evidence: list[EvidenceReference] = field(default_factory=list)


@dataclass
class CropPlanResponse:
    plan_id: str | None
    request: PlanningRequest
    activities: list[PlannedActivity]
    status: Verification = "provisional"
    generated_at: datetime | None = None


@dataclass
class WeatherRequest:
    district: str
    sector: str | None = None
    latitude: float | None = None
    longitude: float | None = None


@dataclass
class WeatherResponse:
    status: Literal["available", "stale", "unavailable", "demo"]
    source: str | None = None
    retrieved_at: datetime | None = None
    period_start: date | None = None
    period_end: date | None = None
    current: dict[str, Any] | None = None
    daily_forecast: list[dict[str, Any]] = field(default_factory=list)
    message: str = ""


@dataclass
class FarmerWeatherObservation:
    district: str
    observed_on: date
    source: str
    rainfall_mm: float | None = None
    temperature_min_c: float | None = None
    temperature_max_c: float | None = None
    verification: Verification = "user_reported"


@dataclass
class MarketQuote:
    crop: str
    market_id: str
    market_name: str
    observed_on: date
    price: float
    currency: Literal["RWF"]
    unit: str
    source_name: str
    source_url: str | None = None
    verification: Verification = "user_reported"


@dataclass
class FarmRecord:
    id: str | None
    owner_id: str | None
    district: str
    sector: str | None
    crop: str
    season: Literal["A", "B", "C"]
    record_type: str
    event_date: date
    area_ha: float | None = None
    quantity: float | None = None
    unit: str | None = None
    amount_rwf: float | None = None
    notes: str = ""
    verification: Verification = "user_reported"


@dataclass
class RecommendationFeedback:
    recommendation_id: str | None
    rating: Literal["useful", "not_useful", "unsafe", "unclear"]
    message: str = ""
    submitted_at: datetime | None = None


@dataclass
class PestReport:
    district: str
    crop: str
    observed_on: date
    description: str
    severity: str
    action_taken: str = ""
    verification: Verification = "user_reported"


@dataclass
class ExtensionVisit:
    district: str
    crop: str
    visit_date: date
    issue: str
    follow_up: str = ""
    officer_id: str | None = None


@dataclass
class CooperativeActivity:
    district: str
    crop: str
    season: Literal["A", "B", "C"]
    activity_date: date
    topic: str
    members_reached: int = 0
    area_ha: float | None = None
    follow_up: str = ""


@dataclass
class GuidanceReviewSubmission:
    crop: str
    district: str
    season: Literal["A", "B", "C"]
    suggestion: str
    evidence: list[EvidenceReference] = field(default_factory=list)
    status: Literal["submitted", "in_review", "accepted", "rejected"] = "submitted"


@dataclass
class ApiError:
    code: str
    message: str
    field_errors: dict[str, str] = field(default_factory=dict)
    request_id: str | None = None


class CropPlanningService(Protocol):
    def create_plan(self, request: PlanningRequest) -> CropPlanResponse: ...


class WeatherService(Protocol):
    def forecast(self, request: WeatherRequest) -> WeatherResponse: ...


class MarketService(Protocol):
    def quotes(self, crop: str, market_id: str | None = None) -> list[MarketQuote]: ...


class FarmRecordsService(Protocol):
    def list_records(self, owner_id: str) -> list[FarmRecord]: ...
    def create_record(self, owner_id: str, record: FarmRecord) -> FarmRecord: ...


class FeedbackService(Protocol):
    def submit(self, feedback: RecommendationFeedback) -> None: ...


class ReferenceDataService(Protocol):
    def districts(self, province: str | None = None) -> list[dict[str, str]]: ...
    def crops(self, district: str | None = None, season: str | None = None) -> list[dict[str, Any]]: ...


class RecommendationService(Protocol):
    def recommend(self, district: str, season: str, conditions: dict[str, Any]) -> list[dict[str, Any]]: ...
    def evidence(self, recommendation_id: str) -> list[EvidenceReference]: ...


class AnalyticsService(Protocol):
    def summary(self, filters: dict[str, Any]) -> dict[str, Any]: ...


class ExtensionService(Protocol):
    def create_visit(self, visit: ExtensionVisit) -> ExtensionVisit: ...


class CooperativeService(Protocol):
    def create_activity(self, activity: CooperativeActivity) -> CooperativeActivity: ...


class PestReportService(Protocol):
    def submit(self, report: PestReport) -> None: ...


class GuidanceReviewService(Protocol):
    def submit(self, submission: GuidanceReviewSubmission) -> None: ...


class UserRoleService(Protocol):
    def current_user(self) -> dict[str, Any] | None: ...
    def permissions(self) -> set[str]: ...
