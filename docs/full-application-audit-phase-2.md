# CropPulse Rwanda — Full Application Audit, Phase 2

**Audit date:** 2026-10-22  
**Scope:** source, documentation, data manifests, and the existing automated checks. No live deployment, live database, migration, or browser session was inspected during this audit.

## Executive status

CropPulse is a functioning development/pilot prototype with authenticated React/API workflows and a legacy Streamlit planning and analytics application. The codebase includes account-scoped persistence, explicit evidence boundaries, and a substantial automated test suite. It is **not ready for public production use**: external security, privacy, infrastructure, backup/restore, licensing, accessibility, and field validation remain unverified or incomplete. This is a source audit, not a penetration test or production certification.

## Feature inventory

| Area | Current status | Boundary / remaining work |
|---|---|---|
| React farmer workspace | Implemented for accounts, farms/fields, activities, saved plans, messages, crop-health reports, point weather, NISR statistics, settings | Uses FastAPI; live deployment and browser usability were not tested. English is primary; Streamlit has language options but detailed React Kinyarwanda coverage is incomplete. |
| Streamlit planning and analytics | Existing application still available through the account handoff | Several legacy tools/collections are session-only; they are not equivalent to durable React/API features. See `utils/frontend_services.py` and `docs/backend-phase-1.md`. |
| Authentication and roles | API-backed sessions, password hashing, CSRF/browser cookie flows, role and reviewer-scope checks exist | No MFA or registration email verification. SMTP is required for recovery/email change. Deployment-specific controls need review. |
| Farm and crop-plan records | Persisted under authenticated farmer account | Values are user-entered; coordinates do not prove field boundaries. |
| Recommendations and crop calendar | Provisional, deterministic CropPulse rules | Agronomic registry currently has zero approved rules; NISR is descriptive historical context and does not validate or rank recommendations. |
| Crop-health reporting | Private, persisted report/photo workflow with reviewer follow-up; maize model screening is experimental | Model labels are candidates, not diagnoses; scores are uncalibrated; Rwanda field validation and approved treatment guidance are absent. Streamlit pest observations remain session-only. |
| Weather and climate | Open-Meteo point forecast and saved forecasts; imported source PDFs and selected transcribed outlook ranges are available | Forecast is not observation or field-verified weather. METEO RWANDA reuse rights need written clarification. Alert preferences/history exist, but no approved alert rules or generator are enabled. |
| NISR statistics | Manifested district/crop/season dataset is structurally validated and displayed as historical context | Dataset licensing/attribution and source caveats must accompany reuse; it is not an agronomic recommendation source. |
| Private messaging | Persisted text conversations between eligible farmers and assigned active reviewers; administrator setting controls service | Reviewer status does not assert an agricultural qualification. No groups, file attachments, or advanced moderation in this phase. |
| External Hekitari service | Referral/link only | No shared login, account federation, API integration, or farm data transfer. |
| Agronomic evidence intake | Local operator-run, versioned intake and coverage tooling | Not a public upload service; actor/qualification fields are operator attestations, not authenticated identity or proof of professional credentials. Intake packages do not automatically become recommendations. |

## Prioritized findings register

Severity indicates release priority based on source review; it is not a claim that an exploit was demonstrated.

| ID / severity | Finding and evidence | Recommended next action |
|---|---|---|
| A1 — **High** | Production deployment checklist requires `CROP_PULSE_ENVIRONMENT=production`, secure cookies, exact CORS allowlist, managed secrets, HTTPS, and reverse proxy review. Source configuration should be validated against the actual hosting topology; the checklist itself says deployment controls are not tested. Evidence: `docs/react-deployment-checklist.md`, `docs/backend-phase-1.md`. | Add a release-time production configuration validator and verify it in the target deployment before inviting real users. |
| A2 — **High** | Crop-health photo size/dimension checks occur in the application workflow, but an upstream/request-body limit before multipart parsing is not documented or established in this source audit. Application-level 5 MiB photo checks alone do not bound all request parsing/spooling work. Evidence: `backend/api.py`, `docs/crop-health-review.md`, `docs/react-deployment-checklist.md`. | Set and test request-body and multipart limits at the proxy/server boundary; keep per-file validation as a second layer. |
| A3 — **High** | Existing database-backed throttling covers account-sensitive actions, but general endpoints and upload/forecast/message traffic rely on deployment-level controls; documentation explicitly says application login limiting is not a gateway replacement. Evidence: `docs/backend-phase-1.md`, `docs/react-deployment-checklist.md`. | Define per-route and edge limits, abuse monitoring, and cleanup policy for the production topology. |
| A4 — **High** | No agronomic rule is approved for automated recommendation/alert use (`data/agronomy/rules.json`, `utils/agronomy_knowledge.py`; weather rule registry is empty at `utils/weather_alert_rules.py`). Current recommendations remain provisional. | Obtain scoped, traceable review by qualified local specialists and preserve source, geography, crop/variety, season, conditions, and expiry before activating any rule. |
| A5 — **High** | The maize image model is a screening candidate, not a diagnosis; local Rwanda field validation, calibration/abstention, and treatment knowledge are missing. Dataset license/revision provenance also needs distribution review. Evidence: `docs/crop-disease-model.md`, `docs/crop-health-guidance-library.md`. | Conduct consented Rwanda field evaluation and specialist review; resolve upstream dataset/model rights before distribution or commercial use. |
| A6 — **High** | Weather alert preference/history endpoints are present, but `WEATHER_ALERT_RULES` is empty and no approved agriculture-alert generation process is enabled. Preferences alone do not produce alerts. Evidence: `utils/weather_alert_rules.py`, `docs/weather-alert-readiness.md`. | Keep alerts clearly unavailable until rules, validation, scheduling, expiry, and failure handling are reviewed. |
| A7 — **High** | No evidence in this audit of a monitored production backup service, successful restore drill, or deployment-level database resilience. PostgreSQL may be supported by configuration, but production migration/concurrency/restore behavior is not established by local tests. Evidence: `docs/react-deployment-checklist.md`, `docs/backend-phase-1.md`. | Choose/provision the production database, rehearse backup and restore, and run migration/concurrency checks against an isolated staging copy. |
| A8 — **High** | Crop-health photos and private farm/account data are persisted; production retention, data residency, incident response, and privacy/legal approvals remain deployment work. Evidence: `docs/react-deployment-checklist.md`, `docs/crop-health-review.md`. | Approve privacy notice, consent, retention/deletion, access logging, encryption, support, and incident processes before real-farmer onboarding. |
| A9 — **High** | Open-Meteo free API terms restrict use to non-commercial use and specify attribution; commercial/promotion requires an appropriate paid plan/license. Evidence: `docs/weather.md`. | Confirm the intended deployment’s commercial status and terms; implement compliant attribution and plan before public/commercial release. |
| A10 — **High** | Existing weather-data review has not identified explicit open reuse permission for all METEO RWANDA bulletin PDFs/transcribed ranges. Government origin and attribution alone do not establish redistribution permission. Evidence: `docs/weather-data-review.md`. | Request written reuse/redistribution terms and preserve source-specific scope; do not imply an open license. |
| A11 — **Medium** | Some one-time account flows use URL query parameters before consumption; access-log and analytics redaction should be confirmed for the selected hosting stack. Evidence: `docs/backend-phase-1.md`, React/Streamlit handoff implementation. | Ensure proxy, application, analytics, and error logs redact tokens/query strings; verify one-use/expiry behavior in deployment. |
| A12 — **Medium** | Streamlit still exposes session-only collections and tools, while React/API is the main durable farmer workspace. User expectations can exceed persistence/integration. Evidence: `utils/frontend_services.py`, `README.md`, `docs/backend-phase-1.md`. | Label temporary entries clearly and migrate only after each React/API replacement preserves access, persistence, and privacy boundaries. |
| A13 — **Medium** | User-facing localized coverage is uneven; README identifies English as primary for detailed analytics/agronomy text. Evidence: `README.md`, frontend source and Streamlit language controls. | Complete translation inventory and have Kinyarwanda agricultural terminology reviewed by fluent local users. |
| A14 — **Medium** | External usability/accessibility, low-bandwidth/mobile behavior, dependency security, penetration testing, monitoring, and disaster recovery have not been demonstrated by automated checks. Evidence: `docs/react-deployment-checklist.md`. | Complete the checklist on a controlled staging deployment; record actual browser/device and security test results. |

## Data, scientific, and trust boundaries

- NISR SAS is a statistical source for historical area/production context. Structural/checksum validation confirms file integrity and expected structure; it does not independently certify survey estimates or authorize every form of reuse.
- Weather products must remain distinguished by type: Open-Meteo model forecast, METEO RWANDA outlook/bulletin, climatology, and observed station measurement are not interchangeable.
- CropPulse-generated suitability/calendar guidance is provisional. No approved rule currently makes the recommender institutionally or professionally verified.
- Experimental image labels must not be presented as confirmed disease, root cause, medicine, pesticide rate, or treatment advice.
- Intake lifecycle approvals are local operator attestations. They do not prove publisher authenticity, permission, identity, or professional qualifications. Registry coverage must be interpreted only for valid, active, unexpired, scoped, traceable records.
- Never fabricate reviewer assignments, dataset provenance, location boundaries, local model accuracy, or agronomic validation to make a feature appear complete.

## Verification actually performed

Latest executed checks in this workspace (no application code changed during this audit):

- Python full suite: `\.venv\Scripts\python.exe tests\windows_safe_pytest.py` — **153 passed, 1 warning** (AnyIO `PytestAssertRewriteWarning`).
- Focused agronomy suite: `\.venv\Scripts\python.exe tests\windows_safe_pytest.py tests\test_agronomy_intake.py tests\test_agronomy_knowledge.py tests\test_recommender.py` — **38 passed, 1 warning**.
- Frontend tests: `npm test -- --configLoader native --pool=threads --maxWorkers=1` — **35 passed**.
- Frontend typecheck: `npm run typecheck` — **passed**.
- Frontend lint: `npm run lint` — **passed**.
- Frontend production build: `npm run build -- --configLoader native` — **passed**.
- Knowledge validator: `\.venv\Scripts\python.exe -m utils.agronomy_knowledge` — passed structural/integrity validation; active approved agronomic rules: **0**; open quality issues: **6**; NISR rows: **2020**.
- NISR and agronomy manifest/checksum validation was reported valid in the latest workspace verification.

Not performed: browser/manual workflow, accessibility/screen-reader, live API/database, production configuration, migration, penetration, dependency vulnerability, performance/load, backup/restore, or deployment verification. The checks above do not establish production readiness.

## Next work

### Software work

1. Establish a controlled staging deployment with strict environment validation, request-size controls, edge throttling, structured redacted logs, monitoring, and HTTPS/CORS/cookie checks.
2. Confirm backup/restore and database migration behavior using isolated staging data; retain a reviewed rollback plan.
3. Test complete farmer/reviewer/admin workflows in real browsers and on low-bandwidth mobile devices; include accessibility and Kinyarwanda review.
4. Keep the disease model, weather alerts, and crop recommendations explicitly provisional until evidence and review prerequisites are satisfied.

### External decisions and evidence

1. Obtain METEO RWANDA permission/terms for bulletin reuse and determine Open-Meteo plan suitability for the deployment.
2. Resolve PlantVillage dataset and derived-model license/provenance for the intended distribution.
3. Obtain qualified Rwanda agronomic review and field evaluation; review crop-health treatment content separately before any treatment recommendations.
4. Approve privacy, consent, retention, legal, operational support, hosting, data residency, and incident response requirements.

## Changes made by this audit

This audit adds only this report and a README link. No application behavior, database, migration state, NISR dataset/manifest, weather source files, agronomic intake package, or active rule registry was changed. No live database was opened, no server was started/restarted, and no migration was applied.

## Phase 3A remediation record — 2026-10-22

This dated follow-up implements narrowly scoped fixes for findings A1–A3 and records a local recovery drill. It does not apply a migration or claim production readiness.

| Baseline finding | Status | Evidence / remaining work |
|---|---|---|
| A1 — production security configuration | **Partially remediated in source** | Startup now requires an explicit supported runtime environment. Staging/production require explicit HTTPS CORS origins, reject wildcard/path/userinfo entries, reject insecure-cookie overrides and auto-create-schema, and always set secure cookies. Regression tests cover these checks. The real hosted configuration remains unverified. |
| A2 — request size before parsing | **Partially remediated in source** | ASGI middleware now caps all body-bearing requests at 8 MiB before JSON/multipart parsing, including chunked bodies. Per-photo 5 MiB validation remains. Reverse-proxy limits and concurrent-request controls still need deployment configuration/testing. |
| A3 — general abuse controls | **Partially addressed** | Account-specific persisted throttles remain. This phase documents the required gateway throttles; it does not add an unreliable per-worker limiter. No hosted gateway was configured or tested. |
| A7 — backup/restore evidence | **Local restore test completed** | A pre-existing SQLite backup was opened read-only and restored with SQLite backup API to an in-memory database; integrity was `ok`, revision was `0014_weather_bulletin_records`, and required core tables were present. This does not confirm the active server target, freshness, ACLs, encryption, or production recovery. |
| A8 — privacy and retention | **Inventory documented; policy unresolved** | Data categories, access/deletion behavior, operational log caveats, and policy gaps are documented in `docs/security-privacy-recovery-phase-3a.md`. Legal/organizational approval and defined retention schedules remain required. |

**Files changed for Phase 3A:** `backend/api.py` (startup security validation and request-size middleware), `tests/test_backend_api.py` and `tests/test_react_security_api.py` (regressions), `.env.example` (configuration guidance), `.gitignore` (exclude local API logs), `docs/react-deployment-checklist.md`, `docs/security-privacy-recovery-phase-3a.md`, this audit record, and `README.md` links. No database, migration, NISR data/manifest, weather source files, or agronomic registry were edited. See the new security/privacy/recovery document for the exact restore source and scope.

## Phase 3A.1 follow-up — 2026-10-22

**Diagnosis:** The three prior intake test failures all occurred at the completed package's final directory rename and returned Windows `PermissionError: [WinError 5]`. Python artifact, JSON, and DOCX archive handles were closed before that operation. ACL inspection found the staging and records directories had matching observed permissions, and isolated same-volume rename diagnostics succeeded. This establishes the failing boundary but does not establish the underlying Windows access-denied trigger; no antivirus or external-process cause is assumed.

**Fix:** `utils/agronomy_intake.py` now creates the destination directory with a `.publication_pending` sentinel, copies the fully validated staged package, verifies the copied metadata/event/validation integrity and archived artifact checksum, then removes the sentinel to publish. `list_records` ignores pending destinations as well as hidden staging siblings. I/O failures retain the staged package and pending destination for manual recovery; incomplete packages are not listed or included in coverage. Immutable version locks and no-overwrite behavior remain. Regression tests cover complete publication and simulated permission failure. This changes only intake code and TEST_ONLY test fixtures.

**Verification:** Previously failing cases plus new publication regressions: **5 passed**. Focused intake and knowledge tests: **29 passed**. Full Windows-safe Python suite: **158 passed, 1 warning** (`PytestAssertRewriteWarning` for AnyIO). Frontend tests: **35 passed across 4 files** with `npm test -- --configLoader native --pool=threads --maxWorkers=1`; default `npm test` could not start Vitest workers because Windows returned `spawn EPERM`. `npm run typecheck` and `npm run lint` passed. Production build `npm run build -- --configLoader native` passed. No browser/live service verification or deployment was performed.

**Files changed in Phase 3A.1:** `utils/agronomy_intake.py`, `tests/test_agronomy_intake.py`, `docs/security-privacy-recovery-phase-3a.md`, and this report. No NISR CSV/manifest, active agronomic registry, SQLite database, or migration was changed.
