"""Phase 1 relational schema. User is the farmer profile and owns farms."""
from datetime import date, datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Float, ForeignKey, Index, Integer, JSON, LargeBinary, String, Text, UniqueConstraint, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow():
    return datetime.now(timezone.utc)


class Farmer(Base):
    __tablename__ = "farmers"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    display_name: Mapped[str] = mapped_column(String(120))
    privacy_notice_version: Mapped[str] = mapped_column(String(32))
    privacy_accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    role: Mapped[str] = mapped_column(String(24), default="farmer", server_default="farmer", index=True)
    status: Mapped[str] = mapped_column(String(24), default="active", server_default="active", index=True)
    farms: Mapped[list["Farm"]] = relationship(back_populates="owner", cascade="all, delete-orphan")


class ReviewerDistrict(Base):
    __tablename__ = "reviewer_districts"
    reviewer_id: Mapped[str] = mapped_column(ForeignKey("farmers.id", ondelete="CASCADE"), primary_key=True)
    district: Mapped[str] = mapped_column(String(80), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AdminAuditEvent(Base):
    __tablename__ = "admin_audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("farmers.id", ondelete="SET NULL"), nullable=True, index=True)
    target_farmer_id: Mapped[str | None] = mapped_column(ForeignKey("farmers.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(80))
    target_type: Mapped[str] = mapped_column(String(40))
    target_id: Mapped[str] = mapped_column(String(80))
    reason: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[str] = mapped_column(String(24), default="success")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ActivityReviewDecision(Base):
    __tablename__ = "activity_review_decisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    activity_id: Mapped[str] = mapped_column(ForeignKey("farm_activities.id", ondelete="CASCADE"), index=True)
    reviewer_id: Mapped[str | None] = mapped_column(ForeignKey("farmers.id", ondelete="SET NULL"), nullable=True, index=True)
    decision: Mapped[str] = mapped_column(String(32))
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AgronomyReviewAuthorizationEvent(Base):
    """Append-only admin grants and revocations for agronomic rule review."""
    __tablename__ = "agronomy_review_authorization_events"
    __table_args__ = (Index("ix_agronomy_review_auth_reviewer_created", "reviewer_id", "created_at"),
                      CheckConstraint("action IN ('grant', 'revoke')", name="ck_agronomy_review_auth_action"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    reviewer_id: Mapped[str] = mapped_column(ForeignKey("farmers.id", ondelete="CASCADE"), index=True)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("farmers.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(12))
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AgronomyRuleProposal(Base):
    """Immutable scoped proposal; revisions are separate rows linked to their predecessor."""
    __tablename__ = "agronomy_rule_proposals"
    __table_args__ = (UniqueConstraint("rule_id", "version", name="uq_agronomy_rule_proposal_version"),
                      Index("ix_agronomy_rule_proposals_created", "created_at"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    rule_id: Mapped[str] = mapped_column(String(120), index=True)
    version: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(240))
    category: Mapped[str] = mapped_column(String(40))
    crop_or_topic: Mapped[str] = mapped_column(String(120))
    proposed_claim: Mapped[str] = mapped_column(Text)
    geographic_scope: Mapped[dict] = mapped_column(JSON)
    season_scope: Mapped[list] = mapped_column(JSON)
    units: Mapped[list] = mapped_column(JSON)
    assumptions: Mapped[list] = mapped_column(JSON)
    limitations: Mapped[list] = mapped_column(JSON)
    uncertainty: Mapped[str] = mapped_column(Text)
    source_references: Mapped[list] = mapped_column(JSON)
    proposed_by: Mapped[str | None] = mapped_column(ForeignKey("farmers.id", ondelete="SET NULL"), nullable=True, index=True)
    revision_of_id: Mapped[str | None] = mapped_column(ForeignKey("agronomy_rule_proposals.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AgronomyRuleDecision(Base):
    """Append-only authenticated decision history for one exact proposal version."""
    __tablename__ = "agronomy_rule_decisions"
    __table_args__ = (Index("ix_agronomy_rule_decisions_proposal_created", "proposal_id", "created_at"),
                      CheckConstraint("decision IN ('technical_review', 'approved', 'rejected', 'withdrawn', 'superseded')",
                                      name="ck_agronomy_rule_decision"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    proposal_id: Mapped[str] = mapped_column(ForeignKey("agronomy_rule_proposals.id", ondelete="CASCADE"), index=True)
    reviewer_id: Mapped[str | None] = mapped_column(ForeignKey("farmers.id", ondelete="SET NULL"), nullable=True, index=True)
    decision: Mapped[str] = mapped_column(String(24))
    rationale: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class FarmerSession(Base):
    __tablename__ = "farmer_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # JWT jti
    farmer_id: Mapped[str] = mapped_column(ForeignKey("farmers.id", ondelete="CASCADE"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class StreamlitHandoff(Base):
    __tablename__ = "streamlit_handoffs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    farmer_id: Mapped[str] = mapped_column(ForeignKey("farmers.id", ondelete="CASCADE"), index=True)
    code_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuthAttempt(Base):
    __tablename__ = "auth_attempts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    bucket_hash: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class AccountActionToken(Base):
    __tablename__ = "account_action_tokens"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    farmer_id: Mapped[str] = mapped_column(ForeignKey("farmers.id", ondelete="CASCADE"), index=True)
    purpose: Mapped[str] = mapped_column(String(32), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    target_email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MessagingSetting(Base):
    __tablename__ = "messaging_settings"
    __table_args__ = (CheckConstraint("id = 1", name="ck_messaging_settings_singleton"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    farmer_reviewer_enabled: Mapped[bool] = mapped_column(default=False, server_default=false())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class PrivateConversation(Base):
    __tablename__ = "private_conversations"
    __table_args__ = (UniqueConstraint("farmer_id", "reviewer_id", name="uq_private_conversation_pair"),
                      CheckConstraint("farmer_id <> reviewer_id", name="ck_private_conversation_distinct_participants"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    farmer_id: Mapped[str] = mapped_column(ForeignKey("farmers.id", ondelete="CASCADE"), index=True)
    reviewer_id: Mapped[str] = mapped_column(ForeignKey("farmers.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    messages: Mapped[list["PrivateMessage"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")


class PrivateMessage(Base):
    __tablename__ = "private_messages"
    __table_args__ = (
        CheckConstraint("length(trim(body)) BETWEEN 1 AND 4000", name="ck_private_message_body_length"),
        Index("ix_private_message_history", "conversation_id", "created_at", "id"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    conversation_id: Mapped[str] = mapped_column(ForeignKey("private_conversations.id", ondelete="CASCADE"), index=True)
    sender_id: Mapped[str] = mapped_column(ForeignKey("farmers.id", ondelete="CASCADE"), index=True)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    conversation: Mapped[PrivateConversation] = relationship(back_populates="messages")


class Farm(Base):
    __tablename__ = "farms"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    owner_id: Mapped[str] = mapped_column(ForeignKey("farmers.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    district: Mapped[str] = mapped_column(String(80))
    sector: Mapped[str | None] = mapped_column(String(80), nullable=True)
    area_ha: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    owner: Mapped[Farmer] = relationship(back_populates="farms")
    plans: Mapped[list["CropPlan"]] = relationship(back_populates="farm", cascade="all, delete-orphan")
    activities: Mapped[list["FarmActivity"]] = relationship(back_populates="farm", cascade="all, delete-orphan")
    fields: Mapped[list["FarmField"]] = relationship(back_populates="farm", cascade="all, delete-orphan")
    harvests: Mapped[list["FarmHarvest"]] = relationship(back_populates="farm", cascade="all, delete-orphan")
    irrigation_records: Mapped[list["IrrigationRecord"]] = relationship(back_populates="farm", cascade="all, delete-orphan")
    soil_observations: Mapped[list["SoilObservation"]] = relationship(back_populates="farm", cascade="all, delete-orphan")
    soil_tests: Mapped[list["SoilTestRecord"]] = relationship(back_populates="farm", cascade="all, delete-orphan")


class FarmField(Base):
    """A farmer-managed field; optional coordinates are user supplied."""
    __tablename__ = "farm_fields"
    __table_args__ = (
        CheckConstraint("area_ha IS NULL OR area_ha > 0", name="ck_farm_field_area_positive"),
        CheckConstraint("latitude IS NULL OR latitude BETWEEN -90 AND 90", name="ck_farm_field_latitude"),
        CheckConstraint("longitude IS NULL OR longitude BETWEEN -180 AND 180", name="ck_farm_field_longitude"),
        CheckConstraint("(latitude IS NULL) = (longitude IS NULL)", name="ck_farm_field_coordinate_pair"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    farm_id: Mapped[str] = mapped_column(ForeignKey("farms.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    area_ha: Mapped[float | None] = mapped_column(Float, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    farm: Mapped[Farm] = relationship(back_populates="fields")
    plans: Mapped[list["CropPlan"]] = relationship(back_populates="field")
    irrigation_records: Mapped[list["IrrigationRecord"]] = relationship(back_populates="field")


class WeatherBulletin(Base):
    """Publisher-authored weather forecast PDF, stored unchanged with provenance."""
    __tablename__ = "weather_bulletins"
    __table_args__ = (UniqueConstraint("document_key", name="uq_weather_bulletin_document_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    document_key: Mapped[str] = mapped_column(String(255), index=True)
    title: Mapped[str] = mapped_column(String(240))
    category: Mapped[str] = mapped_column(String(24), index=True)
    publisher: Mapped[str] = mapped_column(String(160), default="Rwanda Meteorology Agency (METEO RWANDA)")
    issued_at: Mapped[date] = mapped_column(Date)
    valid_from: Mapped[date] = mapped_column(Date)
    valid_to: Mapped[date] = mapped_column(Date)
    source_url: Mapped[str] = mapped_column(String(1000))
    provenance_status: Mapped[str] = mapped_column(String(80), default="publisher-indicated; exact-original-match-pending")
    sha256: Mapped[str] = mapped_column(String(64), unique=True)
    content_type: Mapped[str] = mapped_column(String(80), default="application/pdf")
    document_bytes: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class WeatherBulletinRecord(Base):
    """Source-linked numeric outlook extracted from a publisher bulletin."""
    __tablename__ = "weather_bulletin_records"
    __table_args__ = (
        CheckConstraint("record_type IN ('monthly_outlook', 'seasonal_outlook')", name="ck_weather_record_type"),
        CheckConstraint("variable = 'rainfall_total'", name="ck_weather_record_variable"),
        CheckConstraint("geography_type IN ('national', 'named_area')", name="ck_weather_record_geography_type"),
        CheckConstraint("value_min IS NULL OR value_max IS NULL OR value_min <= value_max", name="ck_weather_record_value_order"),
        CheckConstraint("source_page >= 1", name="ck_weather_record_source_page"),
        UniqueConstraint("bulletin_id", "record_key", name="uq_weather_bulletin_record_key"),
        Index("ix_weather_bulletin_records_type_period", "record_type", "valid_from"),
        Index("ix_weather_bulletin_records_geography", "geography_type", "valid_from"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    bulletin_id: Mapped[str] = mapped_column(ForeignKey("weather_bulletins.id", ondelete="CASCADE"))
    record_key: Mapped[str] = mapped_column(String(100))
    record_type: Mapped[str] = mapped_column(String(24))
    variable: Mapped[str] = mapped_column(String(32), default="rainfall_total")
    geography_type: Mapped[str] = mapped_column(String(24))
    geography_label: Mapped[str] = mapped_column(String(600))
    valid_from: Mapped[date] = mapped_column(Date)
    valid_to: Mapped[date] = mapped_column(Date)
    period_label: Mapped[str] = mapped_column(String(80))
    value_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(24), default="mm per period")
    normal_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    normal_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    anomaly_label: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_page: Mapped[int] = mapped_column(Integer)
    source_text: Mapped[str] = mapped_column(Text)
    transcription_status: Mapped[str] = mapped_column(String(32), default="numeric-range-transcribed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SavedWeatherForecast(Base):
    """Latest requested provider forecast per farmer-supplied point and account."""
    __tablename__ = "saved_weather_forecasts"
    __table_args__ = (
        UniqueConstraint("farmer_id", "latitude", "longitude", name="uq_saved_weather_forecast_owner_point"),
        CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_saved_weather_forecast_latitude"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_saved_weather_forecast_longitude"),
        CheckConstraint("status IN ('available', 'stale')", name="ck_saved_weather_forecast_status"),
        CheckConstraint("location_source IN ('saved_field', 'manual', 'device')", name="ck_saved_weather_forecast_location_source"),
        CheckConstraint("field_id IS NULL OR location_source = 'saved_field'", name="ck_saved_weather_forecast_field_source"),
        Index("ix_saved_weather_forecasts_farmer_id", "farmer_id"),
        Index("ix_saved_weather_forecast_retrieved_at", "retrieved_at"),
        Index("ix_saved_weather_forecast_owner_retrieved", "farmer_id", "retrieved_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    farmer_id: Mapped[str] = mapped_column(ForeignKey("farmers.id", ondelete="CASCADE"))
    field_id: Mapped[str | None] = mapped_column(ForeignKey("farm_fields.id", ondelete="SET NULL"), nullable=True, index=True)
    farm_name_snapshot: Mapped[str | None] = mapped_column(String(120), nullable=True)
    field_name_snapshot: Mapped[str | None] = mapped_column(String(120), nullable=True)
    location_source: Mapped[str] = mapped_column(String(16), default="manual", server_default="manual")
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(16))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    forecast_json: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class WeatherAlertPreference(Base):
    """Explicit, disabled-by-default opt-in for a farmer-owned field."""
    __tablename__ = "weather_alert_preferences"
    __table_args__ = (
        UniqueConstraint("farmer_id", "field_id", name="uq_weather_alert_preference_farmer_field"),
        Index("ix_weather_alert_preferences_farmer", "farmer_id"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    farmer_id: Mapped[str] = mapped_column(ForeignKey("farmers.id", ondelete="CASCADE"))
    field_id: Mapped[str] = mapped_column(ForeignKey("farm_fields.id", ondelete="CASCADE"))
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class WeatherAlert(Base):
    """Persistent in-app alert history; generated only by an approved rule."""
    __tablename__ = "weather_alerts"
    __table_args__ = (
        UniqueConstraint("dedupe_key", name="uq_weather_alert_dedupe_key"),
        CheckConstraint("status IN ('active', 'acknowledged', 'dismissed')", name="ck_weather_alert_status"),
        CheckConstraint("approval_status IN ('approved', 'inactive')", name="ck_weather_alert_approval_status"),
        CheckConstraint("valid_to >= valid_from", name="ck_weather_alert_valid_period"),
        Index("ix_weather_alerts_recipient_created", "recipient_id", "created_at"),
        Index("ix_weather_alerts_field_period", "field_id", "valid_from", "valid_to"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    recipient_id: Mapped[str] = mapped_column(ForeignKey("farmers.id", ondelete="CASCADE"))
    farm_id: Mapped[str | None] = mapped_column(ForeignKey("farms.id", ondelete="SET NULL"), nullable=True)
    field_id: Mapped[str | None] = mapped_column(ForeignKey("farm_fields.id", ondelete="SET NULL"), nullable=True)
    forecast_id: Mapped[str | None] = mapped_column(ForeignKey("saved_weather_forecasts.id", ondelete="SET NULL"), nullable=True)
    farm_name_snapshot: Mapped[str | None] = mapped_column(String(120), nullable=True)
    field_name_snapshot: Mapped[str | None] = mapped_column(String(120), nullable=True)
    alert_type: Mapped[str] = mapped_column(String(60))
    rule_id: Mapped[str] = mapped_column(String(100))
    rule_version: Mapped[str] = mapped_column(String(40))
    weather_source: Mapped[str] = mapped_column(String(80))
    forecast_retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    valid_from: Mapped[date] = mapped_column(Date)
    valid_to: Mapped[date] = mapped_column(Date)
    reason: Mapped[str] = mapped_column(Text)
    evidence_status: Mapped[str] = mapped_column(String(40))
    evidence_snapshot_json: Mapped[str] = mapped_column(Text)
    approval_status: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="active", server_default="active")
    dedupe_key: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CropPlan(Base):
    __tablename__ = "crop_plans"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    farm_id: Mapped[str] = mapped_column(ForeignKey("farms.id", ondelete="CASCADE"), index=True)
    field_id: Mapped[str | None] = mapped_column(ForeignKey("farm_fields.id", ondelete="SET NULL"), nullable=True, index=True)
    district: Mapped[str] = mapped_column(String(80))
    crop: Mapped[str] = mapped_column(String(80))
    season: Mapped[str] = mapped_column(String(1))
    planting_date: Mapped[date] = mapped_column(Date)
    area_ha: Mapped[float] = mapped_column(Float)
    plan_json: Mapped[str] = mapped_column(Text)
    verification: Mapped[str] = mapped_column(String(24), default="provisional")
    status: Mapped[str] = mapped_column(String(24), default="planned", server_default="planned")
    actual_planting_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    farm: Mapped[Farm] = relationship(back_populates="plans")
    field: Mapped[FarmField | None] = relationship(back_populates="plans")
    evidence: Mapped[list["CropPlanEvidence"]] = relationship(back_populates="crop_plan", cascade="all, delete-orphan")
    harvests: Mapped[list["FarmHarvest"]] = relationship(back_populates="crop_plan")
    irrigation_records: Mapped[list["IrrigationRecord"]] = relationship(back_populates="crop_plan")


class CropPlanEvidence(Base):
    """Structured provenance snapshot; absent sources are never synthesized."""
    __tablename__ = "crop_plan_evidence"
    __table_args__ = (Index("ix_crop_plan_evidence_plan_generated", "crop_plan_id", "generated_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    crop_plan_id: Mapped[str] = mapped_column(ForeignKey("crop_plans.id", ondelete="CASCADE"), index=True)
    claim: Mapped[str] = mapped_column(Text)
    crop: Mapped[str | None] = mapped_column(String(80), nullable=True)
    geographic_applicability: Mapped[str | None] = mapped_column(String(240), nullable=True)
    source_name: Mapped[str] = mapped_column(String(240))
    source_organization: Mapped[str | None] = mapped_column(String(240), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    source_identifier: Mapped[str | None] = mapped_column(String(240), nullable=True)
    publication_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    retrieval_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    evidence_period: Mapped[str | None] = mapped_column(String(120), nullable=True)
    units: Mapped[str | None] = mapped_column(String(120), nullable=True)
    confidence: Mapped[str | None] = mapped_column(String(120), nullable=True)
    limitations: Mapped[str] = mapped_column(Text, default="")
    dataset_version: Mapped[str | None] = mapped_column(String(120), nullable=True)
    recommender_version: Mapped[str | None] = mapped_column(String(120), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    verification_status: Mapped[str] = mapped_column(String(24), default="unverified", server_default="unverified")
    crop_plan: Mapped[CropPlan] = relationship(back_populates="evidence")


class FarmActivity(Base):
    __tablename__ = "farm_activities"
    __table_args__ = (UniqueConstraint("farm_id", "idempotency_key", name="uq_activity_idempotency"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    farm_id: Mapped[str] = mapped_column(ForeignKey("farms.id", ondelete="CASCADE"), index=True)
    district: Mapped[str] = mapped_column(String(80))
    crop: Mapped[str] = mapped_column(String(80))
    season: Mapped[str] = mapped_column(String(1))
    activity_type: Mapped[str] = mapped_column(String(60))
    event_date: Mapped[date] = mapped_column(Date)
    area_ha: Mapped[float | None] = mapped_column(Float, nullable=True)
    quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(30), nullable=True)
    amount_rwf: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    verification: Mapped[str] = mapped_column(String(24), default="user_reported")
    idempotency_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    farm: Mapped[Farm] = relationship(back_populates="activities")


class FarmHarvest(Base):
    __tablename__ = "farm_harvests"
    __table_args__ = (
        CheckConstraint("season IN ('A', 'B', 'C')", name="ck_farm_harvest_season"),
        CheckConstraint("harvested_area > 0", name="ck_farm_harvest_area_positive"),
        CheckConstraint("quantity > 0", name="ck_farm_harvest_quantity_positive"),
        CheckConstraint("loss_quantity IS NULL OR loss_quantity >= 0", name="ck_farm_harvest_loss_nonnegative"),
        CheckConstraint("area_unit IN ('ha', 'm2', 'acre')", name="ck_farm_harvest_area_unit"),
        CheckConstraint("quantity_unit IN ('kg', 'g', 't', 'lb')", name="ck_farm_harvest_quantity_unit"),
        Index("ix_farm_harvests_farm_date", "farm_id", "harvest_date"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    farm_id: Mapped[str] = mapped_column(ForeignKey("farms.id", ondelete="CASCADE"), index=True)
    field_id: Mapped[str | None] = mapped_column(ForeignKey("farm_fields.id", ondelete="SET NULL"), nullable=True, index=True)
    crop_plan_id: Mapped[str | None] = mapped_column(ForeignKey("crop_plans.id", ondelete="SET NULL"), nullable=True, index=True)
    crop: Mapped[str] = mapped_column(String(80))
    season: Mapped[str] = mapped_column(String(1))
    harvest_date: Mapped[date] = mapped_column(Date)
    harvested_area: Mapped[float] = mapped_column(Float)
    area_unit: Mapped[str] = mapped_column(String(8))
    quantity: Mapped[float] = mapped_column(Float)
    quantity_unit: Mapped[str] = mapped_column(String(8))
    loss_quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    post_harvest_observations: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    farm: Mapped[Farm] = relationship(back_populates="harvests")
    crop_plan: Mapped[CropPlan | None] = relationship(back_populates="harvests")
    observations: Mapped[list["HarvestObservation"]] = relationship(back_populates="harvest", cascade="all, delete-orphan")


class HarvestObservation(Base):
    __tablename__ = "harvest_observations"
    __table_args__ = (
        CheckConstraint("stored_quantity IS NULL OR stored_quantity >= 0", name="ck_harvest_observation_stored_nonnegative"),
        CheckConstraint("lost_quantity IS NULL OR lost_quantity >= 0", name="ck_harvest_observation_loss_nonnegative"),
        CheckConstraint("(stored_quantity IS NULL) = (stored_unit IS NULL)", name="ck_harvest_observation_stored_pair"),
        CheckConstraint("(lost_quantity IS NULL) = (lost_unit IS NULL)", name="ck_harvest_observation_loss_pair"),
        CheckConstraint("stored_unit IS NULL OR stored_unit IN ('kg', 'g', 't', 'lb')", name="ck_harvest_observation_stored_unit"),
        CheckConstraint("lost_unit IS NULL OR lost_unit IN ('kg', 'g', 't', 'lb')", name="ck_harvest_observation_loss_unit"),
        Index("ix_harvest_observations_harvest_date", "harvest_id", "observed_date"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    harvest_id: Mapped[str] = mapped_column(ForeignKey("farm_harvests.id", ondelete="CASCADE"), nullable=False, index=True)
    observed_date: Mapped[date] = mapped_column(Date, nullable=False)
    storage_method: Mapped[str | None] = mapped_column(String(160), nullable=True)
    storage_location: Mapped[str | None] = mapped_column(String(240), nullable=True)
    stored_quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    stored_unit: Mapped[str | None] = mapped_column(String(8), nullable=True)
    lost_quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    lost_unit: Mapped[str | None] = mapped_column(String(8), nullable=True)
    condition: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    harvest: Mapped[FarmHarvest] = relationship(back_populates="observations")


class IrrigationRecord(Base):
    """Farmer-reported water-management event, without inferred adequacy."""
    __tablename__ = "irrigation_records"
    __table_args__ = (
        CheckConstraint("water_source IN ('rainwater', 'river', 'lake', 'pond_reservoir', 'well_borehole', 'piped_supply', 'irrigation_scheme', 'other', 'unknown')", name="ck_irrigation_source"),
        CheckConstraint("irrigation_method IN ('unknown', 'manual', 'watering_can', 'hose', 'sprinkler', 'drip', 'furrow', 'basin', 'other')", name="ck_irrigation_method"),
        CheckConstraint("(water_quantity IS NULL) = (water_quantity_unit IS NULL)", name="ck_irrigation_water_pair"),
        CheckConstraint("(duration_value IS NULL) = (duration_unit IS NULL)", name="ck_irrigation_duration_pair"),
        CheckConstraint("water_quantity IS NULL OR water_quantity >= 0", name="ck_irrigation_water_nonnegative"),
        CheckConstraint("duration_value IS NULL OR duration_value >= 0", name="ck_irrigation_duration_nonnegative"),
        CheckConstraint("water_quantity_unit IS NULL OR water_quantity_unit IN ('L', 'm3')", name="ck_irrigation_water_unit"),
        CheckConstraint("duration_unit IS NULL OR duration_unit IN ('minutes', 'hours')", name="ck_irrigation_duration_unit"),
        CheckConstraint("(water_source = 'other') = (water_source_other IS NOT NULL)", name="ck_irrigation_source_other_pair"),
        CheckConstraint("(irrigation_method = 'other') = (irrigation_method_other IS NOT NULL)", name="ck_irrigation_method_other_pair"),
        CheckConstraint("verification = 'farmer_reported'", name="ck_irrigation_verification"),
        Index("ix_irrigation_records_farm_date", "farm_id", "event_date"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    farm_id: Mapped[str] = mapped_column(ForeignKey("farms.id", ondelete="CASCADE"), nullable=False, index=True)
    field_id: Mapped[str | None] = mapped_column(ForeignKey("farm_fields.id", ondelete="SET NULL"), nullable=True, index=True)
    crop_plan_id: Mapped[str | None] = mapped_column(ForeignKey("crop_plans.id", ondelete="SET NULL"), nullable=True, index=True)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    water_source: Mapped[str] = mapped_column(String(32), nullable=False)
    water_source_other: Mapped[str | None] = mapped_column(String(160), nullable=True)
    irrigation_method: Mapped[str] = mapped_column(String(32), default="unknown", nullable=False)
    irrigation_method_other: Mapped[str | None] = mapped_column(String(160), nullable=True)
    water_quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    water_quantity_unit: Mapped[str | None] = mapped_column(String(8), nullable=True)
    duration_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_unit: Mapped[str | None] = mapped_column(String(12), nullable=True)
    purpose: Mapped[str | None] = mapped_column(String(240), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification: Mapped[str] = mapped_column(String(24), default="farmer_reported", server_default="farmer_reported", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    farm: Mapped[Farm] = relationship(back_populates="irrigation_records")
    field: Mapped[FarmField | None] = relationship(back_populates="irrigation_records")
    crop_plan: Mapped[CropPlan | None] = relationship(back_populates="irrigation_records")


class SoilObservation(Base):
    """Farmer-reported soil observations, not measured test results."""
    __tablename__ = "soil_observations"
    __table_args__ = (
        CheckConstraint("verification = 'farmer_reported'", name="ck_soil_observation_verification"),
        Index("ix_soil_observations_farm_date", "farm_id", "observation_date"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    farm_id: Mapped[str] = mapped_column(ForeignKey("farms.id", ondelete="CASCADE"), nullable=False, index=True)
    field_id: Mapped[str | None] = mapped_column(ForeignKey("farm_fields.id", ondelete="SET NULL"), nullable=True, index=True)
    observation_date: Mapped[date] = mapped_column(Date, nullable=False)
    soil_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    drainage_observation: Mapped[str | None] = mapped_column(String(500), nullable=True)
    erosion_observation: Mapped[str | None] = mapped_column(String(500), nullable=True)
    management_practices: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification: Mapped[str] = mapped_column(String(24), default="farmer_reported", server_default="farmer_reported", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    farm: Mapped[Farm] = relationship(back_populates="soil_observations")


class SoilTestRecord(Base):
    """Farmer-entered transcription of optional soil-test measurements."""
    __tablename__ = "soil_test_records"
    __table_args__ = (
        CheckConstraint("ph_value IS NULL OR (ph_value >= 0 AND ph_value <= 14)", name="ck_soil_test_ph_range"),
        CheckConstraint("nitrogen_value IS NULL OR nitrogen_value >= 0", name="ck_soil_test_nitrogen_nonnegative"),
        CheckConstraint("phosphorus_value IS NULL OR phosphorus_value >= 0", name="ck_soil_test_phosphorus_nonnegative"),
        CheckConstraint("potassium_value IS NULL OR potassium_value >= 0", name="ck_soil_test_potassium_nonnegative"),
        CheckConstraint("organic_matter_value IS NULL OR organic_matter_value >= 0", name="ck_soil_test_organic_matter_nonnegative"),
        CheckConstraint("(nitrogen_value IS NULL) = (nitrogen_unit IS NULL)", name="ck_soil_test_nitrogen_pair"),
        CheckConstraint("(phosphorus_value IS NULL) = (phosphorus_unit IS NULL)", name="ck_soil_test_phosphorus_pair"),
        CheckConstraint("(potassium_value IS NULL) = (potassium_unit IS NULL)", name="ck_soil_test_potassium_pair"),
        CheckConstraint("(organic_matter_value IS NULL) = (organic_matter_unit IS NULL)", name="ck_soil_test_organic_matter_pair"),
        CheckConstraint("nitrogen_unit IS NULL OR nitrogen_unit IN ('mg/kg', 'g/kg', 'cmol/kg', '%')", name="ck_soil_test_nitrogen_unit"),
        CheckConstraint("phosphorus_unit IS NULL OR phosphorus_unit IN ('mg/kg', 'g/kg', 'cmol/kg', '%')", name="ck_soil_test_phosphorus_unit"),
        CheckConstraint("potassium_unit IS NULL OR potassium_unit IN ('mg/kg', 'g/kg', 'cmol/kg', '%')", name="ck_soil_test_potassium_unit"),
        CheckConstraint("organic_matter_unit IS NULL OR organic_matter_unit IN ('g/kg', '%')", name="ck_soil_test_organic_matter_unit"),
        CheckConstraint("verification = 'farmer_reported'", name="ck_soil_test_verification"),
        Index("ix_soil_test_records_farm_date", "farm_id", "test_date"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    farm_id: Mapped[str] = mapped_column(ForeignKey("farms.id", ondelete="CASCADE"), nullable=False, index=True)
    field_id: Mapped[str | None] = mapped_column(ForeignKey("farm_fields.id", ondelete="SET NULL"), nullable=True, index=True)
    test_date: Mapped[date] = mapped_column(Date, nullable=False)
    ph_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    nitrogen_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    nitrogen_unit: Mapped[str | None] = mapped_column(String(12), nullable=True)
    phosphorus_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    phosphorus_unit: Mapped[str | None] = mapped_column(String(12), nullable=True)
    potassium_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    potassium_unit: Mapped[str | None] = mapped_column(String(12), nullable=True)
    organic_matter_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    organic_matter_unit: Mapped[str | None] = mapped_column(String(12), nullable=True)
    laboratory_name: Mapped[str | None] = mapped_column(String(240), nullable=True)
    report_reference: Mapped[str | None] = mapped_column(String(240), nullable=True)
    source_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification: Mapped[str] = mapped_column(String(24), default="farmer_reported", server_default="farmer_reported", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    farm: Mapped[Farm] = relationship(back_populates="soil_tests")


class CropHealthCase(Base):
    """Private farmer crop-health report; photos are normalized and stored in the database."""
    __tablename__ = "crop_health_cases"
    __table_args__ = (
        CheckConstraint("status IN ('submitted', 'under_review', 'awaiting_farmer', 'resolved')", name="ck_crop_health_case_status"),
        CheckConstraint("diagnosis_status IN ('unresolved', 'provisional_observation')", name="ck_crop_health_diagnosis_status"),
        Index("ix_crop_health_case_owner_created", "farmer_id", "created_at"),
        Index("ix_crop_health_case_farm_status", "farm_id", "status"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    farmer_id: Mapped[str] = mapped_column(ForeignKey("farmers.id", ondelete="CASCADE"), index=True)
    farm_id: Mapped[str] = mapped_column(ForeignKey("farms.id", ondelete="CASCADE"), index=True)
    field_id: Mapped[str | None] = mapped_column(ForeignKey("farm_fields.id", ondelete="SET NULL"), nullable=True, index=True)
    crop_plan_id: Mapped[str | None] = mapped_column(ForeignKey("crop_plans.id", ondelete="SET NULL"), nullable=True, index=True)
    crop: Mapped[str] = mapped_column(String(80))
    symptoms: Mapped[str] = mapped_column(Text)
    observed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    plant_parts_affected: Mapped[str | None] = mapped_column(Text, nullable=True)
    spreading: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    ai_screening_status: Mapped[str] = mapped_column(String(32), default="not_run", server_default="not_run")
    ai_screening_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_model_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    ai_model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ai_screened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="submitted", server_default="submitted")
    diagnosis_status: Mapped[str] = mapped_column(String(32), default="unresolved", server_default="unresolved")
    photo_data: Mapped[bytes] = mapped_column(LargeBinary)
    photo_sha256: Mapped[str] = mapped_column(String(64))
    photo_size_bytes: Mapped[int] = mapped_column(Integer)
    photo_width: Mapped[int] = mapped_column(Integer)
    photo_height: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class CropHealthCaseUpdate(Base):
    """Private farmer/reviewer case conversation and lifecycle audit entry."""
    __tablename__ = "crop_health_case_updates"
    __table_args__ = (Index("ix_crop_health_update_case_created", "case_id", "created_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    case_id: Mapped[str] = mapped_column(ForeignKey("crop_health_cases.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[str | None] = mapped_column(ForeignKey("farmers.id", ondelete="SET NULL"), nullable=True, index=True)
    update_type: Mapped[str] = mapped_column(String(32))
    assessment: Mapped[str | None] = mapped_column(String(32), nullable=True)
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
