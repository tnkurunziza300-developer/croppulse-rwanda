# Frontend and backend contract

## Current frontend phase

Streamlit remains supported during a staged migration to the React/TypeScript/Vite farmer workspace. Both clients use the same FastAPI service and persistent database. Streamlit uses the existing bearer API contract through `backend/client.py`; React uses credentialed HttpOnly browser sessions and a signed CSRF token through `frontend/src/api.ts`. React farmer farms, fields, crop plans, activities, and point-weather forecasts use the existing API. With an explicit save confirmation, the latest forecast per account and coordinate is persisted owner-scoped in the database; Streamlit's weather flow remains session-only. Analytics demonstration data remains separate from farmer account records. Streamlit-only workflows remain available until their React replacements are implemented and checked. Live market feeds are not connected. See [weather workflow and limits](weather.md), [Phase 1 setup and boundaries](backend-phase-1.md), and [React setup](react-app-setup.md).

`utils/frontend_services.py` is the Streamlit adapter; React uses a typed API layer with centralized errors in `frontend/src/api.ts`. UI pages should call these service boundaries rather than handling persistence directly. `utils/service_contracts.py` defines the initial Python domain shapes and protocols.

The React weather page also calls authenticated `GET /v1/weather/climate-data`, with optional `year`, `record_type` (`monthly_outlook` or `seasonal_outlook`), and `search` filters. This returns source-linked nationwide rainfall outlook transcriptions from METEO RWANDA bulletin PDFs; it is separate from farm observations and Open-Meteo point forecasts. See [weather workflow and source limitations](weather.md).

## Service boundary

Phase 1 now implements authenticated FastAPI services for farmer profiles, farms, crop plans, farm activities, browser sessions, account administration, reviewer district scope, review decisions, and administrative audit events. Setup, schema, owner permissions, and current integration boundaries are documented in [backend-phase-1.md](backend-phase-1.md). Other endpoints below remain proposed unless explicitly listed there.

Suggested initial endpoints:

| Method and path | Purpose | Access |
| --- | --- | --- |
| `GET /v1/reference/crops?district_id=...&season=...` | List supported crops and applicable reference metadata | Public |
| `GET /v1/reference/districts?province_id=...` | List canonical Rwanda locations and hierarchy | Public |
| `POST /v1/recommendations` | Generate a scoped recommendation with evidence and limitations | Public or signed-in |
| `POST /v1/plans` | Create a provisional field plan from validated inputs and return activities | Public or signed-in |
| `GET /v1/me/farm-records` | List the signed-in user's records with pagination | Farmer |
| `POST /v1/me/farm-records` | Create a farmer-reported record | Farmer |
| `PATCH /v1/me/farm-records/{id}` | Edit an owned record with version/ETag conflict protection | Owner |
| `DELETE /v1/me/farm-records/{id}` | Delete an owned record, with audit event | Owner |
| `GET /v1/market-quotes` | Retrieve quotes with source, unit, place, observed time and verification state | Public or signed-in, per policy |
| `POST /v1/market-quotes` | Submit an attributed observation for review | Signed-in contributor |
| `POST /v1/extension-visits` | Submit a visit record and follow-up action | Authorized extension officer |
| `POST /v1/cooperative-activities` | Submit aggregate cooperative activity and member reach (no member roster) | Authorized cooperative officer |
| `POST /v1/pest-reports` | Submit farmer-observed symptoms for triage; never an automatic diagnosis | Signed-in farmer |
| `POST /v1/recommendation-feedback` | Record rating and optional comment against a recommendation version | Signed-in user |
| `POST /v1/guidance-reviews` | Submit a correction with source evidence | Authenticated reviewer |
| `GET /v1/weather/forecast?district=...` | Retrieve licensed provider forecast with location, issue time, expiry, provider and units | Public |
| `POST /v1/weather-observations` | Submit farmer-observed rainfall or temperature with source and timestamp | Signed-in contributor |

Example JSON shapes (field names are proposed and should be versioned before implementation):

```json
POST /v1/me/farm-records
{
  "district_id": "RW-HUYE", "sector_id": null, "crop_id": "maize",
  "season": "A", "record_type": "harvest", "event_date": "2026-06-12",
  "area_ha": 0.5, "quantity": 420, "unit": "kg", "amount_rwf": null,
  "notes": "Farmer-entered"
}

201 Created
{
  "data": {"id": "rec_123", "verification": "user_reported", "version": 1,
            "event_date": "2026-06-12", "district_id": "RW-HUYE"},
  "meta": {"schema_version": "1", "request_id": "req_456"}
}
```

```json
POST /v1/guidance-reviews
{
  "crop_id": "maize", "district_id": "RW-HUYE", "season": "A",
  "suggestion": "Review calendar window", "evidence": [{"url": "https://example.org/source", "title": "Source title"}]
}
```

Recommendation feedback includes the actual generated `recommendation_id` when submitted from a recommendation card. General feedback may omit it; the frontend does not manufacture a backend identifier.

Responses should use the same `{data, meta}` envelope for success and `{error: {code, message, field_errors}, meta}` for failure. Do not return private reporter fields to public endpoints.

## Proposed architecture, models and roles

Use a versioned HTTPS API service between the Streamlit frontend and relational storage. Keep provider adapters (weather, market) behind backend service boundaries; do not expose provider secrets in the frontend. Run background ingestion only when source licensing and freshness rules are agreed. The frontend adapter should map API DTOs to the Python contracts without embedding HTTP details in pages.

Core relationships: `User` owns many `FarmRecord`s and submits many `Feedback` items; `District` has sectors and belongs to a province; `Crop` has versioned guidance and evidence references; `GuidanceReview` targets a guidance version and is decided by a qualified reviewer; `MarketQuote` references crop, market/location, unit, source, observation time and verification state; `ExtensionVisit` has an officer, location, participants/consent policy, and follow-up actions; `WeatherObservation` records source, location, observation time and verification state; provider `Forecast` records provider, location precision, issue/valid time and license metadata. Keep canonical crop/district identifiers stable while display names can be localized.

Authentication should use a vetted identity provider. Roles should be enforced server-side: farmer (own records), extension officer (assigned/consented visits), analyst (approved aggregated statistics), agronomist reviewer (review queue), administrator (account/configuration). Apply least privilege, audit sensitive reads and review decisions, and prevent identifying farm records from entering public aggregate outputs. Define consent, data minimization, retention/deletion, export, backup/encryption, incident response, and data residency before collecting real farmer data. Use database migrations, backups, access logging, rate limits and monitoring as backend-phase work.

Weather integration must be licensed and disclose forecast horizon, issue time, resolution and limitations. Market integrations must document market coverage, quote unit/quality, timestamps, source attribution and stale/missing behavior. Recommendation approvals should be versioned, attributable to a qualified reviewer, scoped by crop/location/season, and reversible with an audit trail; submissions never become approved automatically.

## Data and trust rules

- Preserve farmer-reported, unverified, reviewed, and official states as distinct values. Never promote a submission to verified merely because it was accepted by an endpoint.
- Attach source, observation time, geographic scope, unit, license/usage constraints, and verification status to external evidence.
- Reject invalid units, negative quantities/prices, future observation dates where disallowed, unknown districts, and cross-user record access on the server.
- Return structured errors such as `VALIDATION_ERROR`, `NOT_FOUND`, `FORBIDDEN`, `CONFLICT`, `RATE_LIMITED`, and `PROVIDER_UNAVAILABLE` with field details where safe.
- Keep audit history for review decisions and record ownership changes. Define retention, deletion, consent, backup, and export policies before deployment.
- Do not present forecasts as agronomic certainty. Surface provider timestamp, location precision, uncertainty, and stale status.
- Do not rely on frontend session state for security, identity, durable records, or national statistics.

## Readiness gate

Before connecting a backend, agree the identity provider and roles, privacy/consent rules, canonical crop and district identifiers, units, API schema versioning, data retention, uptime/error behavior, and qualified-review workflow. Then implement a service adapter against a staging API and obtain user approval before any production deployment.
