# CropPulse Rwanda — Full System Audit and Remediation, Phase 3

**Audit date:** 2026-10-23  
**Repository:** `C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda`  
**Scope:** current source, data manifests, local database integrity metadata, documentation, and automated checks. No production deployment or live service configuration was inspected.  
**Readiness verdict:** **Development only.**

## A. Executive summary

CropPulse is a substantial development prototype with a React farmer workspace, a FastAPI account/data service, and an existing Streamlit application. It has persistent accounts, farms, crop plans, activities, weather forecasts, crop-health reports, and limited farmer-to-reviewer messages. The local service uses an additive Alembic history and can be configured for SQLite or PostgreSQL. The two frontend experiences are not yet a single fully migrated application: React is the main farmer interface, while a short-lived handoff still opens the Streamlit planning workspace and several Streamlit tools remain session-only.

Two verified defects were remediated in this audit. The NISR source entry in the agronomic evidence registry had a stale CSV checksum even though the CSV matched its own manifest; the source reference and derived agronomy manifest/report now match. A regression test covers that mismatch. The Windows intake publication issue from Phase 3A.1 was rechecked: publication now uses a pending-marker commit rather than a directory rename, preserves failed packages, and the focused/full suites pass. The specific Windows mechanism that denied the old rename remains unknown; no antivirus cause is claimed.

The system is **not ready for a controlled farmer pilot or public production**. Most importantly, the approved agronomic-rule registry still has **zero approved rules**. Crop ranking and planting information come from provisional CropPulse-authored tables and are not verified agricultural guidance. The experimental image screening is limited to maize and is not a diagnosis. Weather alerts have no approved active rules or generator. Live market prices are not integrated. Provider reuse/licensing, privacy and retention policy, production infrastructure, deployment throttling, live backup/restore, and authenticated browser workflows remain unverified or unresolved.

This report distinguishes source presence and automated checks from browser verification, external validation, and operational readiness. It does not certify the application, agricultural evidence, institutions, or compliance.

## B. Complete feature inventory

| Feature | Status | Evidence and remaining boundary |
|---|---|---|
| React account sign-in, registration, session, and settings | Implemented but not fully verified | Cookie-based browser flows and API routes exist; API/frontend tests pass. SMTP delivery, hosted configuration, and complete authenticated browser workflows were not tested in this audit. No MFA or registration email verification is implemented. |
| Farmer farms, fields, activities, and saved crop plans | Implemented but not fully verified | Authenticated owner-scoped API and React/Streamlit workflows exist; local automated checks cover persistence and ownership. No current authenticated browser or live production-database test was performed. Farmer-entered coordinates and records are not independently verified. |
| Crop comparison/recommendations and planting calendar | Partially implemented | A deterministic provisional engine uses broad CropPulse zone-fit, season, elevation, and water categories. The API explicitly says NISR statistics do not rank crops. The approved evidence registry contains zero rules; this is not validated crop advice or a probability of success. |
| NISR national statistics | Implemented and verified for structural integrity | The React statistics page and Streamlit analytics use the same validated CSV loader. The unchanged CSV has 2,020 rows, all 30 districts, 8 mapped crop groups, 2023–2025 A/B/C and 2026 A/B, and matches its existing file checksum. This verifies file/structure consistency, not NISR estimates or redistribution rights. It is descriptive context only. |
| Weather point forecast | Implemented but not fully verified | React and Streamlit call the shared Open-Meteo adapter. It validates coordinates against a Rwanda bounding extent, uses timeout/cache/attribution, distinguishes forecasts from observations, and labels stale cache. Coordinates are not point-in-polygon verified; forecasts are not farm observations or recommendation inputs. No live provider service-level test was performed. |
| Weather and climate bulletins | Partially implemented | Original METEO RWANDA PDFs and source-linked numeric transcriptions exist; some bulletin data is persisted and exposed. Product-level reuse permission is not documented as granted, and bulletin issue/validity/transcription coverage has limitations. Do not describe forecasts as verified observations. |
| Weather alerts | Partially implemented | Preferences, history/status routes and storage exist, but `utils/weather_alert_rules.py` has no approved rules. There is no active weather-to-agriculture alert-generation workflow. A saved preference does not mean alerts are being generated. |
| Crop-health reporting and reviewer follow-up | Partially implemented | Private farmer reports/photos persist and active reviewers have district-scoped case access. The photo classifier screens maize only; other crops are unsupported. Model outputs are uncalibrated candidates, not diagnoses. Reviewer role does not verify credentials. No pesticide, medicine, dose, or treatment recommendation is produced. |
| Farmer-to-reviewer private messaging | Implemented but not fully verified | Persisted text conversations, participant checks, reviewer district eligibility, admin enable/disable setting, pagination, and read states are present and covered by tests. It is not farmer-to-farmer messaging; no groups, attachments, WebSockets, advanced moderation, or current live-browser test. |
| Administration and reviewer controls | Implemented but not fully verified | Admin routes manage account status/roles/permissions, reviewer district assignments, messaging configuration and audit events. Reviewer status is an access role, not proof of professional qualification. No authenticated admin browser test was performed here. |
| Streamlit planning and analytics | Implemented but not fully verified | Streamlit remains available via a one-time account handoff and shares the FastAPI account service. Some analytics and operational forms remain session-only. Its farmer-facing tools have not all been migrated into React. |
| Market prices and farm economics | Partially implemented | Economics can use farmer-entered assumptions and provisional yield ranges; session-only market observations are manually entered and unverified. There is no live or independently sourced market-price service. Do not present manual entries as current market prices. |
| Feedback, pest observations, extension notes, cooperative logs, local weather observations | Partially implemented | Legacy Streamlit forms store temporary session entries and provide exports. These entries are not durable shared reports, institutional submissions, notifications, or verified measurements. |
| Hekitari referral | Not implemented as an integration | The button/link opens an external service. No shared sign-in, federation, API connection, or farm-data transfer is implemented. |
| Agronomic evidence intake | Implemented as a local operator workflow; external contribution is blocked | File limits and structure checks, versioned packages, permission metadata, hashes, lifecycle gates, and reviewer separation exist. It is not a public upload endpoint. Local actor/qualification fields are attestations, not authenticated identity or verified credentials. Packages do not automatically enter the farmer registry. |
| Kinyarwanda interface | Partially implemented | Streamlit contains English/Kinyarwanda support in selected farmer workflows. React and detailed agronomic/analytics copy remain predominantly English and have not had a full professional translation/accessibility review. |
| Offline, SMS/USSD/voice, field-partner workflow | Not implemented | No robust offline sync, SMS/USSD/voice delivery, or cooperative/extension partner operating service was found in the current application. |

### Status meanings

- **Implemented and verified:** behavior and stated scope were checked with the evidence described; this is not a production certification.
- **Implemented but not fully verified:** relevant source and automated tests exist, but important browser, live-service, or operational proof is absent.
- **Partially implemented:** some workflow stages exist while a required stage, reliable evidence, data source, or outcome is missing.
- **Not implemented:** no complete implementation was found in the inspected source.
- **Blocked:** progress depends on external permission, source data, qualified specialist review, or organizational decisions.

## C. Prior audit reconciliation

### Phase 2 findings

The Phase 2 report's main boundaries remain accurate. React and FastAPI are the primary durable farmer path; Streamlit still has temporary/session-only tools. No approved agricultural guidance rules exist. Crop-health AI is experimental; alert-generation rules are empty; live market data is absent; and deployment, privacy, licensing, and full browser verification are incomplete.

### Phase 3A security and recovery

- **A1, production configuration:** source now requires an explicit runtime environment and secret; staging/production require explicit HTTPS CORS origins, secure cookies, and migrations rather than auto-schema creation. This is source/test evidence only; actual hosted settings remain unknown.
- **A2, request body size:** API middleware caps bodies at 8 MiB before framework parsing; crop-photo validation has a separate 5 MiB file limit. Edge/proxy limits and concurrent-request controls still need deployment testing.
- **A3, abuse controls:** database-backed throttles cover sensitive account actions. General API, upload, weather, and messaging traffic still requires gateway/rate and concurrency controls.
- **A7, recovery:** the prior Phase 3A local restore drill used a selected pre-existing SQLite backup and an in-memory destination; it proved that backup copy's integrity and schema at the time, not that it matches a live database or meets production RPO/RTO. It was not repeated in this audit.
- **A8, privacy:** a data inventory exists, but retention, legal basis, user rights, data residency, support, and incident processes remain unresolved organizational/legal decisions.

### Phase 3A.1 Windows intake publication

The Phase 3A baseline recorded three intake tests failing at the final Windows directory rename with `PermissionError: [WinError 5]`. Current code no longer requires that directory rename. It builds the destination under `.publication_pending`, copies and verifies package files, and removes the marker to publish. Listing and coverage skip pending packages; publication I/O failures preserve the hidden staging package and pending destination. Tests confirm failures cannot be counted as active guidance. Source handles were closed and observed ACLs matched; the exact OS-level denial trigger was not established. The failure mode is addressed without asserting an unsupported environmental cause.

### New data-integrity finding

The NISR CSV's actual SHA-256 matched `data/verified/MANIFEST.json`, but `data/agronomy/sources.json` still referenced an older CSV hash. That caused the agronomic pack validator to return `valid: false`. The source-registry checksum reference was corrected to the unchanged manifest value, and the derived agronomy `MANIFEST.json` and `validation_report.json` were regenerated. A test now verifies that deliberately mismatched NISR registry hashes fail validation. No rule was added or approved.

## D. Prioritized findings

Severity is a readiness priority based on local evidence, not a demonstrated exploit rating.

| ID / severity | Finding and evidence | Risk / remediation and verification | Dependencies / status |
|---|---|---|---|
| FSA-01 — **Critical readiness gate** | No approved, in-date agronomic rules are registered. `data/agronomy/rules.json` and review decisions are empty; recommender code labels its broad crop fit and timings provisional. | Unsupported advice could be mistaken for validated Rwanda guidance. Keep limits prominent; do not promote NISR statistics or test data to rules. Pack validator now passes while reporting zero approved rules. | Requires source-backed, crop/variety/season/geography/context scope and qualified local review. Open. |
| FSA-02 — **High** | Weather preferences/history are implemented but the approved weather-rule list is empty; no automatic rule-based alert generation exists. | Farmers could mistake opt-in for a working alert. Continue to disclose alerts are unavailable until a sourced, scoped, approved rule and scheduled generation/expiry/monitoring are implemented. | METEO RWANDA source permissions and specialist review. Open. |
| FSA-03 — **High** | Production deployment, rate limits, concurrency controls, TLS/proxy, monitoring, managed secrets, and hosted logging were not inspected. Application account throttles are not general API throttles. | Abuse, outage, or misconfiguration risk remains. Apply and test gateway controls, request/concurrency limits, HTTPS, safe logs, secret management, and monitoring in a controlled staging deployment. | Infrastructure/operations owner. Open. |
| FSA-04 — **High** | No verified production backup schedule, database target identity, backup encryption/permissions, monitoring, or live restore was established. Local database identity is not proof of the serving process's database. | Data loss or restore-to-wrong-database risk. Identify the actual runtime target, define recovery objectives, take protected backups, and restore to an isolated target before pilot. | Deployment operator; no migration was applied. Open. |
| FSA-05 — **High** | Crop-health model uses PlantVillage data and a bundled model; it is maize-only, uncalibrated, and not evaluated on Rwanda field photos. HF currently tags the dataset CC BY-SA 3.0; local artifacts do not pin an immutable source revision/license package. | Dataset/model attribution, share-alike/derivative scope, redistribution, and commercial-use implications need qualified review. Do not make diagnosis or treatment claims. | [Hugging Face dataset card](https://huggingface.co/datasets/mohanty/PlantVillage); counsel and local evaluation. Open. |
| FSA-06 — **High** | Open-Meteo Free API is currently limited to non-commercial use; its published terms describe call caps and CC BY 4.0 attribution. Whether CropPulse's intended service qualifies as non-commercial has not been established. | A free-tier deployment could violate provider terms if the service is commercial/promotional. The terms disclaim accuracy/availability guarantees. Confirm status and use a suitable paid plan/license if needed. | [Current Open-Meteo terms](https://open-meteo.com/en/terms), [pricing/licence information](https://open-meteo.com/en/pricing). Open. |
| FSA-07 — **High** | METEO RWANDA bulletin PDFs and numeric transcriptions are present; exact reuse/redistribution permission was not evidenced. NISR source data is identified, but source attribution alone does not settle all reuse permissions. | Display or redistribution may exceed permitted use. Obtain product/dataset-specific terms and keep issue/valid periods, attribution, and source locators. | METEO RWANDA and NISR permission/terms. Open. |
| FSA-08 — **High** | Farmer personal data, farm coordinates, crop-health photos, messages, and account records persist. The Phase 3A inventory documents deletion and logging caveats, but there is no complete approved retention, access-request, breach, or residency policy. | Privacy and operational risk for real farmers. Minimize collection and approve notice, retention, deletion/export, access, incident, support, and residency policy before onboarding. | Organizational/legal owner. Open. |
| FSA-09 — **High** | Account recovery and email change rely on configured SMTP; live delivery was not exercised. No registration email verification or MFA was found. | Users may be unable to recover access; account assurance is limited. Verify SMTP/one-use expiry/redaction in staging and decide on MFA/email verification based on risk. | Mail provider and deployment. Partial/open. |
| FSA-10 — **Medium** | Live market prices are absent. User-entered market/weather/pest/extension/cooperative forms in Streamlit are session-only. | Users may expect durable records or sourced prices. Label these as temporary/manual and unverified; define sources and persistence/privacy before replacing them. | Trusted market sources and product decisions. Open. |
| FSA-11 — **Medium** | React/Streamlit migration is incomplete; only sign-in was browser-checked in the pre-existing Phase 3 browser record. No authenticated farmer/reviewer/admin workflow was browser-tested in this audit. | Automated checks do not establish usability or E2E persistence. Complete browser workflows on isolated test data at mobile/desktop sizes, including expiry, failure, and role boundaries. | Authorized test accounts and browser environment. Open. |
| FSA-12 — **Medium** | React localization/accessibility/low-bandwidth coverage has not been comprehensively reviewed. English remains primary for detail-heavy copy. | Farmers may misunderstand labels or fail to use the service on supported devices. Translate and review Kinyarwanda with fluent local agricultural users; run accessibility and low-bandwidth checks. | Local language and user review. Open. |
| FSA-13 — **Medium** | The current app has no offline sync or feature-phone/SMS/USSD/voice workflow. | Web-only access limits reach and resilience. Treat these as future product work, not existing capabilities. | Channel, partner, funding, and privacy decisions. Planned. |
| FSA-14 — **Fixed** | Agronomic source registry checksum reference was stale relative to the matching NISR CSV/manifest checksum. | Updated `sources.json`, regenerated agronomy manifest/report, and added regression test. Validator returns valid; NISR file and its manifest were not rewritten. | Completed locally; see verification. |
| FSA-15 — **Fixed at application boundary; OS trigger unresolved** | Windows denied the prior directory rename during intake publication. | Publication now uses a pending sentinel and copy/integrity-check commit; regression tests prove hidden/un-counted failure and normal publication. The precise Windows subsystem cause remains unknown. | Completed in Phase 3A.1; local tests pass. |

## E. Changes made

### This Phase 3 audit

- `data/agronomy/sources.json` — corrected only the NISR registry CSV hash and its descriptive version string to match the existing verified-data manifest.
- `data/agronomy/MANIFEST.json` — regenerated the derived agronomy pack hashes after the source-reference correction.
- `data/agronomy/validation_report.json` — regenerated the derived report; it now validates with zero approved rules and records the NISR file as structurally/hash valid.
- `tests/test_agronomy_knowledge.py` — added a mismatch regression using only a temporary test fixture.
- `docs/full-system-audit-remediation-phase-3.md` — this full audit and remediation record.
- `README.md` — link to this report.

### Prior Phase 3A.1 change re-verified, not newly edited here

`utils/agronomy_intake.py`, `tests/test_agronomy_intake.py`, `docs/security-privacy-recovery-phase-3a.md`, and `docs/full-application-audit-phase-2.md` contain the preceding Windows-safe intake publication fix and dated history. This audit re-ran its tests and preserved the original findings.

## F. Verification record

### Checks run for this audit

| Command/check | Result |
|---|---|
| `\.venv\Scripts\python.exe tests\windows_safe_pytest.py tests\test_agronomy_intake.py tests\test_agronomy_knowledge.py` | **30 passed, 1 warning** (AnyIO pytest assert-rewrite warning). Includes the prior intake cases, publication regressions, and new NISR checksum-mismatch regression. |
| `\.venv\Scripts\python.exe tests\windows_safe_pytest.py` | **159 passed, 1 warning** (AnyIO pytest assert-rewrite warning). |
| `\.venv\Scripts\python.exe tests\windows_safe_pytest.py tests\test_agronomy_intake.py tests\test_agronomy_knowledge.py tests\test_recommender.py` | **41 passed, 1 warning** (same AnyIO warning). |
| `\.venv\Scripts\python.exe -m utils.agronomy_knowledge --write-manifest --write-report` | **Passed; `valid: true`, manifest current, NISR integrity valid, 0 approved rules, 6 open quality issues.** This intentionally regenerated only derived agronomy metadata/report after correcting the source reference. A subsequent read-only `validate_pack()` returned `valid: true`, `manifest_status: current`, and no findings. |
| NISR file SHA-256 compared with `data/verified/MANIFEST.json` | **Match.** Actual and expected: `98de5073d00f60231df496da3c19912834a3156a7f2f044bd6eaa5108f313927`. No CSV or NISR manifest write occurred. |
| SQLite read-only inspection (`mode=ro`, `PRAGMA integrity_check`, `PRAGMA foreign_key_check`, Alembic revision) | `data/croppulse_phase1.sqlite3`: integrity `ok`, revision `0015_weather_alert_foundation`, no FK issue. `data/croppulse_local.sqlite3`: integrity `ok`, no application tables/revision. Two pre-existing Phase 1 backups: integrity `ok`, revision `0014_weather_bulletin_records`, no FK issue. No private row contents or counts were printed. |

### Applicable frontend checks from the immediately preceding Phase 3A.1 run

The frontend source did not change during this audit. On the same frontend tree, the following checks were executed in the preceding remediation turn:

- `npm test -- --configLoader native --pool=threads --maxWorkers=1`: **35 passed across 4 files**. Plain `npm test` failed before test execution because Windows returned `spawn EPERM` while Vitest attempted worker startup.
- `npm run typecheck`: passed.
- `npm run lint`: passed.
- `npm run build -- --configLoader native`: passed.

These checks do not establish authenticated browser workflows or deployment behavior. The pre-existing Phase 3 browser report documents sign-in-screen captures only; it did not sign in or verify farmer data flows. No browser was available for this audit.

### Not performed in this audit

- No current browser, authenticated farmer/reviewer/admin, live external forecast, or live API-to-database end-to-end test.
- No inspection of a running service's environment or proof of which database a live service uses.
- No new backup restore test. The earlier Phase 3A in-memory restore evidence remains limited to the selected local backup and is not a production restore drill.
- No hosted deployment security, rate-limit/concurrency, penetration, load, accessibility, screen-reader, low-bandwidth, or mobile-device testing.
- No migration, deployment, external email delivery, or production action.

## G. Data and database preservation

- **NISR CSV:** unchanged. Its SHA-256 matches the existing `data/verified/MANIFEST.json` value above.
- **NISR manifest:** unchanged.
- **Agronomic rules and review decisions:** unchanged; both remain empty of approved rules/decisions. No demonstration guidance was added.
- **Agronomic source registry:** one stale checksum reference was corrected. The agronomy pack `MANIFEST.json` and `validation_report.json` were regenerated as derived artifacts.
- **Weather source PDFs, PlantVillage images/model, and user databases:** not edited by this audit.
- **Migrations:** none applied or changed. The local Phase 1 SQLite candidate is at revision `0015_weather_alert_foundation`; this does not identify the live service database. The default URL is `sqlite:///./data/croppulse_phase1.sqlite3`, but `CROP_PULSE_DATABASE_URL` overrides it. No running process/configuration was inspected.
- **SQLite:** only read-only integrity/schema/revision checks were made. No private record contents were read out or reported. No destructive operation occurred.

## H. External and specialist dependencies

### External data and terms

- **Open-Meteo:** the current provider terms permit its Free API only for non-commercial use and publish caps of fewer than 10,000 calls/day, 5,000/hour, and 600/minute, plus CC BY 4.0 attribution. The terms also disclaim accuracy/availability warranties. Paid plans provide a commercial-use license; intended CropPulse commercial status, cost, and plan choice remain undecided. See [terms](https://open-meteo.com/en/terms) and [plans](https://open-meteo.com/en/pricing). Terms were checked on 2026-10-23 and may change.
- **PlantVillage:** the current Hugging Face dataset page tags `mohanty/PlantVillage` CC BY-SA 3.0. Local model documentation records the dataset/model connection, but the downloaded snapshot is not pinned to a documented immutable revision and no legal opinion confirms whether/how the trained weights are a covered adaptation or suitable for commercial distribution. Preserve attribution and resolve license obligations before distribution. See [Hugging Face dataset card](https://huggingface.co/datasets/mohanty/PlantVillage) and [original repository](https://github.com/spMohanty/PlantVillage-Dataset).
- **METEO RWANDA:** source bulletins are present and some numeric ranges are transcribed; no product-level redistribution permission was evidenced in the repository. Obtain permission/terms before deployment that redistributes files or derived values.
- **NISR:** official source links and workbook/checksum provenance are recorded. Structural and checksum validation establish file integrity, not independent verification of survey estimates or full reuse permission. Preserve the source's scope and confirm applicable reuse/attribution terms.
- **Market data:** no live provider/source integration was found; manual session values are not external market facts.

### Agricultural, legal, and institutional review

RAB/NISR institutional approval, specialist qualification, or professional certification cannot be inferred from a URL, title, reviewer account role, or passing test. Crop advice requires traceable, current source material and qualified local review for crop, variety, district/geographic level, season, and required soil/environmental conditions. Disease-specific treatment guidance and pesticide use require separate locally applicable evidence and safety/legal checks. Legal/organizational approval is still needed for privacy, retention, data residency, user rights, support, and incident response.

## I. Remaining roadmap

1. **Keep advice and alerts bounded:** retain provisional labels and no-evidence states; do not create rule coverage through NISR statistics, synthetic records, or generic literature. Completion means qualified local review approves actual sourced rules with scope, limits, expiry, and independent validation.
2. **Resolve deployment/provider rights:** decide commercial status and Open-Meteo plan; obtain METEO RWANDA/NISR reuse terms; resolve PlantVillage/model licensing before public distribution.
3. **Prepare controlled staging:** identify the actual database URL without exposing credentials; provision secure DB/secret/TLS/proxy; configure gateway rate/concurrency controls, request limits, redacted logs, monitoring, backups, and incident response.
4. **Prove recovery:** create a protected backup of an identified staging database, restore to a separately named isolated target, check integrity, schema, and representative expected records without exposing private data; measure agreed recovery objectives.
5. **Complete authenticated browser QA:** with disposable test accounts and isolated data, verify farmer, reviewer, and admin routes; ownership and district scopes; save/reload/edit; session expiry; messaging/read states; weather failures/staleness; crop-health image upload and reviewer update; and mobile/accessibility/language behavior.
6. **Govern crop-health AI:** obtain consented Rwanda field images and specialist labels, immutable dataset/model provenance, farm/time-separated evaluation, calibration and abstention, privacy policy, and independent error review before broadening beyond experimental maize screening.
7. **Improve language and reach:** review all farmer-facing Kinyarwanda terms; assess low-bandwidth behavior, offline expectations, and partner-assisted channels. Do not claim feature-phone support until implemented and field-tested.
8. **Define product persistence:** decide whether market observations, feedback, local weather readings, extension reports, and cooperative logs should remain session-only or become private durable records with consent, access, retention, and abuse controls.

## J. Readiness verdict

**Development only.** Automated suites, registry validation, static type/lint checks, a production frontend build, local SQLite integrity checks, and an earlier limited sign-in browser check provide useful engineering evidence. They do not establish authenticated full-workflow usability, deployment configuration, provider licensing, recovery objectives, field performance, legal/privacy readiness, or adequate approved agronomic guidance. With zero approved rules and an experimental non-diagnostic model, the product must continue to describe crop advice and image results as provisional and must communicate evidence gaps clearly.
