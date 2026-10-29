"""Authenticated owner-scoped API for farmer profiles and farm records."""
import json
import os
import math
import hmac
import hashlib
import secrets
import logging
import warnings
from io import BytesIO
from hashlib import sha256
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from itertools import count
from uuid import uuid4
from urllib.parse import urlencode, urlsplit, urlunsplit

import jwt
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageOps, UnidentifiedImageError
from pwdlib import PasswordHash
from starlette.types import ASGIApp, Receive, Scope, Send
from sqlalchemy import func, or_, select, text, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from .db import Base, get_db, get_engine
from . import models
from . import account_mail
from .crop_disease_model import screen_crop_image
from .crop_health_guidance import attach_guidance
from .runtime_config import _cookie_secure, _secret, validate_runtime_config
from .schemas import (ActivityCreate, ActivityOut, ActivityUpdate, Credentials, LoginCredentials, EmailChangeRequest, AccountActionTokenInput,
                      PasswordRecoveryRequest, PasswordResetRequest, AccountDeletionRequest, FarmCreate, FarmOut, FarmUpdate,
                      FarmerOut, PlanCreate, PlanOut, PlanUpdate, PlanStatusUpdate, FieldCreate, FieldOut, TokenResponse, AccountStatusUpdate,
                      AdminFarmerOut, ReviewerDistrictsUpdate, ReviewDecisionInput,
                      FarmerRoleUpdate, ReasonInput, FarmerPermissionsUpdate,
                      PrivateMessageCreate, PrivateConversationCreate, PrivateMessagesRead, MessagingSettingUpdate,
                      WeatherForecastRequest, WeatherAlertPreferenceUpdate, WeatherAlertStatusUpdate,
                      CropRecommendationRequest, StreamlitHandoffInput, StreamlitHandoffOut,
                      CropHealthFarmerReply, CropHealthReviewerUpdate, HarvestCreate, HarvestOut,
                      HarvestObservationCreate, HarvestObservationOut, IrrigationRecordCreate,
                      IrrigationRecordOut, SoilObservationCreate, SoilObservationOut,
                      SoilTestRecordCreate, SoilTestRecordOut, FarmTimelineEntryOut, FarmTimelineOut)
from .schemas import AgronomyReviewerAuthorizationUpdate, AgronomyRuleProposalCreate, AgronomyRuleDecisionInput
from knowledge import CROPS
from utils.weather import get_forecast, RWANDA_BOUNDS
from utils.weather_bulletins import bulletin_metadata
from utils.data_loader import load_data
from utils import recommender as crop_recommender
from utils.harvest import yield_calculation, yield_kg_per_hectare


MAX_REQUEST_BODY_BYTES = 8 * 1024 * 1024


class RequestBodyLimitMiddleware:
    """Bound request buffering before FastAPI parses JSON, forms, or uploads."""

    def __init__(self, app: ASGIApp, max_body_bytes: int = MAX_REQUEST_BODY_BYTES):
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers", []))
        declared_length = headers.get(b"content-length")
        if declared_length:
            try:
                if int(declared_length) > self.max_body_bytes:
                    await JSONResponse(status_code=413, content={"detail": "Request body is too large."})(scope, receive, send)
                    return
            except ValueError:
                await JSONResponse(status_code=400, content={"detail": "Invalid request body length."})(scope, receive, send)
                return

        messages = []
        total_bytes = 0
        while True:
            message = await receive()
            messages.append(message)
            if message["type"] == "http.request":
                total_bytes += len(message.get("body", b""))
                if total_bytes > self.max_body_bytes:
                    await JSONResponse(status_code=413, content={"detail": "Request body is too large."})(scope, receive, send)
                    return
                if not message.get("more_body", False):
                    break
            elif message["type"] == "http.disconnect":
                break

        async def replay_receive():
            if messages:
                return messages.pop(0)
            return await receive()

        await self.app(scope, replay_receive, send)


password_hash = PasswordHash.recommended()
_dummy_hash = password_hash.hash("constant dummy password for timing equalization")
bearer = HTTPBearer(auto_error=False)
PRIVACY_NOTICE_VERSION = "phase1-2026-10-weather-storage"
MAX_CROP_HEALTH_PHOTO_BYTES = 5 * 1024 * 1024
MAX_CROP_HEALTH_PHOTO_PIXELS = 12_000_000
MAX_CROP_HEALTH_PHOTO_DIMENSION = 4096
_rate_prune_counter = count(1)
PLAN_STATUS_TRANSITIONS = {
    "draft": {"planned", "cancelled"},
    "planned": {"planted", "cancelled"},
    "planted": {"monitoring"},
    "monitoring": {"harvesting"},
    "harvesting": {"completed"},
    "completed": set(),
    "cancelled": set(),
}


def _rate_bucket(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _check_rate_bucket(db: Session, key: str, limit: int, window: timedelta):
    now = datetime.now(timezone.utc)
    cutoff = now - window
    bucket_hash = _rate_bucket(key)
    recent = db.scalar(select(func.count()).select_from(models.AuthAttempt).where(
        models.AuthAttempt.bucket_hash == bucket_hash, models.AuthAttempt.created_at >= cutoff)) or 0
    if recent >= limit:
        raise HTTPException(status_code=429, detail="Too many authentication attempts. Wait before trying again.",
                            headers={"Retry-After": str(int(window.total_seconds()))})
    db.add(models.AuthAttempt(bucket_hash=bucket_hash, created_at=now))


def _record_failed_login(request: Request, email: str, db: Session):
    ip = request.client.host if request.client else "unknown"
    window = timedelta(minutes=15)
    _check_rate_bucket(db, f"login-ip:{ip}", 40, window)
    _check_rate_bucket(db, f"login-address:{ip}:{email.lower()}", 8, window)
    db.commit()
    if next(_rate_prune_counter) % 100 == 0:
        db.query(models.AuthAttempt).filter(models.AuthAttempt.created_at < datetime.now(timezone.utc) - timedelta(days=1)).delete(synchronize_session=False)
        db.commit()


def _record_registration_attempt(request: Request, db: Session):
    ip = request.client.host if request.client else "unknown"
    _check_rate_bucket(db, f"registration-ip:{ip}", 5, timedelta(hours=1))
    db.commit()
    if next(_rate_prune_counter) % 100 == 0:
        db.query(models.AuthAttempt).filter(models.AuthAttempt.created_at < datetime.now(timezone.utc) - timedelta(days=1)).delete(synchronize_session=False)
        db.commit()


@asynccontextmanager
async def lifespan(_app):
    # Authentication endpoints must not start in a state where CSRF/JWT signing fails at request time.
    validate_runtime_config()
    # Development convenience only. Deployments must apply Alembic migrations.
    if os.environ.get("CROP_PULSE_AUTO_CREATE_SCHEMA") == "1":
        Base.metadata.create_all(get_engine())
    yield


app = FastAPI(title="CropPulse Rwanda Farmer Records API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.environ.get("CROP_PULSE_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
)
app.add_middleware(RequestBodyLimitMiddleware)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.url.path.startswith("/v1/"):
        response.headers["Cache-Control"] = "no-store"
    if _cookie_secure() and request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


def _check_csrf(request: Request):
    cookie_token = request.cookies.get("cp_csrf", "")
    header_token = request.headers.get("X-CSRF-Token", "")
    nonce, separator, supplied_signature = cookie_token.partition(".")
    expected_signature = hmac.new(_secret().encode(), nonce.encode(), "sha256").hexdigest() if nonce and separator else ""
    if (not cookie_token or not header_token or not nonce or not separator or not supplied_signature
            or not hmac.compare_digest(cookie_token, header_token)
            or not hmac.compare_digest(expected_signature, supplied_signature)):
        raise HTTPException(status_code=403, detail="Request security check failed. Refresh the page and try again.")


def _set_browser_session(response: Response, token: str):
    response.set_cookie("cp_session", token, max_age=1800, httponly=True, secure=_cookie_secure(),
                        samesite="lax", path="/")


@app.exception_handler(RequestValidationError)
async def safe_validation_error(_: Request, exc: RequestValidationError):
    # Pydantic's default errors can echo the submitted input; never reflect passwords or notes.
    errors = [{"loc": list(error.get("loc", ())), "msg": error.get("msg", "Invalid value"),
               "type": error.get("type", "value_error")} for error in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errors})


@app.exception_handler(SQLAlchemyError)
async def safe_database_error(_: Request, _exc: SQLAlchemyError):
    # Avoid returning connection strings, SQL, farmer data, or driver traces to clients.
    return JSONResponse(status_code=503, content={"detail": "Record service is temporarily unavailable."})


@app.get("/health")
def health():
    # Readiness probe: reports healthy only if the configured database is reachable.
    with get_engine().connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok"}


def _issue_token(farmer_id: str, db: Session) -> str:
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=30)
    session_id = str(uuid4())
    db.add(models.FarmerSession(id=session_id, farmer_id=farmer_id, expires_at=expires))
    db.commit()
    return jwt.encode({"sub": farmer_id, "jti": session_id, "iat": now, "exp": expires}, _secret(), algorithm="HS256")


def current_farmer(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)):
    from_bearer = credentials is not None
    token = credentials.credentials if from_bearer else request.cookies.get("cp_session")
    if not token:
        raise HTTPException(status_code=401, detail="Sign in to access farmer records.", headers={"WWW-Authenticate": "Bearer"})
    if not from_bearer and request.method not in {"GET", "HEAD", "OPTIONS"}:
        _check_csrf(request)
    try:
        claims = jwt.decode(token, _secret(), algorithms=["HS256"])
        farmer_id = claims.get("sub")
        session_id = claims.get("jti")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Session expired or invalid. Sign in again.", headers={"WWW-Authenticate": "Bearer"})
    session_record = db.get(models.FarmerSession, session_id) if session_id else None
    expires_at = session_record.expires_at if session_record else None
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if (session_record is None or session_record.farmer_id != farmer_id or
            session_record.revoked_at is not None or expires_at <= datetime.now(timezone.utc)):
        raise HTTPException(status_code=401, detail="Session expired or signed out. Sign in again.", headers={"WWW-Authenticate": "Bearer"})
    farmer = db.get(models.Farmer, farmer_id)
    if farmer is None:
        raise HTTPException(status_code=401, detail="Account is unavailable. Sign in again.")
    if farmer.status != "active":
        raise HTTPException(status_code=403, detail="This account is suspended. Contact CropPulse support.")
    return farmer


def _streamlit_base_url() -> str:
    configured = os.environ.get("CROP_PULSE_STREAMLIT_URL", "").strip()
    environment = os.environ.get("CROP_PULSE_ENVIRONMENT", "development").strip().lower()
    if not configured and environment not in {"production", "prod"}:
        configured = "http://127.0.0.1:8501"
    try:
        parts = urlsplit(configured)
        if (parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password
                or parts.query or parts.fragment):
            raise ValueError
        if environment in {"production", "prod"} and parts.scheme != "https":
            raise ValueError
    except ValueError:
        raise HTTPException(status_code=503, detail="The CropPulse planning workspace is not configured safely.") from None
    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))


def _react_base_url() -> str:
    configured = os.environ.get("CROP_PULSE_REACT_URL", "").strip()
    environment = os.environ.get("CROP_PULSE_ENVIRONMENT", "development").strip().lower()
    if not configured and environment not in {"production", "prod"}:
        configured = "http://127.0.0.1:5173"
    try:
        parts = urlsplit(configured)
        if (parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password
                or parts.query or parts.fragment):
            raise ValueError
        if environment in {"production", "prod"} and parts.scheme != "https":
            raise ValueError
    except ValueError:
        raise HTTPException(status_code=503, detail="The CropPulse React workspace is not configured safely.") from None
    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))


def _new_handoff(db: Session, farmer: models.Farmer) -> str:
    now = datetime.now(timezone.utc)
    db.query(models.StreamlitHandoff).filter(models.StreamlitHandoff.expires_at < now).delete(synchronize_session=False)
    raw_code = secrets.token_urlsafe(48)
    db.add(models.StreamlitHandoff(farmer_id=farmer.id, code_hash=sha256(raw_code.encode()).hexdigest(),
                                   expires_at=now + timedelta(minutes=5), created_at=now))
    db.commit()
    return raw_code


@app.post("/v1/browser-auth/streamlit-handoff", response_model=StreamlitHandoffOut)
def create_streamlit_handoff(farmer: models.Farmer = Depends(current_farmer), db: Session = Depends(get_db)):
    base_url = _streamlit_base_url()
    raw_code = _new_handoff(db, farmer)
    parts = urlsplit(base_url)
    redirect_url = urlunsplit((parts.scheme, parts.netloc, f"{parts.path}/", urlencode({"cp_handoff": raw_code}), ""))
    return StreamlitHandoffOut(redirect_url=redirect_url)


@app.post("/v1/streamlit/react-handoff", response_model=StreamlitHandoffOut)
def create_react_handoff(farmer: models.Farmer = Depends(current_farmer), db: Session = Depends(get_db)):
    """Create a one-use browser code so an authenticated Streamlit session can return to React."""
    base_url = _react_base_url()
    raw_code = _new_handoff(db, farmer)
    parts = urlsplit(base_url)
    path = f"{parts.path.rstrip('/')}/overview"
    redirect_url = urlunsplit((parts.scheme, parts.netloc, path, urlencode({"cp_handoff": raw_code}), ""))
    return StreamlitHandoffOut(redirect_url=redirect_url)


@app.post("/v1/streamlit/handoff/exchange", response_model=TokenResponse)
def exchange_streamlit_handoff(body: StreamlitHandoffInput, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    code_hash = sha256(body.code.encode()).hexdigest()
    handoff = db.scalar(select(models.StreamlitHandoff).where(models.StreamlitHandoff.code_hash == code_hash))
    if handoff is None:
        raise HTTPException(status_code=401, detail="This sign-in link is invalid or expired. Return to CropPulse and try again.")
    # Conditional update makes a valid code single-use even when two requests race.
    claimed = db.execute(update(models.StreamlitHandoff).where(
        models.StreamlitHandoff.id == handoff.id,
        models.StreamlitHandoff.used_at.is_(None),
        models.StreamlitHandoff.expires_at > now,
    ).values(used_at=now).execution_options(synchronize_session=False))
    if claimed.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=401, detail="This sign-in link is invalid or expired. Return to CropPulse and try again.")
    farmer = db.get(models.Farmer, handoff.farmer_id)
    if farmer is None or farmer.status != "active":
        db.commit()
        raise HTTPException(status_code=401, detail="This sign-in link is invalid or expired. Return to CropPulse and try again.")
    db.commit()
    return TokenResponse(access_token=_issue_token(farmer.id, db))


@app.post("/v1/browser-auth/react-handoff/exchange", response_model=FarmerOut)
def exchange_react_handoff(body: StreamlitHandoffInput, request: Request, response: Response,
                           db: Session = Depends(get_db)):
    """Consume a Streamlit handoff in the browser and establish React's HttpOnly session."""
    _check_csrf(request)
    now = datetime.now(timezone.utc)
    code_hash = sha256(body.code.encode()).hexdigest()
    handoff = db.scalar(select(models.StreamlitHandoff).where(models.StreamlitHandoff.code_hash == code_hash))
    if handoff is None:
        raise HTTPException(status_code=401, detail="This sign-in link is invalid or expired. Return to CropPulse and try again.")
    claimed = db.execute(update(models.StreamlitHandoff).where(
        models.StreamlitHandoff.id == handoff.id,
        models.StreamlitHandoff.used_at.is_(None),
        models.StreamlitHandoff.expires_at > now,
    ).values(used_at=now).execution_options(synchronize_session=False))
    if claimed.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=401, detail="This sign-in link is invalid or expired. Return to CropPulse and try again.")
    farmer = db.get(models.Farmer, handoff.farmer_id)
    if farmer is None or farmer.status != "active":
        db.commit()
        raise HTTPException(status_code=401, detail="This sign-in link is invalid or expired. Return to CropPulse and try again.")
    db.commit()
    token = _issue_token(farmer.id, db)
    _set_browser_session(response, token)
    return FarmerOut.model_validate(farmer)


def require_admin(farmer: models.Farmer = Depends(current_farmer)):
    if farmer.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    return farmer


def require_reviewer(farmer: models.Farmer = Depends(current_farmer)):
    if farmer.role not in {"reviewer", "admin"}:
        raise HTTPException(status_code=403, detail="Reviewer access is required.")
    return farmer


def _has_agronomy_review_authorization(db: Session, farmer: models.Farmer) -> bool:
    if farmer.status != "active" or farmer.role not in {"reviewer", "admin"}:
        return False
    latest = db.scalar(select(models.AgronomyReviewAuthorizationEvent)
                       .where(models.AgronomyReviewAuthorizationEvent.reviewer_id == farmer.id)
                       .order_by(models.AgronomyReviewAuthorizationEvent.created_at.desc(),
                                 models.AgronomyReviewAuthorizationEvent.id.desc()).limit(1))
    return latest is not None and latest.action == "grant"


def require_agronomy_reviewer(db: Session = Depends(get_db), farmer: models.Farmer = Depends(current_farmer)):
    if not _has_agronomy_review_authorization(db, farmer):
        raise HTTPException(status_code=403, detail="Explicit agronomic rule-review authorization is required.")
    return farmer


@app.get("/v1/agronomy/review-access")
def agronomy_review_access(db: Session = Depends(get_db), farmer: models.Farmer = Depends(current_farmer)):
    return {"authorized": _has_agronomy_review_authorization(db, farmer),
            "role_eligible": farmer.status == "active" and farmer.role in {"reviewer", "admin"}}


@app.post("/v1/weather/forecast")
def weather_forecast(body: WeatherForecastRequest, db: Session = Depends(get_db),
                     actor: models.Farmer = Depends(current_farmer)):
    """Return and, with explicit request consent, persist the latest forecast for this account/location."""
    if not body.save_to_account:
        raise HTTPException(status_code=422, detail="Confirm that you want to save this forecast and its coordinates to your CropPulse account.")
    field = None
    farm = None
    if body.field_id is not None:
        row = db.execute(select(models.FarmField, models.Farm).join(
            models.Farm, models.Farm.id == models.FarmField.farm_id
        ).where(models.FarmField.id == body.field_id,
                models.Farm.owner_id == actor.id,
                models.FarmField.archived_at.is_(None))).first()
        if row is None:
            raise HTTPException(status_code=404, detail="Field was not found.")
        field, farm = row
        if field.latitude is None or field.longitude is None:
            raise HTTPException(status_code=422, detail="The selected field has no saved coordinates.")
        if round(field.latitude, 4) != round(body.latitude, 4) or round(field.longitude, 4) != round(body.longitude, 4):
            raise HTTPException(status_code=409, detail="The submitted coordinates do not match the selected field's saved coordinates.")
    result = get_forecast(body.latitude, body.longitude)
    if result.get("status") not in {"available", "stale"} or not result.get("daily_forecast"):
        return {**result, "stored": False}

    latitude = round(float(body.latitude), 4)
    longitude = round(float(body.longitude), 4)
    retrieved_at = datetime.fromisoformat(result["retrieved_at"])
    if retrieved_at.tzinfo is None:
        retrieved_at = retrieved_at.replace(tzinfo=timezone.utc)
    location_values = {
        "field_id": field.id if field else None,
        "farm_name_snapshot": farm.name if farm else None,
        "field_name_snapshot": field.name if field else None,
        "location_source": body.location_source,
    }
    result = {**result, "location_context": {
        "association": "owned_field_record" if field else "coordinate_only",
        "location_source": body.location_source,
        "field_id": field.id if field else None,
        "farm_name": farm.name if farm else None,
        "field_name": field.name if field else None,
        "geographic_verification": "not_independently_verified",
        "message": "Coordinates match this account's saved field record; CropPulse has not independently verified the farm boundary or the accuracy of the saved point." if field else "Coordinate-based forecast; no farm or field association was verified.",
    }}
    record = db.scalar(select(models.SavedWeatherForecast).where(
        models.SavedWeatherForecast.farmer_id == actor.id,
        models.SavedWeatherForecast.latitude == latitude,
        models.SavedWeatherForecast.longitude == longitude,
    ))
    stored_this_result = True
    if record is None:
        record = models.SavedWeatherForecast(
            farmer_id=actor.id, latitude=latitude, longitude=longitude,
            status=result["status"], retrieved_at=retrieved_at,
            forecast_json=json.dumps(result, ensure_ascii=False, allow_nan=False),
            **location_values,
        )
        db.add(record)
        db.flush()
    else:
        previous_retrieved_at = record.retrieved_at
        if previous_retrieved_at.tzinfo is None:
            previous_retrieved_at = previous_retrieved_at.replace(tzinfo=timezone.utc)
        if retrieved_at > previous_retrieved_at:
            record.status = result["status"]
            record.retrieved_at = retrieved_at
            record.forecast_json = json.dumps(result, ensure_ascii=False, allow_nan=False)
            for key, value in location_values.items():
                setattr(record, key, value)
        elif retrieved_at == previous_retrieved_at and result["status"] == "stale":
            # Keep the original provider retrieval time while recording that
            # this response came from the stale fallback cache.
            record.status = "stale"
            record.forecast_json = json.dumps(result, ensure_ascii=False, allow_nan=False)
            for key, value in location_values.items():
                setattr(record, key, value)
        elif retrieved_at == previous_retrieved_at:
            for key, value in location_values.items():
                setattr(record, key, value)
            record.forecast_json = json.dumps(result, ensure_ascii=False, allow_nan=False)
        elif retrieved_at < previous_retrieved_at:
            stored_this_result = False
    db.commit()
    return {**result, "stored": stored_this_result,
            **({"record_id": record.id} if stored_this_result else {})}


@app.get("/v1/weather/forecasts")
def list_saved_weather_forecasts(db: Session = Depends(get_db), actor: models.Farmer = Depends(current_farmer)):
    """List the signed-in user's latest saved forecast for each coordinate point."""
    rows = db.scalars(select(models.SavedWeatherForecast).where(
        models.SavedWeatherForecast.farmer_id == actor.id
    ).order_by(models.SavedWeatherForecast.retrieved_at.desc()).limit(50)).all()
    items = []
    for row in rows:
        retrieved_at = row.retrieved_at
        if retrieved_at.tzinfo is None:
            retrieved_at = retrieved_at.replace(tzinfo=timezone.utc)
        items.append({
            "id": row.id,
            "field_id": row.field_id,
            "farm_name": row.farm_name_snapshot,
            "field_name": row.field_name_snapshot,
            "requested_coordinates": {"latitude": row.latitude, "longitude": row.longitude},
            "status": row.status,
            "retrieved_at": retrieved_at.isoformat(),
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            "location_context": json.loads(row.forecast_json).get("location_context", {
                "association": "coordinate_only", "location_source": row.location_source,
                "field_id": row.field_id, "farm_name": row.farm_name_snapshot,
                "field_name": row.field_name_snapshot, "geographic_verification": "not_independently_verified",
            }),
            "forecast": json.loads(row.forecast_json),
        })
    return {"items": items, "total": len(items)}


@app.get("/v1/weather/alert-preferences")
def list_weather_alert_preferences(db: Session = Depends(get_db), actor: models.Farmer = Depends(current_farmer)):
    """Return this farmer's field choices and their explicit alert opt-ins."""
    rows = db.execute(select(models.FarmField, models.Farm).join(
        models.Farm, models.Farm.id == models.FarmField.farm_id
    ).where(models.Farm.owner_id == actor.id, models.FarmField.archived_at.is_(None))
      .order_by(models.Farm.created_at, models.FarmField.created_at)).all()
    preferences = {p.field_id: p for p in db.scalars(select(models.WeatherAlertPreference).where(
        models.WeatherAlertPreference.farmer_id == actor.id))}
    south, north, west, east = RWANDA_BOUNDS
    items = []
    for field, farm in rows:
        in_supported_extent = (field.latitude is not None and field.longitude is not None
                               and south <= field.latitude <= north and west <= field.longitude <= east)
        preference = preferences.get(field.id)
        items.append({
            "field_id": field.id, "farm_id": farm.id, "farm_name": farm.name,
            "field_name": field.name, "has_coordinates": field.latitude is not None,
            "within_supported_extent": in_supported_extent,
            "enabled": bool(preference and preference.enabled),
        })
    from utils.weather_alert_rules import active_weather_rules
    return {"items": items, "active_rules": active_weather_rules(),
            "notice": "Preferences are off by default. No agricultural weather rules are currently approved or generating alerts."}


@app.put("/v1/weather/alert-preferences/{field_id}")
def update_weather_alert_preference(field_id: str, body: WeatherAlertPreferenceUpdate,
                                    db: Session = Depends(get_db), actor: models.Farmer = Depends(current_farmer)):
    row = db.execute(select(models.FarmField, models.Farm).join(
        models.Farm, models.Farm.id == models.FarmField.farm_id
    ).where(models.FarmField.id == field_id, models.Farm.owner_id == actor.id,
            models.FarmField.archived_at.is_(None))).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Field was not found.")
    field, _farm = row
    if body.enabled:
        south, north, west, east = RWANDA_BOUNDS
        if field.latitude is None or field.longitude is None:
            raise HTTPException(status_code=422, detail="Save coordinates for this field before opting it in.")
        if not (south <= field.latitude <= north and west <= field.longitude <= east):
            raise HTTPException(status_code=422, detail="This field is outside the weather service's supported coordinate extent.")
    preference = db.scalar(select(models.WeatherAlertPreference).where(
        models.WeatherAlertPreference.farmer_id == actor.id,
        models.WeatherAlertPreference.field_id == field.id,
    ))
    if preference is None:
        preference = models.WeatherAlertPreference(farmer_id=actor.id, field_id=field.id, enabled=body.enabled)
        db.add(preference)
    else:
        preference.enabled = body.enabled
    db.commit()
    return {"field_id": field.id, "farm_id": field.farm_id, "enabled": preference.enabled,
            "active_rules": [], "notice": "No approved agricultural weather rule is active. This preference does not create or schedule alerts."}


def _weather_alert_payload(row: models.WeatherAlert, now: datetime):
    expires_at = row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    display_status = "expired" if row.status == "active" and expires_at <= now else row.status
    try:
        evidence_snapshot = json.loads(row.evidence_snapshot_json)
        if not isinstance(evidence_snapshot, dict):
            evidence_snapshot = {}
    except (TypeError, ValueError):
        evidence_snapshot = {}
    return {
        "id": row.id, "farm_id": row.farm_id, "field_id": row.field_id, "forecast_id": row.forecast_id,
        "farm_name": row.farm_name_snapshot, "field_name": row.field_name_snapshot,
        "alert_type": row.alert_type, "rule_id": row.rule_id, "rule_version": row.rule_version,
        "weather_source": row.weather_source,
        "forecast_retrieved_at": row.forecast_retrieved_at.isoformat(),
        "valid_from": row.valid_from.isoformat(), "valid_to": row.valid_to.isoformat(),
        "reason": row.reason, "evidence_status": row.evidence_status,
        "evidence_snapshot": evidence_snapshot,
        "approval_status": row.approval_status, "status": display_status,
        "created_at": row.created_at.isoformat(), "expires_at": expires_at.isoformat(),
        "acknowledged_at": row.acknowledged_at.isoformat() if row.acknowledged_at else None,
        "dismissed_at": row.dismissed_at.isoformat() if row.dismissed_at else None,
    }


@app.get("/v1/weather/alerts")
def list_weather_alerts(db: Session = Depends(get_db), actor: models.Farmer = Depends(current_farmer)):
    """List only this farmer's retained in-app alert history."""
    now = datetime.now(timezone.utc)
    rows = db.scalars(select(models.WeatherAlert).where(
        models.WeatherAlert.recipient_id == actor.id
    ).order_by(models.WeatherAlert.created_at.desc()).limit(100)).all()
    return {"items": [_weather_alert_payload(row, now) for row in rows], "total": len(rows)}


@app.patch("/v1/weather/alerts/{alert_id}/status")
def update_weather_alert_status(alert_id: str, body: WeatherAlertStatusUpdate,
                                db: Session = Depends(get_db), actor: models.Farmer = Depends(current_farmer)):
    row = db.scalar(select(models.WeatherAlert).where(
        models.WeatherAlert.id == alert_id, models.WeatherAlert.recipient_id == actor.id,
    ))
    if row is None:
        raise HTTPException(status_code=404, detail="Weather alert was not found.")
    now = datetime.now(timezone.utc)
    expires_at = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        raise HTTPException(status_code=409, detail="This alert has expired and can no longer be changed.")
    if row.status != "active":
        raise HTTPException(status_code=409, detail="This alert has already been acknowledged or dismissed.")
    row.status = body.status
    if body.status == "acknowledged":
        row.acknowledged_at = now
    else:
        row.dismissed_at = now
    db.commit()
    db.refresh(row)
    return _weather_alert_payload(row, now)


@app.get("/v1/weather/bulletins")
def list_weather_bulletins(db: Session = Depends(get_db), actor: models.Farmer = Depends(current_farmer)):
    """List source bulletins and their issue/valid dates."""
    rows = db.scalars(select(models.WeatherBulletin).order_by(
        models.WeatherBulletin.issued_at.desc(), models.WeatherBulletin.title.asc())).all()
    return {"items": [bulletin_metadata(row) for row in rows], "total": len(rows),
            "notice": "Publisher bulletins are forecasts/outlooks, not farm-level observations. Check issue and valid dates."}


@app.get("/v1/weather/climate-data")
def list_weather_climate_data(year: int | None = None, record_type: str | None = None,
                              search: str | None = None, db: Session = Depends(get_db),
                              actor: models.Farmer = Depends(current_farmer)):
    """Return curated, source-linked rainfall outlook statements from the PDFs."""
    if year is not None and not 1900 <= year <= 2200:
        raise HTTPException(status_code=422, detail="Choose a valid publication period year.")
    if record_type is not None and record_type not in {"monthly_outlook", "seasonal_outlook"}:
        raise HTTPException(status_code=422, detail="Choose monthly or seasonal outlook records.")
    if search is not None and len(search.strip()) > 80:
        raise HTTPException(status_code=422, detail="Search text must be 80 characters or fewer.")
    query = select(models.WeatherBulletinRecord, models.WeatherBulletin).join(
        models.WeatherBulletin, models.WeatherBulletin.id == models.WeatherBulletinRecord.bulletin_id)
    if year is not None:
        query = query.where(models.WeatherBulletinRecord.valid_from >= date(year, 1, 1),
                            models.WeatherBulletinRecord.valid_from < date(year + 1, 1, 1))
    if record_type is not None:
        query = query.where(models.WeatherBulletinRecord.record_type == record_type)
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.where(or_(models.WeatherBulletinRecord.geography_label.ilike(term),
                                models.WeatherBulletinRecord.source_text.ilike(term),
                                models.WeatherBulletinRecord.period_label.ilike(term)))
    rows = db.execute(query.order_by(models.WeatherBulletinRecord.valid_from,
                                     models.WeatherBulletinRecord.period_label,
                                     models.WeatherBulletinRecord.geography_label)).all()
    today = date.today()
    items = []
    for record, bulletin in rows:
        items.append({
            "id": record.id,
            "record_type": record.record_type,
            "variable": record.variable,
            "geography_type": record.geography_type,
            "geography_label": record.geography_label,
            "period_label": record.period_label,
            "valid_from": record.valid_from.isoformat(),
            "valid_to": record.valid_to.isoformat(),
            "period_status": "upcoming" if record.valid_from > today else "current" if record.valid_to >= today else "past",
            "value_min": record.value_min,
            "value_max": record.value_max,
            "unit": record.unit,
            "normal_min": record.normal_min,
            "normal_max": record.normal_max,
            "anomaly_label": record.anomaly_label,
            "source_text": record.source_text,
            "source_page": record.source_page,
            "transcription_status": record.transcription_status,
            "bulletin": {
                "id": bulletin.id,
                "title": bulletin.title,
                "issued_at": bulletin.issued_at.isoformat(),
                "source_url": bulletin.source_url,
                "document_url": f"/v1/weather/bulletins/{bulletin.id}/document",
                "sha256": bulletin.sha256,
                "provenance_status": bulletin.provenance_status,
            },
        })
    return {
        "items": items,
        "total": len(items),
        "filters": {"year": year, "record_type": record_type, "search": search},
        "notice": "These are METEO RWANDA rainfall outlook ranges transcribed from PDF text and linked to the source page. They are not farm observations or generated forecasts. Map-only district values and untranscribed bulletin details are not included.",
    }


@app.get("/v1/weather/bulletins/{bulletin_id}/document")
def get_weather_bulletin_document(bulletin_id: str, db: Session = Depends(get_db),
                                  actor: models.Farmer = Depends(current_farmer)):
    bulletin = db.get(models.WeatherBulletin, bulletin_id)
    if bulletin is None:
        raise HTTPException(status_code=404, detail="Weather bulletin was not found.")
    return Response(content=bulletin.document_bytes, media_type="application/pdf", headers={
        "Content-Disposition": f'inline; filename="weather-bulletin-{bulletin.id}.pdf"',
        "ETag": f'"{bulletin.sha256}"',
        "Cache-Control": "private, max-age=3600",
    })


def _messaging_is_enabled(db: Session) -> bool:
    setting = db.get(models.MessagingSetting, 1)
    return bool(setting and setting.farmer_reviewer_enabled)


def _require_messaging_enabled(db: Session):
    if not _messaging_is_enabled(db):
        raise HTTPException(status_code=403, detail="Private messaging is disabled by the administrator.")


def _pair_is_currently_eligible(db: Session, farmer_id: str, reviewer_id: str) -> bool:
    farmer = db.get(models.Farmer, farmer_id)
    reviewer = db.get(models.Farmer, reviewer_id)
    if not farmer or not reviewer or farmer.role != "farmer" or farmer.status != "active" or reviewer.status != "active" or reviewer.role != "reviewer":
        return False
    farm_districts = set(db.scalars(select(models.Farm.district).where(models.Farm.owner_id == farmer_id)).all())
    assigned_districts = set(db.scalars(select(models.ReviewerDistrict.district).where(models.ReviewerDistrict.reviewer_id == reviewer_id)).all())
    return bool(farm_districts.intersection(assigned_districts))


def _authorize_conversation(db: Session, conversation_id: str, actor: models.Farmer):
    conversation = db.get(models.PrivateConversation, conversation_id)
    if conversation is None or actor.id not in {conversation.farmer_id, conversation.reviewer_id}:
        raise HTTPException(status_code=404, detail="Conversation was not found.")
    if not _pair_is_currently_eligible(db, conversation.farmer_id, conversation.reviewer_id):
        raise HTTPException(status_code=404, detail="Conversation is unavailable under current account and district permissions.")
    return conversation


def _conversation_summary(db: Session, conversation: models.PrivateConversation, actor: models.Farmer):
    other_id = conversation.reviewer_id if actor.id == conversation.farmer_id else conversation.farmer_id
    other = db.get(models.Farmer, other_id)
    last = db.scalar(select(models.PrivateMessage).where(
        models.PrivateMessage.conversation_id == conversation.id
    ).order_by(models.PrivateMessage.created_at.desc(), models.PrivateMessage.id.desc()).limit(1))
    unread = db.scalar(select(func.count()).select_from(models.PrivateMessage).where(
        models.PrivateMessage.conversation_id == conversation.id,
        models.PrivateMessage.sender_id != actor.id,
        models.PrivateMessage.read_at.is_(None))) or 0
    return {"id": conversation.id, "other_user_id": other.id, "other_display_name": other.display_name,
            "other_role": "CropPulse reviewer" if other.role == "reviewer" else "Farmer",
            "created_at": conversation.created_at, "last_message": last.body if last else None,
            "last_message_at": last.created_at if last else conversation.created_at,
            "unread_count": unread}


def _record_admin_event(db: Session, actor_id: str | None, target_farmer_id: str | None,
                        action: str, target_type: str, target_id: str, reason: str = ""):
    db.add(models.AdminAuditEvent(actor_id=actor_id, target_farmer_id=target_farmer_id,
                                  action=action, target_type=target_type, target_id=target_id,
                                  reason=reason, result="success"))


def _activity_review_status(db: Session, activity: models.FarmActivity) -> str:
    latest = db.scalar(select(models.ActivityReviewDecision).where(
        models.ActivityReviewDecision.activity_id == activity.id
    ).order_by(models.ActivityReviewDecision.created_at.desc()).limit(1))
    if latest is None:
        return "pending"
    reviewed_at = latest.created_at
    updated_at = activity.updated_at
    if reviewed_at.tzinfo is None:
        reviewed_at = reviewed_at.replace(tzinfo=timezone.utc)
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)
    return latest.decision if reviewed_at >= updated_at else "pending"


@app.post("/v1/auth/register", response_model=TokenResponse, status_code=201)
def register(body: Credentials, request: Request, db: Session = Depends(get_db)):
    _record_registration_attempt(request, db)
    if not body.display_name:
        raise HTTPException(422, detail="Display name is required for registration.")
    if not body.privacy_notice_accepted:
        raise HTTPException(422, detail="Review and accept the account data notice to create an account.")
    farmer = models.Farmer(email=str(body.email).lower(), display_name=body.display_name.strip(), password_hash=password_hash.hash(body.password),
                           privacy_notice_version=PRIVACY_NOTICE_VERSION, privacy_accepted_at=datetime.now(timezone.utc))
    db.add(farmer)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, detail="An account with that email already exists.")
    db.refresh(farmer)
    return TokenResponse(access_token=_issue_token(farmer.id, db))


@app.post("/v1/auth/login", response_model=TokenResponse)
def login(body: LoginCredentials, request: Request, db: Session = Depends(get_db)):
    farmer = db.scalar(select(models.Farmer).where(models.Farmer.email == str(body.email).lower()))
    # Verify exactly one Argon2 hash for both known and unknown addresses.
    valid_password = password_hash.verify(body.password, farmer.password_hash if farmer else _dummy_hash)
    if farmer is None or not valid_password:
        _record_failed_login(request, str(body.email), db)
        raise HTTPException(status_code=401, detail="Email or password is incorrect.", headers={"WWW-Authenticate": "Bearer"})
    if farmer.status != "active":
        raise HTTPException(status_code=403, detail="This account is suspended. Contact CropPulse support.")
    return TokenResponse(access_token=_issue_token(farmer.id, db))


@app.get("/v1/browser-auth/csrf")
def browser_csrf(response: Response):
    nonce = secrets.token_urlsafe(24)
    signature = hmac.new(_secret().encode(), nonce.encode(), "sha256").hexdigest()
    token = f"{nonce}.{signature}"
    response.set_cookie("cp_csrf", token, max_age=1800, httponly=False, secure=_cookie_secure(),
                        samesite="lax", path="/v1")
    return {"csrf_token": token}


@app.post("/v1/browser-auth/register", response_model=FarmerOut, status_code=201)
def browser_register(body: Credentials, request: Request, response: Response, db: Session = Depends(get_db)):
    _check_csrf(request)
    result = register(body, request, db)
    token = result.access_token
    _set_browser_session(response, token)
    claims = jwt.decode(token, _secret(), algorithms=["HS256"])
    return db.get(models.Farmer, claims["sub"])


@app.post("/v1/browser-auth/login", response_model=FarmerOut)
def browser_login(body: LoginCredentials, request: Request, response: Response, db: Session = Depends(get_db)):
    _check_csrf(request)
    result = login(body, request, db)
    _set_browser_session(response, result.access_token)
    claims = jwt.decode(result.access_token, _secret(), algorithms=["HS256"])
    return db.get(models.Farmer, claims["sub"])


@app.post("/v1/browser-auth/logout", status_code=204)
def browser_logout(request: Request, response: Response, farmer: models.Farmer = Depends(current_farmer), db: Session = Depends(get_db)):
    claims = jwt.decode(request.cookies["cp_session"], _secret(), algorithms=["HS256"])
    session_record = db.get(models.FarmerSession, claims["jti"])
    session_record.revoked_at = datetime.now(timezone.utc)
    db.commit()
    response.delete_cookie("cp_session", path="/", secure=_cookie_secure(), httponly=True, samesite="lax")
    response.delete_cookie("cp_csrf", path="/v1", secure=_cookie_secure(), httponly=False, samesite="lax")


def _account_action_attempt(request: Request, email: str, purpose: str, db: Session):
    ip = request.client.host if request.client else "unknown"
    window = timedelta(hours=1)
    _check_rate_bucket(db, f"account-action-ip:{purpose}:{ip}", 20, window)
    _check_rate_bucket(db, f"account-action-address:{purpose}:{ip}:{email.lower()}", 5, window)
    db.commit()


def _issue_account_action(db: Session, farmer: models.Farmer, purpose: str, target_email: str | None = None) -> str:
    now = datetime.now(timezone.utc)
    previous = db.scalars(select(models.AccountActionToken).where(
        models.AccountActionToken.farmer_id == farmer.id,
        models.AccountActionToken.purpose == purpose,
        models.AccountActionToken.used_at.is_(None),
    )).all()
    for row in previous:
        db.delete(row)
    raw_token = secrets.token_urlsafe(32)
    row = models.AccountActionToken(
        farmer_id=farmer.id, purpose=purpose, token_hash=sha256(raw_token.encode()).hexdigest(),
        target_email=target_email, expires_at=now + timedelta(minutes=30), created_at=now,
    )
    db.add(row)
    db.commit()
    return raw_token


def _deliver_account_action(db: Session, farmer_id: str, purpose: str, recipient: str, subject: str, path: str, token: str):
    action = db.scalar(select(models.AccountActionToken).where(
        models.AccountActionToken.farmer_id == farmer_id,
        models.AccountActionToken.purpose == purpose,
        models.AccountActionToken.token_hash == sha256(token.encode()).hexdigest(),
    ))
    try:
        url = f"{account_mail.public_app_url()}/{path}?token={token}"
        account_mail.send_account_email(recipient, subject,
            f"Use this link within 30 minutes to complete the requested CropPulse account action:\n\n{url}\n\n"
            "If you did not request this, you can ignore this message.")
    except Exception as exc:
        db.rollback()
        if action is not None:
            db.delete(action)
            db.commit()
        logging.getLogger(__name__).error("Account email delivery failed (%s): %s", purpose, type(exc).__name__)
        raise HTTPException(status_code=503, detail="Account email could not be delivered. Try again later.") from None


def _account_action_token(db: Session, raw_token: str, purpose: str) -> tuple[models.AccountActionToken, models.Farmer]:
    row = db.scalar(select(models.AccountActionToken).where(
        models.AccountActionToken.token_hash == sha256(raw_token.encode()).hexdigest(),
        models.AccountActionToken.purpose == purpose,
    ))
    now = datetime.now(timezone.utc)
    if row is None or row.used_at is not None:
        raise HTTPException(status_code=400, detail="This link is invalid or has already been used.")
    expires_at = row.expires_at.replace(tzinfo=timezone.utc) if row.expires_at.tzinfo is None else row.expires_at
    if expires_at <= now:
        raise HTTPException(status_code=400, detail="This link has expired. Request a new one.")
    farmer = db.get(models.Farmer, row.farmer_id)
    if farmer is None or farmer.status != "active":
        raise HTTPException(status_code=400, detail="This link is invalid or has already been used.")
    return row, farmer


def _revoke_farmer_sessions(db: Session, farmer_id: str, now: datetime):
    db.execute(update(models.FarmerSession).where(
        models.FarmerSession.farmer_id == farmer_id,
        models.FarmerSession.revoked_at.is_(None),
    ).values(revoked_at=now))


@app.post("/v1/browser-auth/email-change", status_code=202)
def request_email_change(body: EmailChangeRequest, request: Request,
                         farmer: models.Farmer = Depends(current_farmer), db: Session = Depends(get_db)):
    _account_action_attempt(request, body.new_email, "email-change", db)
    if not account_mail.configured():
        raise HTTPException(status_code=503, detail="Account email delivery is not configured by the server administrator.")
    if not password_hash.verify(body.current_password, farmer.password_hash):
        raise HTTPException(status_code=403, detail="Current password is incorrect.")
    new_email = str(body.new_email).lower()
    if new_email == farmer.email.lower():
        raise HTTPException(status_code=422, detail="Choose an email address different from the current one.")
    if db.scalar(select(models.Farmer.id).where(func.lower(models.Farmer.email) == new_email)):
        raise HTTPException(status_code=409, detail="An account with that email already exists.")
    token = _issue_account_action(db, farmer, "email_change", new_email)
    _deliver_account_action(db, farmer.id, "email_change", new_email, "Confirm your CropPulse email change", "confirm-email-change", token)
    return {"message": "Check the new email address for a confirmation link. The address changes only after confirmation."}


@app.post("/v1/browser-auth/email-change/confirm")
def confirm_email_change(body: AccountActionTokenInput, response: Response, db: Session = Depends(get_db)):
    row, farmer = _account_action_token(db, body.token, "email_change")
    new_email = row.target_email
    if not new_email:
        raise HTTPException(status_code=400, detail="This link is invalid or has already been used.")
    if db.scalar(select(models.Farmer.id).where(func.lower(models.Farmer.email) == new_email.lower(), models.Farmer.id != farmer.id)):
        raise HTTPException(status_code=409, detail="That email address is now in use. Request a new change with another address.")
    now = datetime.now(timezone.utc)
    farmer.email = new_email.lower()
    row.used_at = now
    _revoke_farmer_sessions(db, farmer.id, now)
    db.commit()
    response.delete_cookie("cp_session", path="/", secure=_cookie_secure(), httponly=True, samesite="lax")
    response.delete_cookie("cp_csrf", path="/v1", secure=_cookie_secure(), httponly=False, samesite="lax")
    return {"message": "Email address updated. Sign in again with the new address."}


@app.post("/v1/browser-auth/password-recovery", status_code=202)
def request_password_recovery(body: PasswordRecoveryRequest, request: Request, db: Session = Depends(get_db)):
    email = str(body.email).lower()
    _account_action_attempt(request, email, "password-recovery", db)
    if not account_mail.configured():
        raise HTTPException(status_code=503, detail="Account email delivery is not configured by the server administrator.")
    farmer = db.scalar(select(models.Farmer).where(func.lower(models.Farmer.email) == email, models.Farmer.status == "active"))
    if farmer is not None:
        token = _issue_account_action(db, farmer, "password_reset")
        try:
            _deliver_account_action(db, farmer.id, "password_reset", farmer.email, "Reset your CropPulse password", "reset-password", token)
        except HTTPException:
            # Keep the response indistinguishable for existing and unknown addresses.
            pass
    return {"message": "If an active account uses that email, a password reset link will arrive shortly."}


@app.post("/v1/browser-auth/password-reset/complete")
def complete_password_reset(body: PasswordResetRequest, response: Response, db: Session = Depends(get_db)):
    row, farmer = _account_action_token(db, body.token, "password_reset")
    now = datetime.now(timezone.utc)
    farmer.password_hash = password_hash.hash(body.new_password)
    row.used_at = now
    _revoke_farmer_sessions(db, farmer.id, now)
    db.commit()
    response.delete_cookie("cp_session", path="/", secure=_cookie_secure(), httponly=True, samesite="lax")
    response.delete_cookie("cp_csrf", path="/v1", secure=_cookie_secure(), httponly=False, samesite="lax")
    return {"message": "Password reset. Sign in with your new password."}


@app.delete("/v1/browser-auth/account", status_code=204)
def delete_own_account(body: AccountDeletionRequest, request: Request, response: Response,
                       farmer: models.Farmer = Depends(current_farmer), db: Session = Depends(get_db)):
    _account_action_attempt(request, farmer.email, "account-deletion", db)
    if not password_hash.verify(body.current_password, farmer.password_hash):
        raise HTTPException(status_code=403, detail="Current password is incorrect.")
    if farmer.role == "admin":
        admins = db.scalar(select(func.count()).select_from(models.Farmer).where(models.Farmer.role == "admin")) or 0
        if admins <= 1:
            raise HTTPException(status_code=409, detail="The last administrator account cannot be deleted. Grant admin access to another account first.")
    farmer_id = farmer.id
    db.add(models.AdminAuditEvent(
        actor_id=None, target_farmer_id=None, action="self_service_account_deleted", target_type="farmer",
        target_id=farmer_id, reason="Account owner confirmed deletion after password verification.",
        result="success", created_at=datetime.now(timezone.utc),
    ))
    db.delete(farmer)
    db.commit()
    response.delete_cookie("cp_session", path="/", secure=_cookie_secure(), httponly=True, samesite="lax")
    response.delete_cookie("cp_csrf", path="/v1", secure=_cookie_secure(), httponly=False, samesite="lax")


@app.post("/v1/auth/logout", status_code=204)
def logout(credentials: HTTPAuthorizationCredentials = Depends(bearer),
           farmer: models.Farmer = Depends(current_farmer), db: Session = Depends(get_db)):
    claims = jwt.decode(credentials.credentials, _secret(), algorithms=["HS256"])
    session_record = db.get(models.FarmerSession, claims["jti"])
    session_record.revoked_at = datetime.now(timezone.utc)
    db.commit()


@app.get("/v1/me", response_model=FarmerOut)
def me(farmer: models.Farmer = Depends(current_farmer)):
    return farmer


@app.get("/v1/messaging/reviewers")
def messaging_reviewers(db: Session = Depends(get_db), farmer: models.Farmer = Depends(current_farmer)):
    _require_messaging_enabled(db)
    if farmer.role != "farmer":
        raise HTTPException(status_code=403, detail="Only farmers can start a private conversation.")
    districts = set(db.scalars(select(models.Farm.district).where(models.Farm.owner_id == farmer.id)).all())
    if not districts:
        return []
    rows = db.execute(select(models.Farmer, models.ReviewerDistrict.district)
        .join(models.ReviewerDistrict, models.ReviewerDistrict.reviewer_id == models.Farmer.id)
        .where(models.Farmer.role == "reviewer", models.Farmer.status == "active",
               models.ReviewerDistrict.district.in_(districts))
        .order_by(models.Farmer.display_name, models.ReviewerDistrict.district)).all()
    reviewers = {}
    for reviewer, district in rows:
        entry = reviewers.setdefault(reviewer.id, {"id": reviewer.id, "display_name": reviewer.display_name,
            "role_label": "CropPulse reviewer", "eligible_districts": []})
        if district not in entry["eligible_districts"]:
            entry["eligible_districts"].append(district)
    return list(reviewers.values())


@app.post("/v1/messaging/conversations", status_code=200)
def create_or_get_conversation(body: PrivateConversationCreate, db: Session = Depends(get_db), farmer: models.Farmer = Depends(current_farmer)):
    _require_messaging_enabled(db)
    reviewer_id = body.reviewer_id
    if farmer.role != "farmer" or not isinstance(reviewer_id, str):
        raise HTTPException(status_code=422, detail="Choose an eligible CropPulse reviewer.")
    if not _pair_is_currently_eligible(db, farmer.id, reviewer_id):
        raise HTTPException(status_code=404, detail="Reviewer is unavailable for your farm districts.")
    conversation = db.scalar(select(models.PrivateConversation).where(
        models.PrivateConversation.farmer_id == farmer.id,
        models.PrivateConversation.reviewer_id == reviewer_id))
    if conversation is None:
        conversation = models.PrivateConversation(farmer_id=farmer.id, reviewer_id=reviewer_id)
        db.add(conversation)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            conversation = db.scalar(select(models.PrivateConversation).where(
                models.PrivateConversation.farmer_id == farmer.id,
                models.PrivateConversation.reviewer_id == reviewer_id))
            if conversation is None:
                raise
        db.refresh(conversation)
    return _conversation_summary(db, conversation, farmer)


@app.get("/v1/messaging/conversations")
def list_conversations(db: Session = Depends(get_db), actor: models.Farmer = Depends(current_farmer)):
    _require_messaging_enabled(db)
    if actor.role not in {"farmer", "reviewer"}:
        raise HTTPException(status_code=403, detail="Private messaging is available to farmers and CropPulse reviewers.")
    key = "farmer_id" if actor.role == "farmer" else "reviewer_id"
    rows = db.scalars(select(models.PrivateConversation).where(
        getattr(models.PrivateConversation, key) == actor.id).order_by(models.PrivateConversation.created_at.desc())).all()
    summaries = [_conversation_summary(db, row, actor) for row in rows
                 if _pair_is_currently_eligible(db, row.farmer_id, row.reviewer_id)]
    return sorted(summaries, key=lambda item: item["last_message_at"].isoformat(), reverse=True)


@app.get("/v1/messaging/conversations/{conversation_id}/messages")
def list_messages(conversation_id: str, offset: int = 0, limit: int = 50,
                  db: Session = Depends(get_db), actor: models.Farmer = Depends(current_farmer)):
    _require_messaging_enabled(db)
    if offset < 0 or not 1 <= limit <= 100:
        raise HTTPException(status_code=422, detail="Invalid message pagination.")
    conversation = _authorize_conversation(db, conversation_id, actor)
    total = db.scalar(select(func.count()).select_from(models.PrivateMessage).where(
        models.PrivateMessage.conversation_id == conversation.id)) or 0
    rows = db.scalars(select(models.PrivateMessage).where(
        models.PrivateMessage.conversation_id == conversation.id).order_by(
        models.PrivateMessage.created_at.desc(), models.PrivateMessage.id.desc()).offset(offset).limit(limit)).all()
    return {"items": [{"id": row.id, "sender_id": row.sender_id, "body": row.body,
                        "created_at": row.created_at, "read_at": row.read_at} for row in reversed(rows)],
            "total": total, "offset": offset, "limit": limit}


@app.post("/v1/messaging/conversations/{conversation_id}/messages", status_code=201)
def send_message(conversation_id: str, body: PrivateMessageCreate,
                 db: Session = Depends(get_db), actor: models.Farmer = Depends(current_farmer)):
    _require_messaging_enabled(db)
    conversation = _authorize_conversation(db, conversation_id, actor)
    message = models.PrivateMessage(conversation_id=conversation.id, sender_id=actor.id, body=body.body)
    db.add(message)
    db.commit()
    db.refresh(message)
    return {"id": message.id, "sender_id": message.sender_id, "body": message.body,
            "created_at": message.created_at, "read_at": message.read_at}


@app.post("/v1/messaging/conversations/{conversation_id}/read")
def mark_conversation_read(conversation_id: str, body: PrivateMessagesRead,
                           db: Session = Depends(get_db), actor: models.Farmer = Depends(current_farmer)):
    _require_messaging_enabled(db)
    conversation = _authorize_conversation(db, conversation_id, actor)
    now = datetime.now(timezone.utc)
    count = db.query(models.PrivateMessage).filter(
        models.PrivateMessage.conversation_id == conversation.id,
        models.PrivateMessage.id.in_(body.message_ids),
        models.PrivateMessage.sender_id != actor.id,
        models.PrivateMessage.read_at.is_(None)).update({"read_at": now}, synchronize_session=False)
    db.commit()
    return {"marked_read": count, "read_at": now}


@app.get("/v1/admin/messaging-setting")
def get_messaging_setting(db: Session = Depends(get_db), admin: models.Farmer = Depends(require_admin)):
    setting = db.get(models.MessagingSetting, 1)
    return {"farmer_reviewer_enabled": bool(setting and setting.farmer_reviewer_enabled)}


@app.put("/v1/admin/messaging-setting")
def set_messaging_setting(body: MessagingSettingUpdate, db: Session = Depends(get_db), admin: models.Farmer = Depends(require_admin)):
    setting = db.get(models.MessagingSetting, 1)
    if setting is None:
        setting = models.MessagingSetting(id=1, farmer_reviewer_enabled=body.farmer_reviewer_enabled)
        db.add(setting)
    else:
        setting.farmer_reviewer_enabled = body.farmer_reviewer_enabled
        setting.updated_at = datetime.now(timezone.utc)
    _record_admin_event(db, admin.id, None, "private_messaging_enabled" if body.farmer_reviewer_enabled else "private_messaging_disabled",
                        "messaging_setting", "farmer_reviewer", body.reason)
    db.commit()
    return {"farmer_reviewer_enabled": setting.farmer_reviewer_enabled}


@app.get("/v1/admin/overview")
def admin_overview(db: Session = Depends(get_db), admin: models.Farmer = Depends(require_admin)):
    total_farmers = db.scalar(select(func.count()).select_from(models.Farmer)) or 0
    active = db.scalar(select(func.count()).select_from(models.Farmer).where(models.Farmer.status == "active")) or 0
    suspended = db.scalar(select(func.count()).select_from(models.Farmer).where(models.Farmer.status == "suspended")) or 0
    farms = db.scalar(select(func.count()).select_from(models.Farm)) or 0
    activities = db.scalar(select(func.count()).select_from(models.FarmActivity)) or 0
    by_district = db.execute(select(models.Farm.district, func.count(models.Farm.id)).group_by(models.Farm.district).order_by(models.Farm.district)).all()
    by_crop = db.execute(select(models.FarmActivity.crop, func.count(models.FarmActivity.id)).group_by(models.FarmActivity.crop).order_by(models.FarmActivity.crop)).all()
    all_activities = db.scalars(select(models.FarmActivity)).all()
    pending = sum(1 for activity in all_activities if _activity_review_status(db, activity) in ("pending", "correction_requested"))
    return {
        "accounts": {"total": total_farmers, "active": active, "suspended": suspended},
        "farms": farms,
        "farmer_reported_activities": activities,
        "awaiting_review": pending,
        "farms_by_district": [{"district": name, "farms": count} for name, count in by_district],
        "reported_activities_by_crop": [{"crop": name, "activities": count} for name, count in by_crop],
        "health": {"api": "available", "database": "available"},
        "definitions": {
            "farmer_reported_activities": "Persisted farm activity submissions; not independently verified.",
            "awaiting_review": "Activities with no review decision or a correction request.",
            "health": "Current request reached the API and executed database queries; this is not an uptime history.",
        },
    }


@app.get("/v1/agricultural-statistics/nisr")
def nisr_agricultural_statistics(
    year: int | None = None, season: str | None = None, district: str | None = None, crop: str | None = None,
    farmer: models.Farmer = Depends(current_farmer),
):
    """Serve validated public NISR SAS aggregates to signed-in React users."""
    frame, status = load_data()
    if status.get("state") != "validated":
        raise HTTPException(status_code=503, detail="NISR agricultural statistics are not available with a validated source manifest.")
    provenance = next((item for item in status.get("provenance", [])
                       if item.get("publisher") == "National Institute of Statistics of Rwanda (NISR)"), None)
    if provenance is None or frame.empty:
        raise HTTPException(status_code=503, detail="A validated NISR SAS dataset is not installed.")
    if season is not None and season not in {"A", "B", "C"}:
        raise HTTPException(status_code=422, detail="Season must be A, B, or C.")
    if year is not None:
        frame = frame[frame["year"] == year]
    if season is not None:
        frame = frame[frame["season"] == season]
    if district is not None:
        frame = frame[frame["district"] == district]
    if crop is not None:
        frame = frame[frame["crop"] == crop]
    records = []
    for row in frame[["district", "crop", "season", "year", "area_ha", "production_t", "yield_t_ha"]].to_dict("records"):
        records.append({key: (None if value is None or (isinstance(value, float) and not math.isfinite(value))
                              else value.item() if hasattr(value, "item") else value)
                        for key, value in row.items()})
    return {
        "publisher": provenance["publisher"], "title": provenance["title"],
        "source_url": provenance["source_url"], "reference_period": provenance["reference_period"],
        "retrieved_at": provenance["retrieved_at"], "units": provenance["units"],
        "limitations": provenance.get("limitations", ""), "quality_report": provenance.get("quality_report", {}),
        "coverage": status.get("geography", {}),
        "available_years": sorted(int(value) for value in frame["year"].dropna().unique()),
        "available_seasons": sorted(frame["season"].dropna().unique()),
        "available_districts": sorted(frame["district"].dropna().unique()),
        "available_crops": sorted(frame["crop"].dropna().unique()),
        "records": records,
    }


@app.get("/v1/admin/farmers", response_model=list[AdminFarmerOut])
def admin_farmers(q: str = "", status: str | None = None, offset: int = 0, limit: int = 50,
                  db: Session = Depends(get_db), admin: models.Farmer = Depends(require_admin)):
    if status not in (None, "active", "suspended") or offset < 0 or not 1 <= limit <= 100:
        raise HTTPException(status_code=422, detail="Invalid account filter or pagination.")
    query = select(models.Farmer)
    if status:
        query = query.where(models.Farmer.status == status)
    if q.strip():
        term = f"%{q.strip().lower()}%"
        query = query.where((func.lower(models.Farmer.email).like(term)) | (func.lower(models.Farmer.display_name).like(term)))
    farmers = db.scalars(query.order_by(models.Farmer.created_at.desc()).offset(offset).limit(limit)).all()
    if not farmers:
        return []
    ids = [farmer.id for farmer in farmers]
    counts = dict(db.execute(select(models.Farm.owner_id, func.count(models.Farm.id)).where(models.Farm.owner_id.in_(ids)).group_by(models.Farm.owner_id)).all())
    scopes: dict[str, list[str]] = {}
    for reviewer_id, district in db.execute(select(models.ReviewerDistrict.reviewer_id, models.ReviewerDistrict.district).where(models.ReviewerDistrict.reviewer_id.in_(ids)).order_by(models.ReviewerDistrict.district)).all():
        scopes.setdefault(reviewer_id, []).append(district)
    return [{"id": farmer.id, "email": farmer.email, "display_name": farmer.display_name,
             "role": farmer.role, "status": farmer.status, "created_at": farmer.created_at,
             "farm_count": counts.get(farmer.id, 0), "reviewer_districts": scopes.get(farmer.id, [])} for farmer in farmers]


@app.patch("/v1/admin/farmers/{farmer_id}/status")
def admin_set_status(farmer_id: str, body: AccountStatusUpdate, db: Session = Depends(get_db), admin: models.Farmer = Depends(require_admin)):
    target = db.get(models.Farmer, farmer_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Account was not found.")
    if target.id == admin.id and body.status == "suspended":
        raise HTTPException(status_code=409, detail="You cannot suspend your own administrator account.")
    target.status = body.status
    if body.status == "suspended":
        db.query(models.FarmerSession).filter(models.FarmerSession.farmer_id == target.id,
              models.FarmerSession.revoked_at.is_(None)).update({"revoked_at": datetime.now(timezone.utc)}, synchronize_session=False)
    _record_admin_event(db, admin.id, target.id, f"account_{body.status}", "farmer", target.id, body.reason)
    db.commit()
    return {"id": target.id, "status": target.status}


@app.post("/v1/admin/farmers/{farmer_id}/revoke-sessions")
def admin_revoke_sessions(farmer_id: str, body: ReasonInput, db: Session = Depends(get_db), admin: models.Farmer = Depends(require_admin)):
    target = db.get(models.Farmer, farmer_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Account was not found.")
    count = db.query(models.FarmerSession).filter(models.FarmerSession.farmer_id == target.id,
              models.FarmerSession.revoked_at.is_(None)).update({"revoked_at": datetime.now(timezone.utc)}, synchronize_session=False)
    _record_admin_event(db, admin.id, target.id, "sessions_revoked", "farmer", target.id, body.reason)
    db.commit()
    return {"id": target.id, "revoked_sessions": count}


@app.patch("/v1/admin/farmers/{farmer_id}/role")
def admin_set_role(farmer_id: str, body: FarmerRoleUpdate, db: Session = Depends(get_db), admin: models.Farmer = Depends(require_admin)):
    target = db.get(models.Farmer, farmer_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Account was not found.")
    if target.role == "admin" and body.role != "admin":
        raise HTTPException(status_code=409, detail="Administrator demotion requires the server-side operator command.")
    target.role = body.role
    if body.role != "reviewer":
        db.query(models.ReviewerDistrict).filter_by(reviewer_id=target.id).delete(synchronize_session=False)
    _record_admin_event(db, admin.id, target.id, "account_role_changed", "farmer", target.id, body.reason)
    db.commit()
    return {"id": target.id, "role": target.role}


@app.patch("/v1/admin/farmers/{farmer_id}/permissions")
def admin_set_permissions(farmer_id: str, body: FarmerPermissionsUpdate,
                          db: Session = Depends(get_db), admin: models.Farmer = Depends(require_admin)):
    target = db.get(models.Farmer, farmer_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Account was not found.")
    if target.role == "admin" and body.role != "admin":
        raise HTTPException(status_code=409, detail="Administrator demotion requires the server-side operator command.")
    if body.role == "reviewer" and not body.districts:
        raise HTTPException(status_code=422, detail="Assign at least one district to a reviewer.")
    if body.role != "reviewer" and body.districts:
        raise HTTPException(status_code=422, detail="District assignments are only valid for reviewers.")
    target.role = body.role
    db.query(models.ReviewerDistrict).filter_by(reviewer_id=target.id).delete(synchronize_session=False)
    if body.role == "reviewer":
        db.add_all(models.ReviewerDistrict(reviewer_id=target.id, district=district) for district in body.districts)
    _record_admin_event(db, admin.id, target.id, "account_permissions_changed", "farmer", target.id,
                        f"{body.reason}; role={body.role}; districts={','.join(body.districts)}")
    db.commit()
    return {"id": target.id, "role": target.role, "districts": body.districts}


@app.put("/v1/admin/farmers/{farmer_id}/reviewer-districts")
def admin_set_reviewer_districts(farmer_id: str, body: ReviewerDistrictsUpdate, db: Session = Depends(get_db), admin: models.Farmer = Depends(require_admin)):
    target = db.get(models.Farmer, farmer_id)
    if target is None or target.role != "reviewer":
        raise HTTPException(status_code=404, detail="Reviewer account was not found.")
    db.query(models.ReviewerDistrict).filter_by(reviewer_id=target.id).delete(synchronize_session=False)
    db.add_all(models.ReviewerDistrict(reviewer_id=target.id, district=district) for district in body.districts)
    _record_admin_event(db, admin.id, target.id, "reviewer_scope_changed", "farmer", target.id,
                        ", ".join(body.districts) or "All district assignments removed")
    db.commit()
    return {"reviewer_id": target.id, "districts": body.districts}


@app.get("/v1/admin/agronomy-review-authorizations")
def admin_agronomy_review_authorizations(db: Session = Depends(get_db), admin: models.Farmer = Depends(require_admin)):
    del admin
    rows = db.execute(select(models.AgronomyReviewAuthorizationEvent, models.Farmer)
                      .join(models.Farmer, models.Farmer.id == models.AgronomyReviewAuthorizationEvent.reviewer_id)
                      .order_by(models.AgronomyReviewAuthorizationEvent.created_at.desc()).limit(200)).all()
    return [{"id": event.id, "reviewer_id": reviewer.id, "reviewer_name": reviewer.display_name,
             "reviewer_email": reviewer.email, "reviewer_role": reviewer.role,
             "action": event.action, "actor_id": event.actor_id, "reason": event.reason,
             "created_at": event.created_at}
            for event, reviewer in rows]


@app.post("/v1/admin/farmers/{farmer_id}/agronomy-review-authorization")
def admin_update_agronomy_review_authorization(farmer_id: str, body: AgronomyReviewerAuthorizationUpdate,
                                                db: Session = Depends(get_db), admin: models.Farmer = Depends(require_admin)):
    target = db.get(models.Farmer, farmer_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Account was not found.")
    if body.action == "grant" and (target.status != "active" or target.role not in {"reviewer", "admin"}):
        raise HTTPException(status_code=422, detail="Only an active reviewer or administrator account can receive explicit agronomy review authorization.")
    event = models.AgronomyReviewAuthorizationEvent(reviewer_id=target.id, actor_id=admin.id,
                                                      action=body.action, reason=body.reason)
    db.add(event)
    _record_admin_event(db, admin.id, target.id, f"agronomy_review_authorization_{body.action}",
                        "farmer", target.id, body.reason)
    db.commit()
    db.refresh(event)
    return {"id": event.id, "reviewer_id": event.reviewer_id, "action": event.action,
            "created_at": event.created_at,
            "authorized": body.action == "grant" and target.status == "active" and target.role in {"reviewer", "admin"}}


def _agronomy_proposal_payload(db: Session, proposal: models.AgronomyRuleProposal):
    decisions = db.scalars(select(models.AgronomyRuleDecision)
                           .where(models.AgronomyRuleDecision.proposal_id == proposal.id)
                           .order_by(models.AgronomyRuleDecision.created_at, models.AgronomyRuleDecision.id)).all()
    status = decisions[-1].decision if decisions else "proposed"
    return {"id": proposal.id, "rule_id": proposal.rule_id, "version": proposal.version,
            "title": proposal.title, "category": proposal.category, "crop_or_topic": proposal.crop_or_topic,
            "proposed_claim": proposal.proposed_claim, "geographic_scope": proposal.geographic_scope,
            "season_scope": proposal.season_scope, "units": proposal.units, "assumptions": proposal.assumptions,
            "limitations": proposal.limitations, "uncertainty": proposal.uncertainty,
            "source_references": proposal.source_references, "proposed_by": proposal.proposed_by,
            "revision_of_id": proposal.revision_of_id, "created_at": proposal.created_at,
            "status": status, "guidance_activation": False,
            "guidance_note": "Review workflow decisions do not activate farmer guidance; external qualification and the agronomic trust anchor remain unverified.",
            "decision_history": [{"id": d.id, "reviewer_id": d.reviewer_id, "decision": d.decision,
                                  "rationale": d.rationale, "created_at": d.created_at} for d in decisions]}


@app.get("/v1/agronomy/rule-proposals")
def list_agronomy_rule_proposals(offset: int = 0, limit: int = 50, db: Session = Depends(get_db),
                                 reviewer: models.Farmer = Depends(require_agronomy_reviewer)):
    del reviewer
    if offset < 0 or not 1 <= limit <= 100:
        raise HTTPException(status_code=422, detail="Invalid proposal pagination.")
    rows = db.scalars(select(models.AgronomyRuleProposal).order_by(models.AgronomyRuleProposal.created_at.desc(),
                                                                  models.AgronomyRuleProposal.id.desc())
                      .offset(offset).limit(limit)).all()
    return [_agronomy_proposal_payload(db, proposal) for proposal in rows]


@app.post("/v1/agronomy/rule-proposals", status_code=201)
def create_agronomy_rule_proposal(body: AgronomyRuleProposalCreate, db: Session = Depends(get_db),
                                  reviewer: models.Farmer = Depends(require_agronomy_reviewer)):
    revision = None
    if body.revision_of_id:
        revision = db.get(models.AgronomyRuleProposal, body.revision_of_id)
        if revision is None or revision.rule_id != body.rule_id:
            raise HTTPException(status_code=422, detail="A revision must reference an existing proposal with the same rule identifier.")
        if revision.version == body.version:
            raise HTTPException(status_code=422, detail="A revised proposal must use a new version identifier.")
    proposal = models.AgronomyRuleProposal(**body.model_dump(mode="json", exclude={"revision_of_id"}),
                                           proposed_by=reviewer.id,
                                           revision_of_id=revision.id if revision else None)
    db.add(proposal)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="This rule identifier and version already exist.") from None
    db.refresh(proposal)
    return _agronomy_proposal_payload(db, proposal)


@app.post("/v1/agronomy/rule-proposals/{proposal_id}/decisions")
def decide_agronomy_rule_proposal(proposal_id: str, body: AgronomyRuleDecisionInput,
                                  db: Session = Depends(get_db), reviewer: models.Farmer = Depends(require_agronomy_reviewer)):
    proposal = db.get(models.AgronomyRuleProposal, proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Rule proposal was not found.")
    if proposal.proposed_by == reviewer.id:
        raise HTTPException(status_code=403, detail="A proposer cannot review or decide their own rule version.")
    prior = db.scalars(select(models.AgronomyRuleDecision)
                       .where(models.AgronomyRuleDecision.proposal_id == proposal.id)
                       .order_by(models.AgronomyRuleDecision.created_at.desc(), models.AgronomyRuleDecision.id.desc())).first()
    if prior and prior.decision in {"approved", "rejected", "withdrawn", "superseded"}:
        raise HTTPException(status_code=409, detail="This proposal version has a terminal decision; submit a new revision instead.")
    if body.decision == "approved":
        scope = proposal.geographic_scope or {}
        has_scoped_geography = scope.get("type") != "unknown" and bool(scope.get("scope"))
        has_versioned_source = any(reference.get("source_version") or reference.get("publication_or_revision_date")
                                   for reference in proposal.source_references)
        if (not proposal.source_references or not has_versioned_source or not has_scoped_geography
                or not proposal.season_scope or not proposal.units or not proposal.assumptions
                or not proposal.limitations or not proposal.uncertainty.strip()):
            raise HTTPException(status_code=422, detail="Approval requires a versioned evidence citation, defined geographic and seasonal scope, units, assumptions, limitations, and uncertainty.")
    decision = models.AgronomyRuleDecision(proposal_id=proposal.id, reviewer_id=reviewer.id,
                                            decision=body.decision, rationale=body.rationale)
    db.add(decision)
    _record_admin_event(db, reviewer.id, proposal.proposed_by, f"agronomy_rule_{body.decision}",
                        "agronomy_rule_proposal", proposal.id, body.rationale)
    db.commit()
    db.refresh(decision)
    result = _agronomy_proposal_payload(db, proposal)
    result["latest_decision_id"] = decision.id
    return result


def _review_queue(db: Session, reviewer: models.Farmer, district: str | None, offset: int, limit: int):
    if offset < 0 or not 1 <= limit <= 100:
        raise HTTPException(status_code=422, detail="Invalid review queue pagination.")
    allowed = None
    if reviewer.role != "admin":
        allowed = set(db.scalars(select(models.ReviewerDistrict.district).where(models.ReviewerDistrict.reviewer_id == reviewer.id)).all())
        if district and district not in allowed:
            raise HTTPException(status_code=403, detail="This district is outside your assigned review scope.")
    query = select(models.FarmActivity, models.Farm.name).join(models.Farm, models.Farm.id == models.FarmActivity.farm_id)
    if district:
        query = query.where(models.FarmActivity.district == district)
    if allowed is not None:
        if not allowed:
            return []
        query = query.where(models.FarmActivity.district.in_(allowed))
    rows = db.execute(query.order_by(models.FarmActivity.created_at.desc()).offset(offset).limit(limit)).all()
    ids = [activity.id for activity, _ in rows]
    decisions = db.scalars(select(models.ActivityReviewDecision).where(models.ActivityReviewDecision.activity_id.in_(ids))
                           .order_by(models.ActivityReviewDecision.created_at.desc())).all() if ids else []
    latest = {}
    history = {}
    for decision in decisions:
        latest.setdefault(decision.activity_id, decision)
        history.setdefault(decision.activity_id, []).append(decision)
    result = []
    for activity, farm_name in rows:
        current = latest.get(activity.id)
        result.append({"id": activity.id, "farm_id": activity.farm_id, "farm_name": farm_name,
                       "district": activity.district, "crop": activity.crop, "season": activity.season,
                       "activity_type": activity.activity_type, "event_date": activity.event_date,
                       "area_ha": activity.area_ha, "quantity": activity.quantity, "unit": activity.unit,
                       "amount_rwf": activity.amount_rwf, "notes": activity.notes,
                       "verification": activity.verification,
                       "review_status": _activity_review_status(db, activity),
                       "review_history": [{"decision": d.decision, "reason": d.reason,
                                           "reviewer_id": d.reviewer_id, "created_at": d.created_at}
                                          for d in history.get(activity.id, [])]})
    return result


@app.post("/v1/crop-planning/recommendations")
def crop_planning_recommendations(body: CropRecommendationRequest,
                                  farmer: models.Farmer = Depends(current_farmer)):
    """Use the single existing, explainable engine and the validated-data loader."""
    del farmer  # Authentication is required; recommendations contain no private farm data.
    frame, data_status = load_data()
    result = crop_recommender.recommend(
        frame, data_status, body.district, body.season,
        elevation=body.elevation_m, irrigation=body.irrigation,
        water=body.water_availability,
    )
    result["context"] = {
        "district": body.district,
        "season": body.season,
        "elevation_m": body.elevation_m,
        "irrigation": body.irrigation,
        "water_availability": body.water_availability,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "statistics_status": data_status.get("state", "unavailable"),
        "statistics_provenance": data_status.get("provenance", []),
        "statistics_note": data_status.get("message", "Statistics status unavailable."),
        "ranking_method": "Provisional CropPulse guide category, then crop name. Validated NISR observations are descriptive context only and never affect suitability or rank.",
    }
    return result


@app.get("/v1/reviewer/activities")
def reviewer_activities(district: str | None = None, offset: int = 0, limit: int = 50,
                        db: Session = Depends(get_db), reviewer: models.Farmer = Depends(require_reviewer)):
    return _review_queue(db, reviewer, district, offset, limit)


@app.post("/v1/reviewer/activities/{activity_id}/decisions")
def reviewer_decide(activity_id: str, body: ReviewDecisionInput, db: Session = Depends(get_db), reviewer: models.Farmer = Depends(require_reviewer)):
    activity = db.get(models.FarmActivity, activity_id)
    if activity is None:
        raise HTTPException(status_code=404, detail="Submission was not found.")
    if reviewer.role != "admin":
        assigned = db.scalar(select(models.ReviewerDistrict.district).where(
            models.ReviewerDistrict.reviewer_id == reviewer.id,
            models.ReviewerDistrict.district == activity.district))
        if not assigned:
            raise HTTPException(status_code=404, detail="Submission was not found.")
    decision = models.ActivityReviewDecision(activity_id=activity.id, reviewer_id=reviewer.id,
                                             decision=body.decision, reason=body.reason)
    db.add(decision)
    _record_admin_event(db, reviewer.id, activity.farm.owner_id, "activity_review_decision", "farm_activity", activity.id,
                        f"{body.decision}: {body.reason}")
    db.commit()
    db.refresh(decision)
    return {"id": decision.id, "activity_id": decision.activity_id, "decision": decision.decision,
            "reason": decision.reason, "created_at": decision.created_at}


@app.get("/v1/admin/audit-events")
def admin_audit_events(offset: int = 0, limit: int = 50, db: Session = Depends(get_db), admin: models.Farmer = Depends(require_admin)):
    if offset < 0 or not 1 <= limit <= 100:
        raise HTTPException(status_code=422, detail="Invalid audit event pagination.")
    rows = db.scalars(select(models.AdminAuditEvent).order_by(models.AdminAuditEvent.created_at.desc()).offset(offset).limit(limit)).all()
    return [{"id": row.id, "actor_id": row.actor_id, "target_farmer_id": row.target_farmer_id,
             "action": row.action, "target_type": row.target_type, "target_id": row.target_id,
             "reason": row.reason, "result": row.result, "created_at": row.created_at} for row in rows]


def _owned_farm(farm_id: str, farmer_id: str, db: Session) -> models.Farm:
    farm = db.scalar(select(models.Farm).where(models.Farm.id == farm_id, models.Farm.owner_id == farmer_id))
    if farm is None:
        # Same response for missing and another farmer's farm prevents ID enumeration.
        raise HTTPException(status_code=404, detail="Farm was not found.")
    return farm


def _normalize_crop_health_photo(photo: UploadFile) -> tuple[bytes, int, int]:
    content = photo.file.read(MAX_CROP_HEALTH_PHOTO_BYTES + 1)
    if not content or len(content) > MAX_CROP_HEALTH_PHOTO_BYTES:
        raise HTTPException(status_code=413, detail="Choose a crop photo no larger than 5 MB.")
    declared_mime = (photo.content_type or "").lower().split(";", 1)[0].strip()
    accepted_mime = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as probe:
                image_format = probe.format
                width, height = probe.size
                if image_format not in accepted_mime:
                    raise ValueError("unsupported image format")
                if declared_mime and declared_mime != accepted_mime[image_format]:
                    raise ValueError("image content type does not match file data")
                if (width < 32 or height < 32 or width > MAX_CROP_HEALTH_PHOTO_DIMENSION
                        or height > MAX_CROP_HEALTH_PHOTO_DIMENSION or width * height > MAX_CROP_HEALTH_PHOTO_PIXELS):
                    raise ValueError("image dimensions are outside supported limits")
                probe.verify()
            with Image.open(BytesIO(content)) as image:
                image = ImageOps.exif_transpose(image)
                image.load()
                normalized = image.convert("RGB")
                output = BytesIO()
                normalized.save(output, format="JPEG", quality=84, optimize=True)
                cleaned = output.getvalue()
                if len(cleaned) > MAX_CROP_HEALTH_PHOTO_BYTES:
                    raise ValueError("normalized image is too large")
                return cleaned, normalized.width, normalized.height
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError,
            Image.DecompressionBombWarning) as exc:
        raise HTTPException(status_code=422, detail="Upload a valid JPEG, PNG, or WebP photo with dimensions up to 4096 by 4096 pixels.") from exc


def _crop_health_update_rows(db: Session, case_id: str):
    rows = db.execute(select(models.CropHealthCaseUpdate, models.Farmer.display_name, models.Farmer.role)
        .outerjoin(models.Farmer, models.Farmer.id == models.CropHealthCaseUpdate.author_id)
        .where(models.CropHealthCaseUpdate.case_id == case_id)
        .order_by(models.CropHealthCaseUpdate.created_at, models.CropHealthCaseUpdate.id)).all()
    return [{"id": row.id, "author_id": row.author_id, "author_name": author_name or "Former account",
             "author_role": author_role or "unavailable", "update_type": row.update_type,
             "assessment": row.assessment, "message": row.message, "created_at": row.created_at}
            for row, author_name, author_role in rows]


def _crop_health_case_payload(db: Session, case: models.CropHealthCase, *, include_updates: bool = False):
    farm = db.get(models.Farm, case.farm_id)
    field = db.get(models.FarmField, case.field_id) if case.field_id else None
    plan = db.get(models.CropPlan, case.crop_plan_id) if case.crop_plan_id else None
    payload = {"id": case.id, "farm_id": case.farm_id, "farm_name": farm.name if farm else "Unavailable farm",
        "district": farm.district if farm else "", "field_id": case.field_id,
        "field_name": field.name if field else None, "crop_plan_id": case.crop_plan_id,
        "crop_plan_status": plan.status if plan else None, "farmer_id": case.farmer_id,
        "crop": case.crop, "symptoms": case.symptoms, "observed_date": case.observed_date,
        "plant_parts_affected": case.plant_parts_affected, "spreading": case.spreading,
        "ai_screening": attach_guidance(json.loads(case.ai_screening_json)) if case.ai_screening_json else attach_guidance({
            "status": case.ai_screening_status or "not_run", "model_name": case.ai_model_name,
            "model_version": case.ai_model_version, "generated_at": case.ai_screened_at,
            "candidates": [], "message": "No automated screening is available for this report.",
        }),
        "status": case.status, "diagnosis_status": case.diagnosis_status,
        "photo_url": f"/v1/crop-health/cases/{case.id}/photo",
        "photo_size_bytes": case.photo_size_bytes, "photo_width": case.photo_width,
        "photo_height": case.photo_height, "created_at": case.created_at, "updated_at": case.updated_at}
    if include_updates:
        payload["updates"] = _crop_health_update_rows(db, case.id)
    return payload


def _crop_health_reviewer_scope(db: Session, case: models.CropHealthCase, reviewer: models.Farmer) -> bool:
    if reviewer.role == "admin":
        return True
    if reviewer.role != "reviewer":
        return False
    farm = db.get(models.Farm, case.farm_id)
    if farm is None:
        return False
    return db.scalar(select(models.ReviewerDistrict.reviewer_id).where(
        models.ReviewerDistrict.reviewer_id == reviewer.id,
        models.ReviewerDistrict.district == farm.district)) is not None


def _crop_health_reviewer_case(db: Session, case_id: str, reviewer: models.Farmer) -> models.CropHealthCase:
    case = db.get(models.CropHealthCase, case_id)
    if case is None or not _crop_health_reviewer_scope(db, case, reviewer):
        raise HTTPException(status_code=404, detail="Crop-health report was not found.")
    return case


def _crop_health_farmer_case(db: Session, case_id: str, farmer: models.Farmer) -> models.CropHealthCase:
    case = db.get(models.CropHealthCase, case_id)
    if case is None or case.farmer_id != farmer.id:
        raise HTTPException(status_code=404, detail="Crop-health report was not found.")
    return case


@app.get("/v1/crop-health/crops")
def crop_health_crops(farmer: models.Farmer = Depends(current_farmer)):
    if farmer.role != "farmer":
        raise HTTPException(status_code=403, detail="Only farmers can submit crop-health reports.")
    return sorted(CROPS)


@app.get("/v1/crop-health/cases")
def list_crop_health_cases(offset: int = 0, limit: int = 50,
                           db: Session = Depends(get_db), farmer: models.Farmer = Depends(current_farmer)):
    if farmer.role != "farmer":
        raise HTTPException(status_code=403, detail="Only farmers can view farmer crop-health reports.")
    if offset < 0 or not 1 <= limit <= 100:
        raise HTTPException(status_code=422, detail="Invalid report pagination.")
    rows = db.scalars(select(models.CropHealthCase).where(models.CropHealthCase.farmer_id == farmer.id)
        .order_by(models.CropHealthCase.created_at.desc()).offset(offset).limit(limit)).all()
    return [_crop_health_case_payload(db, case) for case in rows]


@app.post("/v1/crop-health/cases", status_code=201)
def create_crop_health_case(
    farm_id: str = Form(...), crop: str = Form(...), symptoms: str = Form(...),
    field_id: str | None = Form(default=None), crop_plan_id: str | None = Form(default=None),
    observed_date: date | None = Form(default=None),
    plant_parts_affected: str | None = Form(default=None), spreading: bool | None = Form(default=None),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db), farmer: models.Farmer = Depends(current_farmer),
):
    if farmer.role != "farmer":
        raise HTTPException(status_code=403, detail="Only farmers can submit crop-health reports.")
    farm = _owned_farm(farm_id, farmer.id, db)
    crop = crop.strip()
    symptoms = symptoms.strip()
    if crop not in CROPS:
        raise HTTPException(status_code=422, detail="Choose a crop supported by CropPulse.")
    if not symptoms or len(symptoms) > 3000:
        raise HTTPException(status_code=422, detail="Describe the visible symptoms in 1 to 3,000 characters.")
    plant_parts_affected = plant_parts_affected.strip() if plant_parts_affected else None
    if plant_parts_affected and len(plant_parts_affected) > 300:
        raise HTTPException(status_code=422, detail="Affected plant parts must be 300 characters or fewer.")
    if observed_date and observed_date > date.today():
        raise HTTPException(status_code=422, detail="The first-noticed date cannot be in the future.")
    field_id = field_id.strip() if field_id and field_id.strip() else None
    crop_plan_id = crop_plan_id.strip() if crop_plan_id and crop_plan_id.strip() else None
    selected_field = None
    if field_id:
        selected_field = db.scalar(select(models.FarmField).where(
            models.FarmField.id == field_id, models.FarmField.farm_id == farm.id,
            models.FarmField.archived_at.is_(None)))
        if selected_field is None:
            raise HTTPException(status_code=404, detail="Active field was not found on this farm.")
    plan = None
    if crop_plan_id:
        plan = db.scalar(select(models.CropPlan).where(
            models.CropPlan.id == crop_plan_id, models.CropPlan.farm_id == farm.id))
        if plan is None:
            raise HTTPException(status_code=404, detail="Crop plan was not found on this farm.")
        if plan.crop != crop:
            raise HTTPException(status_code=422, detail="The selected crop must match the linked crop plan.")
        if selected_field and plan.field_id and selected_field.id != plan.field_id:
            raise HTTPException(status_code=422, detail="The selected field does not match the linked crop plan.")
        if not selected_field and plan.field_id:
            selected_field = db.scalar(select(models.FarmField).where(
                models.FarmField.id == plan.field_id, models.FarmField.farm_id == farm.id))
            field_id = selected_field.id if selected_field else None
    image_data, width, height = _normalize_crop_health_photo(photo)
    now = datetime.now(timezone.utc)
    screening = screen_crop_image(crop, image_data)
    screening["generated_at"] = now.isoformat() if screening.get("status") == "candidate_screening" else None
    screening = attach_guidance(screening)
    case = models.CropHealthCase(
        farmer_id=farmer.id, farm_id=farm.id, field_id=field_id,
        crop_plan_id=crop_plan_id, crop=crop, symptoms=symptoms,
        observed_date=observed_date, plant_parts_affected=plant_parts_affected, spreading=spreading,
        ai_screening_status=screening["status"], ai_screening_json=json.dumps(screening),
        ai_model_name=screening.get("model_name"), ai_model_version=screening.get("model_version"),
        ai_screened_at=now if screening.get("status") == "candidate_screening" else None,
        status="submitted", diagnosis_status="unresolved",
        photo_data=image_data, photo_sha256=sha256(image_data).hexdigest(),
        photo_size_bytes=len(image_data), photo_width=width, photo_height=height,
        created_at=now, updated_at=now,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return _crop_health_case_payload(db, case, include_updates=True)


@app.get("/v1/crop-health/cases/{case_id}")
def get_crop_health_case(case_id: str, db: Session = Depends(get_db), farmer: models.Farmer = Depends(current_farmer)):
    return _crop_health_case_payload(db, _crop_health_farmer_case(db, case_id, farmer), include_updates=True)


@app.get("/v1/crop-health/cases/{case_id}/photo")
def get_crop_health_photo(case_id: str, db: Session = Depends(get_db), actor: models.Farmer = Depends(current_farmer)):
    case = db.get(models.CropHealthCase, case_id)
    if case is None or not (case.farmer_id == actor.id or _crop_health_reviewer_scope(db, case, actor)):
        raise HTTPException(status_code=404, detail="Crop-health photograph was not found.")
    return Response(content=case.photo_data, media_type="image/jpeg",
                    headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff",
                             "Content-Disposition": "inline"})


@app.get("/v1/reviewer/crop-health/cases")
def reviewer_crop_health_cases(offset: int = 0, limit: int = 50,
                               db: Session = Depends(get_db), reviewer: models.Farmer = Depends(require_reviewer)):
    if offset < 0 or not 1 <= limit <= 100:
        raise HTTPException(status_code=422, detail="Invalid report pagination.")
    query = select(models.CropHealthCase).join(models.Farm, models.Farm.id == models.CropHealthCase.farm_id)
    if reviewer.role != "admin":
        districts = select(models.ReviewerDistrict.district).where(models.ReviewerDistrict.reviewer_id == reviewer.id)
        query = query.where(models.Farm.district.in_(districts))
    rows = db.scalars(query.order_by(models.CropHealthCase.created_at.desc()).offset(offset).limit(limit)).all()
    result = []
    for case in rows:
        payload = _crop_health_case_payload(db, case)
        farmer = db.get(models.Farmer, case.farmer_id)
        payload["farmer_name"] = farmer.display_name if farmer else "Former account"
        result.append(payload)
    return result


@app.get("/v1/reviewer/crop-health/cases/{case_id}")
def reviewer_get_crop_health_case(case_id: str, db: Session = Depends(get_db), reviewer: models.Farmer = Depends(require_reviewer)):
    case = _crop_health_reviewer_case(db, case_id, reviewer)
    payload = _crop_health_case_payload(db, case, include_updates=True)
    farmer = db.get(models.Farmer, case.farmer_id)
    payload["farmer_name"] = farmer.display_name if farmer else "Former account"
    return payload


@app.post("/v1/reviewer/crop-health/cases/{case_id}/updates", status_code=201)
def reviewer_update_crop_health_case(case_id: str, body: CropHealthReviewerUpdate,
                                     db: Session = Depends(get_db), reviewer: models.Farmer = Depends(require_reviewer)):
    case = _crop_health_reviewer_case(db, case_id, reviewer)
    transitions = {
        "start_review": {"submitted": "under_review"},
        "request_information": {"under_review": "awaiting_farmer"},
        "provide_update": {"under_review": "under_review"},
        "resolve": {"under_review": "resolved"},
    }
    next_status = transitions[body.action].get(case.status)
    if next_status is None:
        raise HTTPException(status_code=409, detail=f"Cannot apply '{body.action}' while this case is {case.status}.")
    if body.assessment == "provisional_observation" and body.action not in {"provide_update", "resolve"}:
        raise HTTPException(status_code=422, detail="A provisional observation can be added with a review update or resolution.")
    now = datetime.now(timezone.utc)
    if body.assessment is not None:
        case.diagnosis_status = body.assessment
    case.status = next_status
    case.updated_at = now
    update_row = models.CropHealthCaseUpdate(case_id=case.id, author_id=reviewer.id,
        update_type=body.action, assessment=body.assessment, message=body.message, created_at=now)
    db.add(update_row)
    db.commit()
    db.refresh(case)
    return _crop_health_case_payload(db, case, include_updates=True)


@app.post("/v1/crop-health/cases/{case_id}/reply", status_code=201)
def farmer_reply_crop_health_case(case_id: str, body: CropHealthFarmerReply,
                                  db: Session = Depends(get_db), farmer: models.Farmer = Depends(current_farmer)):
    case = _crop_health_farmer_case(db, case_id, farmer)
    if case.status != "awaiting_farmer":
        raise HTTPException(status_code=409, detail="A reply is only available when a reviewer has requested more information.")
    now = datetime.now(timezone.utc)
    case.status = "under_review"
    case.updated_at = now
    db.add(models.CropHealthCaseUpdate(case_id=case.id, author_id=farmer.id,
        update_type="farmer_reply", message=body.message, created_at=now))
    db.commit()
    db.refresh(case)
    return _crop_health_case_payload(db, case, include_updates=True)


@app.get("/v1/farms", response_model=list[FarmOut])
def list_farms(db: Session = Depends(get_db), farmer: models.Farmer = Depends(current_farmer)):
    return list(db.scalars(select(models.Farm).where(models.Farm.owner_id == farmer.id).order_by(models.Farm.created_at)))


@app.post("/v1/farms", response_model=FarmOut, status_code=201)
def create_farm(body: FarmCreate, db: Session = Depends(get_db), farmer: models.Farmer = Depends(current_farmer)):
    farm = models.Farm(owner_id=farmer.id, name=body.name.strip(), district=body.district.strip(), sector=body.sector.strip() if body.sector else None, area_ha=body.area_ha)
    db.add(farm); db.commit(); db.refresh(farm)
    return farm


@app.get("/v1/farms/{farm_id}", response_model=FarmOut)
def get_farm(farm_id: str, db: Session = Depends(get_db), farmer: models.Farmer = Depends(current_farmer)):
    return _owned_farm(farm_id, farmer.id, db)


@app.put("/v1/farms/{farm_id}", response_model=FarmOut)
def update_farm(farm_id: str, body: FarmUpdate, db: Session = Depends(get_db), farmer: models.Farmer = Depends(current_farmer)):
    farm = _owned_farm(farm_id, farmer.id, db)
    for key, value in body.model_dump().items():
        setattr(farm, key, value)
    db.commit(); db.refresh(farm)
    return farm


@app.delete("/v1/farms/{farm_id}", status_code=204)
def delete_farm(farm_id: str, db: Session = Depends(get_db), farmer: models.Farmer = Depends(current_farmer)):
    farm = _owned_farm(farm_id, farmer.id, db)
    db.delete(farm); db.commit()


@app.get("/v1/farms/{farm_id}/fields", response_model=list[FieldOut])
def list_fields(farm_id: str, db: Session = Depends(get_db), farmer: models.Farmer = Depends(current_farmer)):
    _owned_farm(farm_id, farmer.id, db)
    return list(db.scalars(select(models.FarmField).where(
        models.FarmField.farm_id == farm_id, models.FarmField.archived_at.is_(None)
    ).order_by(models.FarmField.created_at)))


@app.post("/v1/farms/{farm_id}/fields", response_model=FieldOut, status_code=201)
def create_field(farm_id: str, body: FieldCreate, db: Session = Depends(get_db), farmer: models.Farmer = Depends(current_farmer)):
    _owned_farm(farm_id, farmer.id, db)
    row = models.FarmField(farm_id=farm_id, **body.model_dump())
    db.add(row); db.commit(); db.refresh(row)
    return row


@app.put("/v1/farms/{farm_id}/fields/{field_id}", response_model=FieldOut)
def update_field(farm_id: str, field_id: str, body: FieldCreate, db: Session = Depends(get_db), farmer: models.Farmer = Depends(current_farmer)):
    _owned_farm(farm_id, farmer.id, db)
    row = db.scalar(select(models.FarmField).where(models.FarmField.farm_id == farm_id, models.FarmField.id == field_id))
    if row is None:
        raise HTTPException(404, detail="Field was not found.")
    if row.archived_at is not None:
        raise HTTPException(409, detail="Archived fields cannot be changed.")
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    db.commit(); db.refresh(row)
    return row


@app.post("/v1/farms/{farm_id}/fields/{field_id}/archive", response_model=FieldOut)
def archive_field(farm_id: str, field_id: str, db: Session = Depends(get_db), farmer: models.Farmer = Depends(current_farmer)):
    _owned_farm(farm_id, farmer.id, db)
    row = db.scalar(select(models.FarmField).where(models.FarmField.farm_id == farm_id, models.FarmField.id == field_id))
    if row is None:
        raise HTTPException(404, detail="Field was not found.")
    if row.archived_at is None:
        row.archived_at = datetime.now(timezone.utc)
        db.commit(); db.refresh(row)
    return row


@app.get("/v1/farms/{farm_id}/activities", response_model=list[ActivityOut])
def list_activities(farm_id: str, db: Session = Depends(get_db), farmer: models.Farmer = Depends(current_farmer)):
    _owned_farm(farm_id, farmer.id, db)
    rows = db.scalars(select(models.FarmActivity).where(models.FarmActivity.farm_id == farm_id).order_by(models.FarmActivity.event_date.desc())).all()
    result = []
    for row in rows:
        item = ActivityOut.model_validate(row, from_attributes=True).model_dump()
        item["review_status"] = _activity_review_status(db, row)
        result.append(item)
    return result


@app.get("/v1/farms/{farm_id}/timeline", response_model=FarmTimelineOut)
def farm_timeline(
    farm_id: str,
    limit: int = Query(default=300, ge=1, le=500),
    db: Session = Depends(get_db),
    farmer: models.Farmer = Depends(current_farmer),
):
    """Read-only, owner-scoped view over existing dated farm records."""
    farm = _owned_farm(farm_id, farmer.id, db)
    fields = {row.id: row.name for row in db.scalars(
        select(models.FarmField).where(models.FarmField.farm_id == farm_id)
    ).all()}
    entries: list[FarmTimelineEntryOut] = []

    def add(record_id, event_date, event_type, field_id, description, source_label, href):
        entries.append(FarmTimelineEntryOut(
            id=f"{event_type}:{record_id}", event_date=event_date, event_type=event_type,
            farm_id=farm.id, farm_name=farm.name, field_id=field_id,
            field_name=fields.get(field_id) if field_id else None,
            description=description, source_label=source_label, href=href,
        ))

    plans = db.scalars(select(models.CropPlan).where(
        models.CropPlan.farm_id == farm_id
    ).order_by(models.CropPlan.created_at.desc()).limit(limit + 1)).all()
    plan_ids_with_planting_dates = set()
    for row in plans:
        add(row.id, row.created_at.date() if row.created_at else None, "crop_plan_created", row.field_id,
            f"Crop plan saved for {row.crop}, Season {row.season}.",
            "Provisional CropPulse planning record", "#crop-plans-title")
        if row.actual_planting_date:
            plan_ids_with_planting_dates.add(row.id)
            add(row.id, row.actual_planting_date, "planting_recorded", row.field_id,
                f"Planting date recorded for {row.crop}, Season {row.season}.",
                "Farmer reported", "#crop-plans-title")

    activities = db.scalars(select(models.FarmActivity).where(
        models.FarmActivity.farm_id == farm_id
    ).order_by(models.FarmActivity.event_date.desc()).limit(limit + 1)).all()
    for row in activities:
        idempotency_parts = (row.idempotency_key or "").split(":")
        if (row.activity_type.casefold() == "planting" and len(idempotency_parts) == 3
                and idempotency_parts[0] == "plan" and idempotency_parts[1] in plan_ids_with_planting_dates
                and idempotency_parts[2] == "planted"):
            # The plan's actual date and this generated activity are the same persisted event.
            continue
        description = f"{row.activity_type} recorded for {row.crop}, Season {row.season}."
        if row.quantity is not None:
            description += f" Quantity: {row.quantity:g} {row.unit or '(unit not recorded)'}."
        source_label = "Farmer reported" if row.verification in {"user_reported", "farmer_reported"} else f"Recorded as {row.verification.replace('_', ' ')}"
        add(row.id, row.event_date, "activity", None, description, source_label, "#activity-history-title")

    irrigation = db.scalars(select(models.IrrigationRecord).where(
        models.IrrigationRecord.farm_id == farm_id
    ).order_by(models.IrrigationRecord.event_date.desc()).limit(limit + 1)).all()
    for row in irrigation:
        description = f"Water-management event: {row.water_source.replace('_', ' ')}; method {row.irrigation_method.replace('_', ' ')}."
        if row.water_quantity is not None:
            description += f" Recorded quantity: {row.water_quantity:g} {row.water_quantity_unit}."
        add(row.id, row.event_date, "irrigation", row.field_id, description, "Farmer reported", "#irrigation-log-title")

    observations = db.scalars(select(models.SoilObservation).where(
        models.SoilObservation.farm_id == farm_id
    ).order_by(models.SoilObservation.observation_date.desc()).limit(limit + 1)).all()
    for row in observations:
        details = row.soil_description or row.drainage_observation or row.erosion_observation
        description = "Soil observation recorded" + (f": {details}." if details else ".")
        add(row.id, row.observation_date, "soil_observation", row.field_id, description, "Farmer reported", "#soil-records-title")

    soil_tests = db.scalars(select(models.SoilTestRecord).where(
        models.SoilTestRecord.farm_id == farm_id
    ).order_by(models.SoilTestRecord.test_date.desc()).limit(limit + 1)).all()
    for row in soil_tests:
        measurements = []
        if row.ph_value is not None: measurements.append(f"pH {row.ph_value:g}")
        for label, value, unit in (("N", row.nitrogen_value, row.nitrogen_unit), ("P", row.phosphorus_value, row.phosphorus_unit),
                                   ("K", row.potassium_value, row.potassium_unit), ("organic matter", row.organic_matter_value, row.organic_matter_unit)):
            if value is not None: measurements.append(f"{label} {value:g} {unit}")
        description = "Soil-test values entered" + (f": {', '.join(measurements)}." if measurements else "; no measurements recorded.")
        add(row.id, row.test_date, "soil_test", row.field_id, description, "Farmer entered; source not independently verified", "#soil-tests-title")

    harvests = db.scalars(select(models.FarmHarvest).where(
        models.FarmHarvest.farm_id == farm_id
    ).order_by(models.FarmHarvest.harvest_date.desc()).limit(limit + 1)).all()
    for row in harvests:
        add(row.id, row.harvest_date, "harvest", row.field_id,
            f"Harvest recorded for {row.crop}, Season {row.season}: {row.quantity:g} {row.quantity_unit}.",
            "Farmer reported", "#harvest-records-title")
    post_harvest = db.execute(select(
        models.HarvestObservation, models.FarmHarvest.field_id, models.FarmHarvest.crop
    ).join(models.FarmHarvest, models.HarvestObservation.harvest_id == models.FarmHarvest.id).where(
        models.FarmHarvest.farm_id == farm_id
    ).order_by(models.HarvestObservation.observed_date.desc()).limit(limit + 1)).all()
    for row, field_id, crop in post_harvest:
        detail = row.condition or row.storage_method
        description = f"Post-harvest observation for {crop}" + (f": {detail}." if detail else ".")
        add(row.id, row.observed_date, "post_harvest_observation", field_id,
            description, "Farmer reported", "#harvest-records-title")

    entries.sort(key=lambda item: (item.event_date or date.min, item.id), reverse=True)
    return FarmTimelineOut(entries=entries[:limit], has_more=len(entries) > limit)


@app.post("/v1/farms/{farm_id}/activities", response_model=ActivityOut, status_code=201)
def create_activity(farm_id: str, body: ActivityCreate, db: Session = Depends(get_db), farmer: models.Farmer = Depends(current_farmer)):
    _owned_farm(farm_id, farmer.id, db)
    values = body.model_dump()
    if values.get("idempotency_key"):
        prior = db.scalar(select(models.FarmActivity).where(models.FarmActivity.farm_id == farm_id, models.FarmActivity.idempotency_key == values["idempotency_key"]))
        if prior:
            return prior
    values["verification"] = "user_reported"
    row = models.FarmActivity(farm_id=farm_id, **values)
    db.add(row); db.commit(); db.refresh(row)
    return row


@app.put("/v1/farms/{farm_id}/activities/{activity_id}", response_model=ActivityOut)
def update_activity(farm_id: str, activity_id: str, body: ActivityUpdate, db: Session = Depends(get_db), farmer: models.Farmer = Depends(current_farmer)):
    _owned_farm(farm_id, farmer.id, db)
    row = db.scalar(select(models.FarmActivity).where(models.FarmActivity.id == activity_id, models.FarmActivity.farm_id == farm_id))
    if row is None: raise HTTPException(404, detail="Activity was not found.")
    for key, value in body.model_dump().items(): setattr(row, key, value)
    db.commit(); db.refresh(row)
    return row


@app.delete("/v1/farms/{farm_id}/activities/{activity_id}", status_code=204)
def delete_activity(farm_id: str, activity_id: str, db: Session = Depends(get_db), farmer: models.Farmer = Depends(current_farmer)):
    _owned_farm(farm_id, farmer.id, db)
    row = db.scalar(select(models.FarmActivity).where(models.FarmActivity.id == activity_id, models.FarmActivity.farm_id == farm_id))
    if row is None: raise HTTPException(404, detail="Activity was not found.")
    db.delete(row); db.commit()


def _validate_irrigation_links(farm_id: str, body: IrrigationRecordCreate, db: Session) -> str | None:
    field_id = body.field_id
    plan = None
    if body.crop_plan_id:
        plan = db.scalar(select(models.CropPlan).where(
            models.CropPlan.id == body.crop_plan_id,
            models.CropPlan.farm_id == farm_id,
        ))
        if plan is None:
            raise HTTPException(404, detail="Crop plan was not found for this farm.")
        if plan.field_id and field_id and plan.field_id != field_id:
            raise HTTPException(422, detail="Irrigation field must match the selected crop plan's field.")
        if field_id is None:
            field_id = plan.field_id

    if field_id and db.scalar(select(models.FarmField.id).where(
        models.FarmField.id == field_id,
        models.FarmField.farm_id == farm_id,
    )) is None:
        raise HTTPException(404, detail="Field was not found for this farm.")
    return field_id


def _owned_irrigation_record(farm_id: str, record_id: str, farmer_id: str,
                             db: Session) -> models.IrrigationRecord:
    _owned_farm(farm_id, farmer_id, db)
    row = db.scalar(select(models.IrrigationRecord).where(
        models.IrrigationRecord.id == record_id,
        models.IrrigationRecord.farm_id == farm_id,
    ))
    if row is None:
        raise HTTPException(404, detail="Irrigation record was not found.")
    return row


def _validate_soil_field(farm_id: str, field_id: str | None, db: Session) -> None:
    if field_id and db.scalar(select(models.FarmField.id).where(
        models.FarmField.id == field_id,
        models.FarmField.farm_id == farm_id,
    )) is None:
        raise HTTPException(status_code=404, detail="Field was not found for this farm.")


def _owned_soil_record(model, farm_id: str, record_id: str, farmer_id: str, db: Session):
    _owned_farm(farm_id, farmer_id, db)
    row = db.scalar(select(model).where(model.id == record_id, model.farm_id == farm_id))
    if row is None:
        raise HTTPException(status_code=404, detail="Soil record was not found.")
    return row


@app.get("/v1/farms/{farm_id}/soil-observations", response_model=list[SoilObservationOut])
def list_soil_observations(farm_id: str, db: Session = Depends(get_db),
                           farmer: models.Farmer = Depends(current_farmer)):
    _owned_farm(farm_id, farmer.id, db)
    return db.scalars(select(models.SoilObservation).where(
        models.SoilObservation.farm_id == farm_id
    ).order_by(models.SoilObservation.observation_date.desc(), models.SoilObservation.created_at.desc())).all()


@app.post("/v1/farms/{farm_id}/soil-observations", response_model=SoilObservationOut, status_code=201)
def create_soil_observation(farm_id: str, body: SoilObservationCreate, db: Session = Depends(get_db),
                            farmer: models.Farmer = Depends(current_farmer)):
    _owned_farm(farm_id, farmer.id, db)
    _validate_soil_field(farm_id, body.field_id, db)
    row = models.SoilObservation(farm_id=farm_id, **body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@app.get("/v1/farms/{farm_id}/soil-observations/{record_id}", response_model=SoilObservationOut)
def get_soil_observation(farm_id: str, record_id: str, db: Session = Depends(get_db),
                         farmer: models.Farmer = Depends(current_farmer)):
    return _owned_soil_record(models.SoilObservation, farm_id, record_id, farmer.id, db)


@app.put("/v1/farms/{farm_id}/soil-observations/{record_id}", response_model=SoilObservationOut)
def update_soil_observation(farm_id: str, record_id: str, body: SoilObservationCreate,
                            db: Session = Depends(get_db), farmer: models.Farmer = Depends(current_farmer)):
    row = _owned_soil_record(models.SoilObservation, farm_id, record_id, farmer.id, db)
    _validate_soil_field(farm_id, body.field_id, db)
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


@app.get("/v1/farms/{farm_id}/soil-tests", response_model=list[SoilTestRecordOut])
def list_soil_test_records(farm_id: str, db: Session = Depends(get_db),
                           farmer: models.Farmer = Depends(current_farmer)):
    _owned_farm(farm_id, farmer.id, db)
    return db.scalars(select(models.SoilTestRecord).where(
        models.SoilTestRecord.farm_id == farm_id
    ).order_by(models.SoilTestRecord.test_date.desc(), models.SoilTestRecord.created_at.desc())).all()


@app.post("/v1/farms/{farm_id}/soil-tests", response_model=SoilTestRecordOut, status_code=201)
def create_soil_test_record(farm_id: str, body: SoilTestRecordCreate, db: Session = Depends(get_db),
                            farmer: models.Farmer = Depends(current_farmer)):
    _owned_farm(farm_id, farmer.id, db)
    _validate_soil_field(farm_id, body.field_id, db)
    row = models.SoilTestRecord(farm_id=farm_id, **body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@app.get("/v1/farms/{farm_id}/soil-tests/{record_id}", response_model=SoilTestRecordOut)
def get_soil_test_record(farm_id: str, record_id: str, db: Session = Depends(get_db),
                         farmer: models.Farmer = Depends(current_farmer)):
    return _owned_soil_record(models.SoilTestRecord, farm_id, record_id, farmer.id, db)


@app.put("/v1/farms/{farm_id}/soil-tests/{record_id}", response_model=SoilTestRecordOut)
def update_soil_test_record(farm_id: str, record_id: str, body: SoilTestRecordCreate,
                            db: Session = Depends(get_db), farmer: models.Farmer = Depends(current_farmer)):
    row = _owned_soil_record(models.SoilTestRecord, farm_id, record_id, farmer.id, db)
    _validate_soil_field(farm_id, body.field_id, db)
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


@app.get("/v1/farms/{farm_id}/irrigation-records", response_model=list[IrrigationRecordOut])
def list_irrigation_records(farm_id: str, db: Session = Depends(get_db),
                            farmer: models.Farmer = Depends(current_farmer)):
    _owned_farm(farm_id, farmer.id, db)
    return db.scalars(select(models.IrrigationRecord).where(
        models.IrrigationRecord.farm_id == farm_id
    ).order_by(models.IrrigationRecord.event_date.desc(), models.IrrigationRecord.created_at.desc())).all()


@app.get("/v1/farms/{farm_id}/irrigation-records/{record_id}", response_model=IrrigationRecordOut)
def get_irrigation_record(farm_id: str, record_id: str, db: Session = Depends(get_db),
                          farmer: models.Farmer = Depends(current_farmer)):
    return _owned_irrigation_record(farm_id, record_id, farmer.id, db)


@app.post("/v1/farms/{farm_id}/irrigation-records", response_model=IrrigationRecordOut, status_code=201)
def create_irrigation_record(farm_id: str, body: IrrigationRecordCreate,
                             db: Session = Depends(get_db),
                             farmer: models.Farmer = Depends(current_farmer)):
    _owned_farm(farm_id, farmer.id, db)
    values = body.model_dump()
    values["field_id"] = _validate_irrigation_links(farm_id, body, db)
    row = models.IrrigationRecord(farm_id=farm_id, **values)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@app.put("/v1/farms/{farm_id}/irrigation-records/{record_id}", response_model=IrrigationRecordOut)
def update_irrigation_record(farm_id: str, record_id: str, body: IrrigationRecordCreate,
                             db: Session = Depends(get_db),
                             farmer: models.Farmer = Depends(current_farmer)):
    row = _owned_irrigation_record(farm_id, record_id, farmer.id, db)
    values = body.model_dump()
    values["field_id"] = _validate_irrigation_links(farm_id, body, db)
    for key, value in values.items():
        setattr(row, key, value)
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


@app.delete("/v1/farms/{farm_id}/irrigation-records/{record_id}", status_code=204)
def delete_irrigation_record(farm_id: str, record_id: str,
                             db: Session = Depends(get_db),
                             farmer: models.Farmer = Depends(current_farmer)):
    row = _owned_irrigation_record(farm_id, record_id, farmer.id, db)
    db.delete(row)
    db.commit()


def _harvest_payload(row: models.FarmHarvest) -> dict:
    return {
        "id": row.id,
        "farm_id": row.farm_id,
        "field_id": row.field_id,
        "crop_plan_id": row.crop_plan_id,
        "crop": row.crop,
        "season": row.season,
        "harvest_date": row.harvest_date,
        "harvested_area": row.harvested_area,
        "area_unit": row.area_unit,
        "quantity": row.quantity,
        "quantity_unit": row.quantity_unit,
        "loss_quantity": row.loss_quantity,
        "post_harvest_observations": row.post_harvest_observations,
        "notes": row.notes,
        "yield_kg_ha": yield_kg_per_hectare(row.harvested_area, row.area_unit, row.quantity, row.quantity_unit),
        "yield_calculation": yield_calculation(row.harvested_area, row.area_unit, row.quantity, row.quantity_unit),
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _validate_harvest_links(farm_id: str, body: HarvestCreate, db: Session) -> str | None:
    field_id = body.field_id
    plan = None
    if body.crop_plan_id:
        plan = db.scalar(select(models.CropPlan).where(
            models.CropPlan.id == body.crop_plan_id, models.CropPlan.farm_id == farm_id
        ))
        if plan is None:
            raise HTTPException(404, detail="Crop plan was not found for this farm.")
        if plan.crop != body.crop or plan.season != body.season:
            raise HTTPException(422, detail="Harvest crop and season must match the selected crop plan.")
        if plan.field_id and field_id and plan.field_id != field_id:
            raise HTTPException(422, detail="Harvest field must match the selected crop plan's field.")
        if field_id is None:
            field_id = plan.field_id

    if field_id and db.scalar(select(models.FarmField.id).where(
        models.FarmField.id == field_id, models.FarmField.farm_id == farm_id
    )) is None:
        raise HTTPException(404, detail="Field was not found for this farm.")
    return field_id


@app.get("/v1/farms/{farm_id}/harvests", response_model=list[HarvestOut])
def list_harvests(farm_id: str, db: Session = Depends(get_db), farmer: models.Farmer = Depends(current_farmer)):
    _owned_farm(farm_id, farmer.id, db)
    rows = db.scalars(select(models.FarmHarvest).where(
        models.FarmHarvest.farm_id == farm_id
    ).order_by(models.FarmHarvest.harvest_date.desc(), models.FarmHarvest.created_at.desc()))
    return [_harvest_payload(row) for row in rows]


@app.post("/v1/farms/{farm_id}/harvests", response_model=HarvestOut, status_code=201)
def create_harvest(farm_id: str, body: HarvestCreate, db: Session = Depends(get_db), farmer: models.Farmer = Depends(current_farmer)):
    _owned_farm(farm_id, farmer.id, db)
    values = body.model_dump()
    values["field_id"] = _validate_harvest_links(farm_id, body, db)
    row = models.FarmHarvest(farm_id=farm_id, **values)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _harvest_payload(row)


@app.put("/v1/farms/{farm_id}/harvests/{harvest_id}", response_model=HarvestOut)
def update_harvest(farm_id: str, harvest_id: str, body: HarvestCreate,
                   db: Session = Depends(get_db), farmer: models.Farmer = Depends(current_farmer)):
    _owned_farm(farm_id, farmer.id, db)
    row = db.scalar(select(models.FarmHarvest).where(
        models.FarmHarvest.id == harvest_id, models.FarmHarvest.farm_id == farm_id
    ))
    if row is None:
        raise HTTPException(404, detail="Harvest record was not found.")
    values = body.model_dump()
    values["field_id"] = _validate_harvest_links(farm_id, body, db)
    for key, value in values.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return _harvest_payload(row)


def _owned_harvest(farm_id: str, harvest_id: str, farmer_id: str, db: Session) -> models.FarmHarvest:
    _owned_farm(farm_id, farmer_id, db)
    row = db.scalar(select(models.FarmHarvest).where(
        models.FarmHarvest.id == harvest_id, models.FarmHarvest.farm_id == farm_id
    ))
    if row is None:
        raise HTTPException(404, detail="Harvest record was not found.")
    return row


def _owned_harvest_observation(harvest: models.FarmHarvest, observation_id: str, db: Session) -> models.HarvestObservation:
    row = db.scalar(select(models.HarvestObservation).where(
        models.HarvestObservation.id == observation_id,
        models.HarvestObservation.harvest_id == harvest.id,
    ))
    if row is None:
        raise HTTPException(404, detail="Post-harvest observation was not found.")
    return row


@app.get("/v1/farms/{farm_id}/harvests/{harvest_id}/observations", response_model=list[HarvestObservationOut])
def list_harvest_observations(farm_id: str, harvest_id: str, db: Session = Depends(get_db),
                              farmer: models.Farmer = Depends(current_farmer)):
    harvest = _owned_harvest(farm_id, harvest_id, farmer.id, db)
    return db.scalars(select(models.HarvestObservation).where(
        models.HarvestObservation.harvest_id == harvest.id
    ).order_by(models.HarvestObservation.observed_date.desc(), models.HarvestObservation.created_at.desc())).all()


@app.post("/v1/farms/{farm_id}/harvests/{harvest_id}/observations", response_model=HarvestObservationOut, status_code=201)
def create_harvest_observation(farm_id: str, harvest_id: str, body: HarvestObservationCreate,
                               db: Session = Depends(get_db), farmer: models.Farmer = Depends(current_farmer)):
    harvest = _owned_harvest(farm_id, harvest_id, farmer.id, db)
    if body.observed_date < harvest.harvest_date:
        raise HTTPException(422, detail="Observation date cannot be before the linked harvest date.")
    row = models.HarvestObservation(harvest_id=harvest.id, **body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@app.put("/v1/farms/{farm_id}/harvests/{harvest_id}/observations/{observation_id}", response_model=HarvestObservationOut)
def update_harvest_observation(farm_id: str, harvest_id: str, observation_id: str,
                               body: HarvestObservationCreate, db: Session = Depends(get_db),
                               farmer: models.Farmer = Depends(current_farmer)):
    harvest = _owned_harvest(farm_id, harvest_id, farmer.id, db)
    row = _owned_harvest_observation(harvest, observation_id, db)
    if body.observed_date < harvest.harvest_date:
        raise HTTPException(422, detail="Observation date cannot be before the linked harvest date.")
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


@app.get("/v1/farms/{farm_id}/plans", response_model=list[PlanOut])
def list_plans(farm_id: str, db: Session = Depends(get_db), farmer: models.Farmer = Depends(current_farmer)):
    _owned_farm(farm_id, farmer.id, db)
    rows = db.scalars(select(models.CropPlan).where(models.CropPlan.farm_id == farm_id).order_by(models.CropPlan.created_at.desc()))
    result = []
    for row in rows:
        result.append({"id": row.id, "farm_id": row.farm_id, "district": row.district, "crop": row.crop,
                       "season": row.season, "planting_date": row.planting_date, "area_ha": row.area_ha,
                       "plan": json.loads(row.plan_json), "verification": row.verification,
                       "status": row.status, "actual_planting_date": row.actual_planting_date,
                       "field_id": row.field_id,
                       "evidence": [{"id": item.id, "claim": item.claim, "crop": item.crop,
                           "geographic_applicability": item.geographic_applicability,
                           "source_name": item.source_name, "source_organization": item.source_organization,
                           "source_url": item.source_url, "source_identifier": item.source_identifier,
                           "publication_date": item.publication_date, "retrieval_date": item.retrieval_date,
                           "evidence_period": item.evidence_period, "units": item.units,
                           "confidence": item.confidence, "limitations": item.limitations,
                           "dataset_version": item.dataset_version, "recommender_version": item.recommender_version,
                           "generated_at": item.generated_at, "verification_status": item.verification_status}
                           for item in row.evidence]})
    return result


@app.post("/v1/farms/{farm_id}/plans", response_model=PlanOut, status_code=201)
def create_plan(farm_id: str, body: PlanCreate, db: Session = Depends(get_db), farmer: models.Farmer = Depends(current_farmer)):
    _owned_farm(farm_id, farmer.id, db)
    if body.field_id and db.scalar(select(models.FarmField.id).where(
        models.FarmField.id == body.field_id, models.FarmField.farm_id == farm_id,
        models.FarmField.archived_at.is_(None)
    )) is None:
        raise HTTPException(404, detail="An active field on this farm was not found.")
    row = models.CropPlan(farm_id=farm_id, district=body.district.strip(), crop=body.crop.strip(), season=body.season,
                          planting_date=body.planting_date, area_ha=body.area_ha, field_id=body.field_id,
                          plan_json=json.dumps(body.plan, allow_nan=False), verification="provisional")
    db.add(row)
    db.add(models.FarmActivity(farm_id=farm_id, district=body.district.strip(), crop=body.crop.strip(), season=body.season,
                               activity_type="Seasonal plan", event_date=body.planting_date, area_ha=body.area_ha,
                               unit="ha", notes="Saved from Crop Plan; guidance remains provisional.", verification="user_reported"))
    db.commit(); db.refresh(row)
    return {"id": row.id, "farm_id": row.farm_id, "district": row.district, "crop": row.crop, "season": row.season,
            "planting_date": row.planting_date, "area_ha": row.area_ha, "plan": body.plan,
            "verification": row.verification, "status": row.status, "actual_planting_date": row.actual_planting_date,
            "field_id": row.field_id, "evidence": []}


@app.put("/v1/farms/{farm_id}/plans/{plan_id}", response_model=PlanOut)
def replace_crop_plan(farm_id: str, plan_id: str, body: PlanUpdate,
                      db: Session = Depends(get_db), farmer: models.Farmer = Depends(current_farmer)):
    _owned_farm(farm_id, farmer.id, db)
    row = db.scalar(select(models.CropPlan).where(
        models.CropPlan.id == plan_id, models.CropPlan.farm_id == farm_id
    ))
    if row is None:
        raise HTTPException(404, detail="Crop plan was not found.")
    if row.status not in {"draft", "planned"}:
        raise HTTPException(409, detail="Only draft or planned crop plans can be edited.")
    if body.field_id and db.scalar(select(models.FarmField.id).where(
        models.FarmField.id == body.field_id, models.FarmField.farm_id == farm_id,
        models.FarmField.archived_at.is_(None)
    )) is None:
        raise HTTPException(404, detail="An active field on this farm was not found.")
    row.district = body.district
    row.crop = body.crop
    row.season = body.season
    row.planting_date = body.planting_date
    row.area_ha = body.area_ha
    row.field_id = body.field_id
    row.plan_json = json.dumps(body.plan, allow_nan=False)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "farm_id": row.farm_id, "district": row.district, "crop": row.crop,
            "season": row.season, "planting_date": row.planting_date, "area_ha": row.area_ha,
            "plan": json.loads(row.plan_json), "verification": row.verification,
            "status": row.status, "actual_planting_date": row.actual_planting_date,
            "field_id": row.field_id, "evidence": [
                {"id": item.id, "claim": item.claim, "crop": item.crop,
                 "geographic_applicability": item.geographic_applicability,
                 "source_name": item.source_name, "source_organization": item.source_organization,
                 "source_url": item.source_url, "source_identifier": item.source_identifier,
                 "publication_date": item.publication_date, "retrieval_date": item.retrieval_date,
                 "evidence_period": item.evidence_period, "units": item.units,
                 "confidence": item.confidence, "limitations": item.limitations,
                 "dataset_version": item.dataset_version, "recommender_version": item.recommender_version,
                 "generated_at": item.generated_at, "verification_status": item.verification_status}
                for item in row.evidence]}


@app.patch("/v1/farms/{farm_id}/plans/{plan_id}/status", response_model=PlanOut)
def update_plan_status(farm_id: str, plan_id: str, body: PlanStatusUpdate,
                       db: Session = Depends(get_db), farmer: models.Farmer = Depends(current_farmer)):
    _owned_farm(farm_id, farmer.id, db)
    row = db.scalar(select(models.CropPlan).where(
        models.CropPlan.id == plan_id, models.CropPlan.farm_id == farm_id
    ))
    if row is None:
        raise HTTPException(404, detail="Crop plan was not found.")
    if body.status == row.status:
        if body.actual_planting_date == row.actual_planting_date:
            return {"id": row.id, "farm_id": row.farm_id, "district": row.district, "crop": row.crop,
                    "season": row.season, "planting_date": row.planting_date, "area_ha": row.area_ha,
                    "plan": json.loads(row.plan_json), "verification": row.verification,
                    "status": row.status, "actual_planting_date": row.actual_planting_date}
        raise HTTPException(409, detail="Crop plan is already in that status with different planting details.")
    if body.status not in PLAN_STATUS_TRANSITIONS.get(row.status, set()):
        raise HTTPException(409, detail=f"Crop plan cannot transition from '{row.status}' to '{body.status}'.")
    if body.status == "planted" and body.actual_planting_date > datetime.now(timezone.utc).date():
        raise HTTPException(422, detail="Actual planting date cannot be in the future.")
    row.status = body.status
    if body.status == "planted":
        row.actual_planting_date = body.actual_planting_date
        db.add(models.FarmActivity(
            farm_id=farm_id, district=row.district, crop=row.crop, season=row.season,
            activity_type="Planting", event_date=body.actual_planting_date,
            area_ha=None, unit=None, notes=f"Farmer confirmed planting for crop plan {row.id}.",
            verification="user_reported", idempotency_key=f"plan:{row.id}:planted",
        ))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        db.refresh(row)
        if row.status == body.status and row.actual_planting_date == body.actual_planting_date:
            return {"id": row.id, "farm_id": row.farm_id, "district": row.district, "crop": row.crop,
                    "season": row.season, "planting_date": row.planting_date, "area_ha": row.area_ha,
                    "plan": json.loads(row.plan_json), "verification": row.verification,
                    "status": row.status, "actual_planting_date": row.actual_planting_date}
        raise HTTPException(409, detail="Crop plan changed while the status update was being saved.")
    db.refresh(row)
    return {"id": row.id, "farm_id": row.farm_id, "district": row.district, "crop": row.crop,
            "season": row.season, "planting_date": row.planting_date, "area_ha": row.area_ha,
            "plan": json.loads(row.plan_json), "verification": row.verification,
            "status": row.status, "actual_planting_date": row.actual_planting_date}
