# React migration audit and target plan

Audit date: 2026-10-16. The worktree has an existing Streamlit app and a separate FastAPI API; the React app must be introduced alongside them. This note records the source and database baseline before any React or schema changes.

## Current architecture and baseline

- `app.py`, `plan.py`, `views.py`, and `product_pages.py` implement the Streamlit experience. `utils/frontend_services.py` manages most form state in Streamlit session state and `backend/client.py` calls the API synchronously with bearer JWTs.
- `backend/api.py` exposes `/health`, farmer registration/login/logout/profile, owner-scoped farms, activities, and crop plans. Farm, plan, and activity requests use the current farmer dependency and hide other farmers' farm IDs with 404 responses. The API has no staff roles, account statuses, reviewer assignments, review API, admin analytics, or audit events.
- `backend/models.py` defines `Farmer`, `FarmerSession`, `Farm`, `CropPlan`, and `FarmActivity`. There is no durable review queue or review history. The existing report-like product pages are still Streamlit session state; they cannot be represented as administrator review records without first defining a persistent submission workflow.
- Authentication is a 30-minute bearer JWT backed by a revocable `farmer_sessions` row. Streamlit keeps the token in server-side session state. There is no browser-cookie login or CSRF protection for a browser app yet.
- Existing API success responses are direct JSON models, validation failures are a sanitized `{detail: [...]}` response, and other errors use FastAPI's `{detail: ...}` shape. Existing API routes and the Streamlit bearer flow must remain compatible.
- Dependencies are in `requirements.txt`; no JavaScript package manifest existed at audit time. Node 24.19.0 and npm 11.17.0 are available locally.
- The current Python suite baseline is **59 passed, 2 warnings** with `python tests/windows_safe_pytest.py`. The warnings are a pytest `anyio` rewrite warning and Starlette's warning about the installed HTTPX test-client integration.

## Database preservation checkpoint

Before schema changes, copies were made under the ignored `.backups/pre-react-migration-20261016/` directory. Both copies passed SQLite `PRAGMA integrity_check` and matched the source table counts.

| Database | Baseline tables and row counts | Alembic revision |
| --- | --- | --- |
| `data/croppulse_phase1.sqlite3` | farmers 1; farms 1; crop_plans 0; farm_activities 1; farmer_sessions 3 | `0002_revocable_sessions` |
| `data/croppulse_local.sqlite3` | farm_records 1; market_quotes 0 | No Alembic revision |

The local legacy database has a different schema and is not the Phase 1 database. Do not point the Phase 1 Alembic migrations at it. Neither source database is replaced or reset.

## Target architecture

1. Keep Streamlit and its existing bearer-token contract working. Add a separately configured React + strict TypeScript + Vite client that uses FastAPI only; do not make either frontend maintain a second persistent copy of records.
2. Add an HttpOnly, bounded browser session for React, with an explicit CSRF defense for cookie-authenticated state changes. Keep bearer authentication for Streamlit. Use an explicit local development origin allowlist and production HTTPS configuration; do not put credentials in browser storage.
3. Add additive account role/status fields with existing accounts defaulting to active farmer, and an explicit reviewer-to-district assignment relation. Never grant existing accounts elevated access. Provision the first administrator only through a controlled server-side operator command, not public registration or request payloads.
4. Add administrator-only account and aggregated-metrics endpoints; add reviewer endpoints only for persistently stored farmer reports in assigned districts. Preserve original submitted activity facts and store review decisions separately with actor, timestamp, reason, and outcome. Session-only forms are not silently imported or presented as reviewable data.
5. Build role-aware React routes, an accessible responsive shell, farmer farm/record views using current APIs, and explicit not-yet-available states for data or operations that do not yet exist. Do not invent metrics, alerts, audit history, backups, or health statuses.
6. Add migration, API security/authorization, React component and build checks. Verify an additive migration against the verified backup, compare baseline rows/IDs and table counts, then apply it to the local Phase 1 database only after the copy migration succeeds.

## Known limits and gates

The source contains no historical trend records, backup-monitoring records, or production deployment configuration. A controlled pilot still requires privacy and retention policy, TLS/deployment review, recovery testing, low-end device/accessibility checks, agronomic review, and real user evaluation. PostgreSQL is not required for this migration and is not being substituted for SQLite.

## Implementation and verification status (2026-10-16)

- The React client, browser-cookie authentication, role-protected farmer/reviewer/admin workspaces, additive migration 0003, role and ownership enforcement, review history, admin audit events, rate limiting, and setup/recovery documentation have been implemented. The existing Streamlit app and bearer-token API remain in place.
- Migration 0003 was exercised against a backup copy through upgrade, downgrade to 0002, and re-upgrade. Baseline records were preserved. The actual local `data/croppulse_phase1.sqlite3` is now at revision 0003 and passes `PRAGMA integrity_check`; the unrelated `data/croppulse_local.sqlite3` remains untouched.
- Latest check (see [Phase 2 verification](phase-2-verification.md)): backend **68 passed, 1 harmless pytest runner warning**; frontend typecheck/lint/build passed and **10 frontend tests passed**. `httpx2` resolved Starlette's TestClient deprecation. The React app now returns to sign-in when an active API session expires.
- Runtime check against the local migrated SQLite database: FastAPI `/health` returned `{"status":"ok"}` and unauthenticated `GET /v1/me` returned HTTP 401. The temporary loopback API process was stopped after the check; no account or farmer record was created.
- Reviewer decisions remain separate from farmer-reported facts. The farmer record list shows review status and source separately; editing a reviewed submission makes it pending again while preserving prior review history.

These results cover automated checks and local SQLite only. There has been no PostgreSQL, deployment, visual browser, mobile-device, screen-reader, or real-user verification. The limits in [React app setup](react-app-setup.md) still apply; passing tests is not a production-readiness claim.

See [Phase 2 end-to-end verification](phase-2-verification.md) for the current runtime port mismatch, expanded authentication and authorization checks, warning review, and prioritized release checklist.
