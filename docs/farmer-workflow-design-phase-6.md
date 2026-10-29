# CropPulse Rwanda — Farmer Workflow Design and Evidence Acquisition Readiness, Phase 6

**Review date:** 2026-10-28  
**Repository:** C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda  
**Status:** **DEVELOPMENT ONLY**  
**Scope:** Read-only inspection of React, FastAPI, Streamlit, persistence, agricultural evidence, prior audit and test sources. This phase documents design and evidence requirements; it does not add major integrations, activate agricultural rules, alter databases or authorize a pilot or release.

## 1. Executive summary

CropPulse has a foundation for account-backed farms, fields, crop plans, activities, weather forecasts, crop-health cases, private messaging and role-scoped review. React is the main account-backed farmer experience; FastAPI enforces identity and ownership; Streamlit still exposes earlier planning and analytics tools. They share the service for selected records, but they are not one unified implementation: Streamlit has a separate provisional crop-planning path and several temporary session collections.

The proposed farmer journey below is a design target, not a claim that every step is integrated. Farm setup, plans, activities, weather, health cases and messages are separate screens and data relationships. There is no dedicated harvest entity: a farmer can enter an activity named “Harvest” with a quantity, but that is not a complete, unit-safe harvest or yield workflow. Weather is not attached to plan outcomes or used to change crop recommendations. Plan status is farmer-managed, not proof that a crop stage was observed.

The evidence boundary remains strict. The current read-only agronomy validator reports a valid/current pack with five sources, four statements, six open quality issues, zero rules, zero approved rules and zero review decisions. There are 12 legacy provisional guide entries; these are not evidence coverage. NISR is descriptive historical context only. Its CSV hash matches the manifest. No reviewer qualification, source permission, field validation or institutional endorsement was established.

No application defect was confirmed or fixed in Phase 6. No application source, database, migration, verified dataset, evidence rule, prior report or existing frontend build was changed. This report and a README link are the only intended changes. A local API listener on 127.0.0.1:8001 and Vite listener on 127.0.0.1:5173 were observed on 2026-10-28; neither was contacted, and neither was tied to a source tree, environment or database by this workflow review.

## 2. Baseline and inspection evidence

### Repository and prior evidence

- Confirmed project root: C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda.
- No .git directory exists in this project copy. Git status/history and a clean baseline could not be established; this report does not attribute all existing edits to this phase.
- Read the Phase 3 full system audit, Phase 4 readiness and full-system verification reports, Phase 5 controlled browser QA and Phase 5 agricultural evidence governance report, plus README and workflow/contract documentation. Prior results are historical evidence, not newly executed checks.
- Inspected current React routes, session client and page components; FastAPI route declarations and ownership helpers; SQLAlchemy models/schemas; Streamlit app/service adapters; database URL configuration; migration declarations; agronomy registry; NISR manifest; and supporting tests and data-limit documentation.
- No authenticated browser workflow, live-provider request, API request, database query, migration, server launch or application test was performed in Phase 6.

### Current read-only observations

| Check | Result | Boundary |
|---|---|---|
| netstat -ano -p tcp \| Select-String -Pattern ':(8000\|8001\|8501\|5173\|18001)\s' | 127.0.0.1:8001 LISTENING, PID 27120; 127.0.0.1:5173 LISTENING, PID 8980. No matching lines for 8000, 8501 or 18001. | Listener/PID evidence only. Neither process was contacted or conclusively tied to this source tree, runtime configuration or database. |
| backend/db.py and backend/migrations/env.py inspection | CROP_PULSE_DATABASE_URL overrides sqlite:///./data/croppulse_phase1.sqlite3; relative SQLite paths resolve from process working directory. Alembic uses the same variable/default. | No database was opened; live process database is unknown. |
| Migration declarations | Linear source chain from 0001_phase1_records through 0015_weather_alert_foundation. | Source head does not establish live database revision. No migration ran. |
| .\\.venv\\Scripts\\python.exe -m utils.agronomy_knowledge | Exit 0; valid/current; 5 sources, 4 statements, 6 open issues, 0 rules, 0 approved rules, 0 decisions, 12 provisional guide entries, 2,020 NISR rows. | Read-only validator mode; no write flags. Coverage has no crops, seasons or districts with approved rules. |
| Get-FileHash data\\verified\\nisr_sas_2023_2026.csv -Algorithm SHA256; compare with sha256 in data/verified/MANIFEST.json | Match: 98de5073d00f60231df496da3c19912834a3156a7f2f044bd6eaa5108f313927. | Integrity match only; does not independently validate survey estimates, source authenticity or reuse rights. |
| Existing tests | Test names and Phase 4/5 result tables inspected; no tests run in Phase 6. | Prior automated results are not browser, provider, hosted or field validation. |

### Verified application shape

- React navigation is role-filtered for presentation. FastAPI also applies authentication, role, ownership and reviewer-district checks on protected routes; the UI is not the security boundary.
- React uses credentialed browser requests with an HttpOnly session and CSRF flow. Streamlit uses its API adapter and a token established through a single-use handoff. Both depend on compatible hostname/cookie configuration. Prior reports describe a 30-minute fixed browser session and local handoff tests; no running browser was exercised here.
- FastAPI declares account, farm, field, activity, crop-plan, weather, crop-health, messaging, reviewer and admin routes. Prior API tests use isolated fixtures. No current live OpenAPI request was made.
- Account-backed data uses SQLAlchemy. The database default is relative to process working directory and can be overridden. The live database identity remains unresolved.
- NISR is aggregate district/crop/season area and production context, not farm yield, crop-fit evidence or prediction.

## 3. Verified architecture and data flow

### Current architecture

    Farmer browser → React workspace → FastAPI → configured SQLAlchemy database
                                   ↘ provisional recommender → provisional guide
                                                           ↘ NISR (historical context only)
                                   ↘ Open-Meteo forecast adapter
                                   ↘ crop-health cases and experimental maize screening
                                   ↘ private farmer-reviewer messaging
                                   ↘ METEO RWANDA bulletin records
    Streamlit workspace → single-use handoff/API client → FastAPI
                       ↘ temporary session collections (not account persistence)
    Local agronomy intake → registry → recommendation path fails closed while
                             trusted approval identity is not configured

The database target of the observed API listener is unknown. Intake packages are separate from the farmer recommendation path. Hashes and local review records do not prove identity or approval.

### Proposed farmer journey

    Register/sign in and accept notice
      → create farm and optional fields
      → compare crop options and evidence limits
      → save provisional crop plan
      → record actual planting and dated activities
      → review weather separately; persist coordinates only with consent
      → report observed crop-health concern and optional photo
      → track authorized follow-up and reply if requested
      → record harvest through a future structured workflow
      → review season history with source and missing-data labels

This target does not imply automatic stage dates, verified field conditions, active alerts or new API links.

## 4. Farmer journey and persistence matrix

| Step and current screen | Route/data path | Persistence and authorization | Validation, states and gaps |
|---|---|---|---|
| Account | React LoginPage/AuthProvider; browser-auth register/login/logout, CSRF, /v1/me, email change/recovery; single-use Streamlit handoff. | Account, sessions and action tokens are database-backed. React uses HttpOnly cookie; Streamlit holds API token in session. | Registration requires privacy-notice acceptance; role self-assignment is denied. Email flows depend on configured mail. No MFA/email verification. Hosted SMTP and browser workflow unverified. |
| Profile | Account display name/email/role and account settings. | Persistent in configured database. | No complete saved language, unit, notification, accessibility or profile-completeness workflow. |
| Farm/field | React FarmsPage; /v1/farms and nested field CRUD/archive routes. | Farm belongs to owner; fields belong to farm; API checks ownership. Field area/paired coordinates optional and farmer-supplied. | Loading/error/empty states and confirmation for destructive actions exist. Coordinates are not surveyed or district-polygon validated; no soil profile. |
| Crop comparison | Farm workspace; POST /v1/crop-planning/recommendations; utils/recommender.py and provisional guide. | A request is not itself a durable recommendation record. | Ranking uses provisional CropPulse guide; missing conditions stay unknown. NISR does not rank crops. No variety, plot soil, measured water, validated calendar or prices. UI exposes limitations. |
| Plan | FarmsPage; GET/POST/PUT plans and status PATCH under /v1/farms/{farm_id}. | Persistent crop_plans associated with farm and optional field. | Draft/planned edit limits and lifecycle transitions enforced server-side. Saving also creates generic “Seasonal plan” activity in same transaction. Plan evidence schema exists, but no independent approved evidence is automatically attached. Status is farmer-reported, not measured stage. |
| Planting/activity | Farm activity history; GET/POST/PUT/DELETE /v1/farms/{farm_id}/activities. | Persistent, owner-scoped through farm; creation supports idempotency key. | Generic type/date/quantity/unit/notes; no strict shared activity vocabulary, full unit compatibility, or correction history. |
| Weather | React WeatherPage; POST /v1/weather/forecast; GET /v1/weather/forecasts; shared adapter. | Explicit save consent required; latest forecast per account/coordinate stored and owner-scoped. Coordinates remain unverified. | Forecast is a model estimate, not plot observation. Stale/unavailable and attribution limits are displayed. Prompts are cautious and signal-based. No direct pesticide/disease/soil/planting determination. No live provider check this phase. |
| Alert preference/history | /v1/weather/alert-preferences, per-field update, /v1/weather/alerts and status update. | Preference/history storage is owner/field scoped. | Defaults off; zero approved rules and no generator. Opt-in does not mean alerts will arrive. |
| Crop-health case | React CropHealthPage; /v1/crop-health/crops, cases list/create/detail/photo/reply. | Photo and case persist; private to owner and eligible assigned-district reviewers. | Photo validation and upload status exist. Maize screening is experimental and uncalibrated; other crops lack model screening. No diagnosis or treatment. Reviewer role does not prove qualifications. |
| Messaging | React MessagingPage; reviewer discovery, conversation, messages and read routes; admin setting. | Persistent private text, participant authorization and current district eligibility checked in API. | Disabled by default. No attachments, groups, offline queue or delivery guarantee. Role is not qualification. |
| Harvest/outcome | Generic FarmActivity may contain “Harvest”; plan lifecycle includes harvesting/completed. | Generic farmer-reported activity persists. | No dedicated multi-harvest model, unit-safe yield, quality/loss/cost ledger or outcome analysis. Completed plan is not verified harvest. |
| Statistics | React AgriculturalDataPage; authenticated /v1/agricultural-statistics/nisr; shipped CSV/manifest. | Aggregate file, not farmer-specific data. | Manifest covers 2023–25 A/B/C and 2026 A/B; 2,020 rows in validator. Current phase verified checksum only. Historical district values cannot establish individual-farm outcome or suitability. |
| Streamlit tools | app.py, plan.py, product_pages.py, views.py, utils/frontend_services.py. | Farms, activities and plans use API when enabled/signed in. Market quotes, review submissions, feedback, pest reports, extension/cooperative notes, weather observations and some planner state use st.session_state and clear at sign-out. | Separate provisional seasonal-plan builder does not use React recommendation endpoint or approved-rule matcher. Temporary entries are not durable reports. |
| Reviewer/admin | React review, crop-health review, accounts, reports, system routes; backend reviewer/admin routes. | Role and district assignments and audit events persist. API enforces roles/scopes. | Browser proof absent. Admin aggregates farmer-reported records; privacy and small-cell disclosure need review before broad sharing. |

### Existing test coverage and limits by journey

| Journey | Existing test evidence identified | Limit |
|---|---|---|
| Registration, session, settings | tests/test_react_security_api.py; frontend App.test.tsx | In-process API and jsdom tests; SMTP delivery and hosted browser behavior are not established. |
| Farms, fields, plans, activities | tests/test_backend_api.py; frontend App.test.tsx and pages.test.tsx | Isolated API/component tests; no authenticated browser workflow against a live isolated service in this phase. |
| Recommendation and NISR | tests/test_recommender.py, test_backend_api.py, AgriculturalDataPage.test.tsx | Confirms software contract/provisional status and mock UI; not agricultural validity or NISR estimate verification. |
| Weather and alerts | tests/test_weather.py, test_weather_alert_rules.py; WeatherPage.test.tsx | Mocked/adapted provider behavior; no live provider, real browser location permission or active alert-generation evidence. |
| Crop health | tests/test_crop_health_api.py; CropHealthPage.test.tsx | API/UI tests cover privacy, upload and review cases; not field-image accuracy, diagnosis safety or hosted upload behavior. |
| Messaging and role boundaries | tests/test_backend_api.py, test_react_security_api.py; App.test.tsx | Isolated role/ownership tests; not a live multi-account browser session or reviewer qualification check. |
| Streamlit records and session state | tests/test_app.py, tests/test_seasonal_plan.py and service-layer tests | AppTest/unit evidence only; does not prove persistent storage for session collections or cross-client browser parity. |
| Reviewer/admin workflows | backend API/security tests and React App/pages tests | In-process/API and jsdom evidence only; no authenticated reviewer/admin browser run here. |

Prior Phase 4/5 reports record their executed suite counts and warnings. This phase did not rerun tests; no prior suite is presented as newly verified.

### Error, retry and partial-failure behavior

React has centralized API error mapping, visible retry/error states on key pages and form busy states. Activity creation can deduplicate with a supplied idempotency key, but there is no general offline queue or cross-screen reconciliation. Plan creation stores plan and generated activity in one transaction. Weather unavailable/stale responses do not count as successful saved forecasts. Crop-health upload is one API operation; interruption/retry duplicate behavior needs browser verification. Streamlit session submissions disappear on sign-out and must not be described as account persistence.

## 5. Proposed unified farmer workspace

React should become the single farmer entry point, summarizing only persisted APIs:

1. Farms and active fields, with “No farm yet”; distinguish missing area/coordinates from zero.
2. Active saved plans, status and proposed/actual planting dates only when entered. Label status farmer-reported; never invent stage dates.
3. Recent saved activities with date, unit and verification label. Do not infer activity from a plan.
4. Saved forecast source, provider time, stale state and consent-aware action. No unsupported risk badge.
5. Owned case status and whether actual reviewer follow-up or farmer reply is pending; no promised response deadline.
6. Real unread message count only if service succeeds and messaging is enabled; otherwise show disabled/unavailable state.
7. Harvest as “Not recorded” unless a farmer-reported harvest activity exists; do not infer yield from plan completion.
8. Evidence status from API: provisional, approved within explicit scope, or unavailable. Current registry has no approved scoped rule.

| Item | Source | Loading / empty / failure | Offline and privacy |
|---|---|---|---|
| Farms/fields | /v1/farms and nested fields | Loading; add-farm empty; retryable error distinct from empty. | Do not present old values as current. Names, district, area and coordinates are private. |
| Plans | per-farm /plans | Loading; create-plan empty; explicit retry. | No offline edits until conflict/idempotency policy exists; plan notes private. |
| Activities | per-farm /activities | Loading; no-activity prompt; retryable failure. | Never display unsaved as saved. Activities reveal production patterns. |
| Weather | saved forecast and request result | No saved forecast; stale/provider unavailable; retry. | Cached forecast needs age label. Coordinates are sensitive; consent and restricted access. |
| Crop-health | owned case list/detail | No reports; loading; error; upload failure must not say submitted. | Photos/symptoms highly sensitive; narrow access, retention and deletion policy. |
| Messages | conversation/read APIs | Disabled, empty, loading and error states; no fabricated count. | No offline queue until expiry, dedupe and conflict are designed. Content is private. |
| Harvest | Future structured entity; today generic activity only | “No harvest record”; never zero yield by default. | No yield if units, area, time and scope do not match. |
| Evidence | recommendation response and registry | Provisional/no-evidence; failed lookup never marks approved. | Future offline evidence needs version, scope, date and expiry. |

Mobile-first language, touch targets, low-bandwidth handling and Kinyarwanda are design requirements, not usability claims established by code inspection. Offline use is not implemented. Any future cache requires device-sharing threat analysis, encryption, expiry, logout clearing and conflict handling.

## 6. Agricultural evidence and trust matrix

| Category/source | Supports, coverage and quality | Rights and farmer-facing boundary | Required verification |
|---|---|---|---|
| NISR: data/verified/nisr_sas_2023_2026.csv and MANIFEST.json | Aggregate area/production by district/crop/season; 2023–25 A/B/C, 2026 A/B; checksum/structure consistency only. | Prior Phase 4 report records general NISR CC BY 4.0 terms; confirm specific publication conditions. Historical context only, never crop fit or farm yield prediction. | Recheck source tables/transformation, attribution and intended redistribution rights. |
| Crop suitability: knowledge.py, utils/recommender.py, data/agronomy | Five sources, four statements, six open issues; zero rules/approvals; zero scoped coverage. | Crop ranking is provisional. Do not label validated suitability without sourced scope and trusted approval. Hash is not truth. | Local source with exact locator, crop/variety/geography/season/conditions, units, dates, uncertainty, reuse permission; qualified review. |
| Crop calendar: provisional guide and utils/seasonal_plan.py | Existing season/month entries; no approved calendar rule. District/variety scope unverified. | Provisional prompt, not official “best date.” | Source/version/date and geographic/crop scope, conflict handling, local review. |
| Soil/elevation/water: farmer inputs and provisional guide | Optional coordinates/area; no verified soil feed. Coarse Rwanda rectangle is not district/farm boundary. | No inferred conditions; missing remains unknown. | Authoritative source, rights, resolution, method/date/units/accuracy and agronomic interpretation. |
| Point forecast: utils/weather.py and /v1/weather/forecast | Open-Meteo forecast adapter; source/time/stale labels in docs/source. No live call this phase. | Prior reports state Free API non-commercial restriction and CC BY 4.0 attribution; recheck current terms and use classification. Forecast is not plot observation. | Current terms/plan, attribution, caps, outage and freshness behavior in target deployment. |
| Official bulletin: data/raw/weather_climate, utils/weather_bulletins.py, bulletin routes | Source-linked PDFs and partial transcription; issue/validity/completeness gaps. | Prior reports found no written redistribution permission. Not a complete warning feed or field observation. | Written rights; issue/valid time, units, transcription QA and revision/expiry process. |
| Agricultural alerts: utils/weather_alert_rules.py and preference/history routes | No approved active rules or generator; preference/history storage only. | Do not create or imply real alerts. Empty history is not a “safe weather” signal. | Scoped source threshold, false-alarm assessment, expiry/dedupe, response and qualified review. |
| Image screening: backend/crop_disease_model.py and case UI | Experimental maize-only ranked labels, uncalibrated, not established on Rwanda field images. | Prior reports note PlantVillage mirror tags CC BY-SA 3.0; pinned revision and model-weight obligations unresolved. Not diagnosis; no chemical advice. | Pin license/provenance, consented Rwanda data, expert labels, farm/time-separated evaluation, calibration, abstention and error review. |
| Disease/treatment | No verified diagnosis or treatment guidance in active path. | Rwanda validation, pesticide label, dose, interval and treatment source not verified. Do not diagnose/prescribe. | Current Rwanda registered labels/sources, legal/safety review and qualified plant-health oversight. |
| Market prices | No live feed; Streamlit cp_market_quotes is manual session state. | No coverage, grade/unit, freshness or license. Not current/official/profit data. | Authorized feed or attributed observations, normalized place/grade/unit/time, validation and moderation. |
| Harvest/yield | Generic FarmActivity; NISR aggregates are separate. | Farmer-entered only; no multi-harvest/unit/area model. No yield claim unless numerator, denominator, scope and period match. | Co-design structured records, correction history, consent and completeness checks. |

## 7. Evidence acquisition plan for Rwanda

No institution, permission, partnership, reviewer, farmer interview or field result is represented as secured. Roles below are responsibility types, not named people.

| Priority | Evidence/question and acceptance | Responsible role/dependency | Blocker if unavailable |
|---|---|---|---|
| 1. Local sources and rights | Determine exact claims by crop/variety/district/season/condition. Candidate sources for inquiry include RAB and RwaSIS; mention is not endorsement. Require reviewed terms, stable version/hash, page/table locator, date, units, scope, uncertainty and second-reader transcription check. | Evidence/data-rights owner and source institution. | Keep advice provisional/unavailable. |
| 2. Calendar and agronomic constraints | Compare valid sources, record conflicts/uncertainty, define scope and expiry, receive qualified Rwanda specialist approval; do not extrapolate one calendar nationally. | Evidence steward and qualified local reviewer; depends on source rights. | No definitive date or suitability claim. |
| 3. Reviewer identity/qualification | Verify identity through organization-approved identity service and qualification through trusted issuer; retain verifier, scope and expiry; require distinct reviewers for high-impact rules. | Organization/security owner and credential authority. | Approval hard gate remains closed. |
| 4. Weather bulletins/thresholds | Obtain written use terms; verify issue/validity, units and transcription; independently review crop/stage/district threshold, uncertainty, false alarms, expiry, dedupe and response. | Source/data owner and qualified meteorology/agronomy reviewers. | No bulletin redistribution or generated agricultural alert. |
| 5. Crop-health validity | Consent/minimize; pin model/dataset provenance; expert-adjudicated labels; farmer/farm/time-separated evaluation, class-level calibration, abstention and out-of-distribution checks. Define criteria before results. | Model owner, plant-health, privacy/legal reviewers. | Keep experimental/non-diagnostic or disable if rights/safety demand. |
| 6. Farmer usability | Voluntary informed consent; varied district/device/language/connectivity; measure comprehension/task completion/error recovery; minimal demographics. | Product research, language and privacy leads. | No validated usability or benefit claim. |
| 7. Harvest records | Co-design repeated harvest, explicit units/area/season/date, losses, corrections, source and reported/verified state; check missingness and bias. | Farmer research and data/evaluation stewards. | No yield/performance claim. |
| 8. Validation pilot | Require privacy/legal/security, runtime identity, protected recovery, support, approved evidence, reviewer staffing, independent evaluation, stop rules and owner authorization. | Data, product, operations and privacy owners. | Do not pilot. |

## 8. Secure future reviewer and approval design

This design is not implemented. Phase 5 correctly fails closed because no independently trusted identity/qualification anchor exists.

1. Quarantine submissions; preserve source version, permission reference, checksum, exact extracted claim, units, date, scope, limits and translation provenance. Nothing becomes active automatically.
2. Use organization-managed authenticated identities and appropriate MFA. Verify qualification/authorization with trusted issuer/process; record minimum proof metadata and expiry. Local JSON booleans, actor labels, email ownership and roles are not proof.
3. Separate submitter, technical reviewer, local specialist reviewer and activation operator. Submitter cannot be sole approver. High-impact rule needs distinct identities and relevant local competence.
4. Record append-only/tamper-evident decisions bound to exact evidence/rule hashes, reviewer identity reference, verified scope, reason, time, policy version and expiry. Hash is not identity or immutability; protect keys/access/backups.
5. Lifecycle: draft → provenance check → technical review → local specialist review → approved for exact scope → independent activation check → active; rejection/return, expiry, withdrawal, supersession and quarantine remain explicit. No silent version replacement.
6. Serving requires valid rights, current artifacts, verified unexpired reviewer authorization, distinct approvals, complete crop/variety/geography/season/condition scope and no conflict/revocation. Otherwise return no rule and preserve exact version snapshots.
7. Audit access/role changes; provide credential renewal/revocation, appeal, backup and trust-anchor recovery. External intake needs file validation, rate control, privacy/retention, quarantine and accountable operations before public use.

**Required tests:** deny unauthenticated, suspended, expired/revoked, wrong-scope/role reviewers; enforce submitter separation; reject missing permission, stale hashes, invalid units/scope, conflicts, expired/withdrawn sources and tampered/out-of-order events; bind decisions to exact versions; test all scope dimensions, expiry propagation, cache invalidation, restore/revocation and farmer-safe disclosure without credential documents.

## 9. Privacy, licensing and operational blocker register

| Blocker | Severity | Evidence and missing proof | Mitigation / scope blocked |
|---|---|---|---|
| Zero approved scoped rules | Critical | Current validator: zero rules/approvals; no trusted qualification verification. | Acquire permitted evidence and independent review. Blocks rule activation and pilot relying on advice. |
| Consent, lawful basis, retention and user rights | High | Notice acceptance exists; identity, coordinates, messages, photos and cases persist. Complete policy/process absent. | Controller/legal owner must approve purpose, minimization, retention, deletion/export/access, residency, support and incident handling. Blocks real-data pilot/public release. |
| Sensitive photos/coordinates/messages | High | Owner/district checks, cookie/CSRF and file limits in code/tests. | Verify hosted encryption, access logging, retention, operator access, abuse handling and browser boundaries. |
| Data rights/attribution | High | NISR, METEO RWANDA, Open-Meteo and PlantVillage provenance in docs/source; product-specific rights remain unresolved. | Reconfirm current terms, commercial status, attribution, redistribution and model obligations. Blocks affected public/commercial features. |
| Live runtime/database identity | High | Source honors CROP_PULSE_DATABASE_URL and relative default; live listener identity unresolved. | Service owner must link process/source/config to canonical sanitized database identity. Blocks safe backup/migration/release proof. |
| Protected backup/restore | High | Prior synthetic restore mechanics passed; ACL restriction was not verified; no live DB identified. | Restricted/encrypted destination, schedule, retention, RPO/RTO and isolated restore. Blocks real data and production migration. |
| Hosted security/abuse controls | High | Source has cookie/CSRF/CORS checks, sensitive-action throttle and body/file bounds. | Verify TLS/proxy, secrets, CORS, general rate/concurrency controls, logging and monitoring at host. Blocks public exposure. |
| Browser workflow/ownership proof | High | Isolated API/component tests exist; authenticated E2E absent in prior report. | Browser test all roles, cross-account/district denials, refresh, expiry, CSRF, upload, failure and duplicate behavior. |
| Weather rights and alert readiness | High | Forecast and preference/history routes exist; no active rules/generator. | Confirm terms and approve local rules, expiry/dedupe, false-alarm controls and response. Blocks alerts/public provider use until rights known. |
| Crop-health model safety/rights | High | Experimental maize-only; no Rwanda field evaluation/treatment. Dataset revision/weight obligations unresolved. | Pin provenance/license and evaluate consented local data with calibration/abstention. Blocks diagnosis claims/expansion. |
| Reviewer qualification/capacity | High | Role and district assignment exist; credentials and service availability unverified. | Trusted verification, staffing, response and escalation policy. Blocks trusted specialist advice/promises. |
| React/Streamlit duplicate paths | Medium | Separate provisional planners; many Streamlit collections session-only. | Define source per workflow; migrate/retire deliberately and show temporary vs saved. |
| Harvest/yield incomplete | Medium | Generic activities and lifecycle only. | Co-design units, area, repeated harvest, correction/provenance. Blocks yield/economic claims. |
| Language/accessibility/offline | Medium | React mostly English; some Streamlit translation; no offline sync. | Kinyarwanda/accessibility/device/connectivity research. Blocks associated inclusion claims. |
| Market data absent | Lower core / High for economic claims | Manual temporary quotes only; no live source. | Authorized source, rights, coverage/unit/freshness. Blocks current-price/profit claims. |
| No Git provenance | Medium | .git absent and Git unavailable in previous audit. | Version-controlled release checkout/change review. Blocks reliable change attribution. |

## 10. Prioritized roadmap

1. Obtain source-specific reuse permissions and local crop/variety/geography evidence; keep approval closed.
2. Decide organization identity, credential verification, approval roles, two-person review, audit, expiry, revocation and recovery.
3. Make React the single farmer entry point; use existing APIs for persisted farms/plans/activities/cases/messages; clearly label Streamlit temporary tools and migrate/retire deliberately.
4. Design plan links to dated farmer-reported stages, weather context, cases and future harvest without inferring observations/advice.
5. Co-design structured harvest records before schema proposals; define units, repeated harvests, area, losses, corrections and provenance.
6. Verify staging process/database identity, isolated persistence, protected backup/restore, TLS, CORS/CSRF, abuse controls, monitoring, mail and rollback.
7. Conduct voluntary farmer usability, language, accessibility and low-bandwidth research; make no representativeness claim without evidence.
8. Evaluate model and alerts separately with experts, rights, uncertainty, false-alarm handling and support capacity.
9. Require independent privacy/security/agricultural review, browser workflows, stop criteria and separate owner authorization before a pilot.

## 11. Proposed acceptance tests for next phase

These are proposals, not measured results or approved targets.

- Synthetic farmer A creates farm/field and reads them after reload; farmer B cannot retrieve or mutate A's records by changing IDs/payloads.
- Farmer can save/edit only eligible plan states, record actual planting separately and follow only allowed transitions; no unobserved stage/date is generated.
- Repeating activity with same idempotency key does not duplicate; failed/uncertain save is not shown as committed. Plan/activity write remains transactional.
- Recommendation remains provisional/no-evidence until trusted scoped rules exist; NISR never changes rank and historical output includes period/unit/source.
- Weather requires consent to persist coordinates and labels provider/time/staleness. It is not reported as observed rain, soil moisture, warning or treatment decision.
- No alert without approved scoped rule and tested expiry/deduplication. Opt-in does not promise delivery.
- Crop-health case/photo is visible only to owner/eligible reviewer; unsupported crop gets no fabricated label; update/reply persists; no diagnosis/treatment claim.
- Backend enforces roles/districts and messaging setting; unread/read counts reflect persisted messages.
- Streamlit session entries are labeled temporary and clear at sign-out; no export/overview says they persist.
- Every page separates loading, empty, validation error, service/provider error, stale and confirmed save; retry does not silently duplicate non-idempotent actions.
- Browser tests record browser/version/viewport with synthetic accounts. Keyboard/screen-reader/mobile/Kinyarwanda/connectivity checks use appropriate user research before claims.
- Rule coverage stays zero if rights, identity, qualification, exact scope, current hash, expiry or lifecycle proof is missing. Approval binds to exact versions and cannot be self-approved.
- Before staging writes verify process/source/config/database identity, isolation, schema, backup/restore and rollback. Verify hosted TLS, secrets, CORS/CSRF, rate/file controls, safe logs and monitoring in actual topology.

## 12. Measurable success criteria

No baseline or measured result is available. Targets should be set prospectively.

| Metric | Calculation | Limitations and collection |
|---|---|---|
| Unassisted task completion | Consenting participants completing task without help / participants attempting it. | Depends on language/device/prior experience; voluntary usability study, minimal demographics. Set target before study. |
| Activity persistence | Successful create-and-read-back / valid isolated test cases. | Synthetic staging is not real-network reliability; use API plus browser tests. |
| Save errors/duplicates | Confirmed failed saves / attempts; duplicate commits / retried intents. | Timeouts obscure commits; use pseudonymous intent IDs, never log private content. |
| Time to record activity | Median/distribution from form start to confirmed save. | Not agricultural benefit; voluntary usability timing without keystroke capture. |
| Evidence traceability | Statements with retrievable, versioned, scoped evidence / all recommendation statements. | Citation is not correctness or permission. Any evidence-backed label requires full coverage; current approved count is zero. |
| Independently verified active rules | Count with permitted evidence, scope and trusted approval. | Current count is zero; count alone is not quality. |
| Crop-health follow-up | Eligible reports with documented update within agreed policy / eligible reports. | No response policy/staffing yet; avoid incentives for rushed review. |
| Farmer comprehension | Participants correctly explain forecast vs observation, provisional vs approved, saved vs temporary / tested participants. | Local sample is not nationally representative. |
| Harvest completeness | Records with crop, farm/field, season/date and compatible area/quantity / harvest records. | Completeness is not verified yield; no dedicated current baseline. |

## 13. Verification, files and preservation

### Checks performed

| Command/check | Result |
|---|---|
| Get-Location and source listing | Confirmed project root/source tree. |
| Get-ChildItem -Force -Name .git | .git absent; Git baseline unavailable. |
| Read Phase 3/4/5 reports, README, contracts, workflow/source/test files | Completed. |
| netstat -ano -p tcp \| Select-String -Pattern ':(8000\|8001\|8501\|5173\|18001)\s' | Loopback listeners observed at 8001 PID 27120 and 5173 PID 8980. No service request. |
| .\\.venv\\Scripts\\python.exe -m utils.agronomy_knowledge | Exit 0; valid/current; 5 sources, 4 statements, 6 open issues, 0 rules, 0 approved rules, 0 decisions, 2,020 NISR rows. No write flags. |
| Read registry/manifest JSON and Get-FileHash of NISR CSV | Registry counts confirmed; CSV hash matches manifest. No data write. |
| rg -n '^(revision|down_revision)\\s*=' backend\\migrations\\versions | Source chain ends at 0015_weather_alert_foundation. No migration. |
| Application tests, browser, API/provider/database workflows | Not performed. No test command, API request, browser, database open/query, server launch, migration or provider call. |

### Files changed and data preservation

- docs/farmer-workflow-design-phase-6.md — this report.
- README.md — one link to this report.

No product source, tests, dependencies, environment, migration, database, NISR CSV/manifest, agronomy registry/rules, evidence package or existing frontend build was changed. No rule was activated. No prior report was replaced.

## 14. Conditions before activation, pilot or release

### Before rule activation

- Source-specific reuse permission and traceable version/extraction.
- Crop, variety, geography, season, conditions and prohibited extrapolations defined.
- Identity, qualifications and reviewer authorization verified by trusted process; distinct reviewers and self-approval prevention enforced.
- Decision bound to immutable evidence/rule versions with expiry, withdrawal, conflict, audit and recovery.
- Exact scope, expiry, revocation and fail-closed behavior tested; wording independently reviewed.

### Before farmer pilot

- Privacy/legal approval for purpose, notice/consent, minimization, retention/deletion/export/access, residency, support and incidents.
- Verified isolated runtime/database identity, protected backup/restore, RPO/RTO and rollback.
- Actual hosted TLS/proxy, secrets, CORS, CSRF/cookies, abuse/file limits, safe logs, monitoring and mail tested.
- Authenticated browser tests for farmer/reviewer/admin including cross-account/district denials, refresh, upload, failures and duplicate handling.
- Verified reviewer capacity and honest response expectations; provider/dataset/bulletin rights cleared.
- Pilot purpose, consent, support, adverse-event report, stop criteria, deletion and independent evaluation documented; separate owner authorization.

### Before public release

All pilot prerequisites plus verified production database/runtime, managed secrets, abuse controls, monitoring/incident response, scheduled protected/off-site recovery, accessibility/localization evidence, provider and dataset permissions, data-protection review, support, change controls and rollback rehearsal. Public release is a distinct decision and is not authorized here.

## 15. Recommended next phase

The safest next implementation is a separately approved, narrow React journey integration that summarizes existing farms, plans, activities, weather, crop-health follow-up and messages through existing read APIs. First agree each item's authoritative source, privacy treatment, stale/error semantics, and how farmer-reported activity differs from plan state. Do not include schema changes, recommendation logic, alerts, harvest/yield claims or approval behavior in that slice. Use synthetic isolated data and browser verification only after runtime/database identity and test isolation are proven.

Separately, an evidence owner must obtain source/reuse documentation and initiate the reviewer identity/qualification decision. Until prerequisites exist, recommendations remain provisional and status remains **DEVELOPMENT ONLY**.
