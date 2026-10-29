# Weather alert evidence and readiness

## Current state

The application has **zero approved automated agricultural weather rules**. `utils/weather_alert_rules.py` is the registry; it intentionally contains no rules. Passing code review or automated tests is not agricultural approval. No weather value currently causes a planting, irrigation, pesticide, disease, or other farm warning.

Before registering a rule, record all of the following in a reviewed change:

| Required field | Meaning |
| --- | --- |
| Stable rule ID and version | Identifies the exact rule implementation used for an alert |
| Alert type, weather variables, units | Defines what data the rule consumes |
| Crop/activity/geographic scope | Defines who and where the advice applies to; use `not applicable` only with a reason |
| Source title, institution, URL, publication/revision date | Lets the recommendation be independently checked |
| Evidence status | Officially sourced, locally specialist-reviewed, provisional, or information-only |
| Applicability and limitations | States known exclusions and what a forecast cannot establish |
| Reviewer identity, institution, review date, approval | Must reflect a real local agronomist or extension review where required |

Rules without evidence and approval stay inactive. Nationwide METEO RWANDA rainfall outlook ranges and Open-Meteo point forecasts do not independently establish crop-specific actions or thresholds.

## Field locations

Saved forecasts can be linked to a field only if the field is active, belongs to the authenticated account, has saved coordinates, and the submitted coordinates match those saved coordinates after the existing four-decimal storage rounding. Otherwise the saved forecast remains coordinate-only. This proves an account-owned record association, **not** that the point lies inside the actual farm or Rwanda.

CropPulse currently has no local Rwanda polygon dataset or installed point-in-polygon library. The existing NISR rectangular extent check is only an extent check and can include locations outside Rwanda. Field coordinates remain farmer-entered; device and manual coordinates are never silently attached to a selected farm. Coordinates continue to be stored only as part of the forecast record with explicit save consent.

## Opt-in preferences and alert history

Migration `0015_weather_alert_foundation` adds optional field linkage and provenance labels to saved forecasts, `weather_alert_preferences`, and persistent `weather_alerts` history. An alert can retain its saved-forecast reference, forecast retrieval time, field/farm name snapshots, validity dates, reason, evidence snapshot, rule approval state, and acknowledgement/dismissal timestamps. Preferences default off and are scoped to an authenticated farmer-owned field. The React Weather & Climate page lets the farmer enable or disable a future in-app preference for each field with coordinates within the supported extent. It clearly states that no rules are active and that the preference does not start monitoring.

The alerts API returns only the authenticated farmer's records. `utils.weather_alert_rules.weather_alert_dedupe_key` produces a stable SHA-256 key from recipient, farm, field, alert type, rule ID/version, and valid date range; retrieval time is deliberately excluded so a refreshed forecast for the same event does not duplicate it. The database enforces key uniqueness. Expired active records are returned with derived status `expired` and retained in history; they are not deleted. Active alerts may be acknowledged or dismissed by their recipient before expiry. There is currently no API endpoint or scheduled process that generates an alert record. The alert table is a persistence foundation, not evidence that alerts are being generated.

## Freshness policy for any future generator

There is no active alert processor and no configured automatic-alert freshness threshold. Before enabling one, document an operational maximum age that matches the provider update cadence and the reviewed rule's valid period. The existing adapter's stale fallback must be display-only for alert purposes. Missing, malformed, unavailable, stale, or superseded forecasts must be rejected.

## Scheduling and operations

No scheduler, task queue, or worker dependency is present in `requirements.txt`, and no background processing is configured by the application. Do not run forecast checks from web request handlers. The smallest option after rules and opt-in eligibility are approved is a supervised OS/container scheduled command invoking an idempotent backend management task at a documented interval. It should query only opted-in eligible fields, use the existing adapter/cache, avoid recording raw coordinates in logs, record per-run outcomes, and rely on database uniqueness for deduplication. Monitor provider limits, transient failures, and alert counts. Retry only transient failures with a bounded policy; validation failures should not retry. This command and scheduler are not implemented in this change.

The Open-Meteo cache is in-process and not shared across workers or replicas. A multi-worker deployment can therefore issue duplicate upstream calls and cannot rely on the process cache as a shared rate limiter. Add shared cache/rate controls only when the deployment topology requires them.

## Licensing and source requirements

The UI preserves Open-Meteo attribution and its CC BY 4.0 notice. Open-Meteo's current [terms](https://open-meteo.com/en/terms), checked 2026-10-22, restrict the free API to non-commercial use, specify request limits, allow blocking for misuse, and disclaim accuracy/completeness/availability guarantees. The terms identify commercial products, ads, subscriptions, and promotional use as commercial. A public or revenue-generating CropPulse deployment needs a licence/use assessment and may need a paid API plan; no paid plan is enabled or purchased. Review terms again before deployment.

The current adapter calls the public forecast endpoint without an API credential. It requests daily maximum/minimum temperature and total precipitation for seven days. Open-Meteo describes the API as model forecasts; these are not station observations. See its [Forecast API documentation](https://open-meteo.com/en/docs). METEO RWANDA PDF reuse permission remains unconfirmed as documented in `docs/weather-data-review.md`.

## Streamlit

The existing Streamlit district-context, manual-coordinate, forecast, and session-only observation workflow is unchanged. Its weather observations remain unverified and session-only; they are not converted into saved fields, forecast records, or alerts.

## Verification commands

From the repository root in PowerShell:

```powershell
.\.venv\Scripts\python.exe tests\windows_safe_pytest.py tests\test_weather.py tests\test_weather_ui.py tests\test_backend_api.py tests\test_weather_alert_migration.py tests\test_weather_alert_rules.py
Push-Location frontend
npm test -- --configLoader native --pool=threads --maxWorkers=1
npm run typecheck
npm run lint
npm run build -- --configLoader native
Pop-Location
```

The migration is additive and should be reviewed/backed up like other deployment migrations. These checks use an isolated temporary SQLite database for migration verification; they do not apply migration `0015` to the configured application database.

## Phase 4 verification record — 2026-10-22

### Database target and migration decision

In the verification shell, `CROP_PULSE_DATABASE_URL` and `CROP_PULSE_ENVIRONMENT` were unset. The effective application/Alembic default is the local SQLite file `data/croppulse_phase1.sqlite3`; no PostgreSQL target was configured in this shell. The file passed `PRAGMA integrity_check` and was at revision `0014_weather_bulletin_records`. Metadata-only inspection found 5 farmer rows, 6 farm rows, 0 field rows, and 2 saved forecast rows. No farmer records or forecast contents were used as test fixtures. The separate legacy `data/croppulse_local.sqlite3` file passed integrity check but has no Alembic version table and was not used.

The default path is local, but the environment marker is absent and this checkout does not establish whether its persisted account data is development-only. Therefore its environment classification is **uncertain**. No backup was created and migration `0015` was **not applied** to either existing database. This follows the safety rule to stop before mutation when the database purpose is uncertain. An existing backup file is not treated as proof of a current, restorable backup.

Migration `0015_weather_alert_foundation` was reviewed as an additive migration. It adds nullable forecast-to-field metadata with a `SET NULL` field foreign key, defaulted location provenance, check constraints and an index; it adds preference/history tables with farmer/field/forecast foreign keys, a unique farmer-field preference, a unique deduplication key, status/period checks, and lookup indexes. Existing saved forecasts receive null field/name snapshots and the `manual` source default. The downgrade drops the new preference/history tables and the added forecast association data; it is destructive to data created in those new tables and must not be used as a routine rollback after they contain records.

The disposable migration regression test upgraded from revision `0014` with a representative legacy saved forecast, verified its ID and values survived, checked the new forecast columns and alert tables, downgraded to `0014`, and verified the legacy forecast still existed. This is not a restore drill for the configured database. No backup location or restoration verification applies because no backup was made. The repository recovery guide requires stopping SQLite writers before copying, keeping the copy access-restricted, and verifying it with `PRAGMA integrity_check`; the local `.backups` directory is not off-site or encrypted.

### Authorization and automated checks

Code review confirmed alert preference list/update and alert history/status routes require `current_farmer`; queries scope preferences to the authenticated farmer's currently owned, unarchived fields and history/status to the authenticated recipient. Forecast saving verifies field ownership and saved-coordinate equality; forecast history filters by farmer ID. Existing API tests cover missing authentication, other-farmer field access, owner-only forecast/history, preference defaults and reversible opt-in, private alert history, deduplication, acknowledgement, dismissal conflict for expired records, and no active rules.

Actual commands and results from the repository root / `frontend` directory:

```text
.\.venv\Scripts\python.exe tests\windows_safe_pytest.py tests\test_weather.py tests\test_weather_ui.py tests\test_backend_api.py tests\test_weather_alert_migration.py tests\test_weather_alert_rules.py
34 passed, 1 PytestAssertRewriteWarning

.\.venv\Scripts\python.exe tests\windows_safe_pytest.py
126 passed, 1 PytestAssertRewriteWarning

npm test -- --configLoader native --pool=threads --maxWorkers=1
4 test files passed, 35 tests passed

npm run typecheck
passed

npm run lint
passed

npm run build -- --configLoader native
passed
```

The full Python suite took 125.47 seconds. The warning reports that the `anyio` module had already been imported before pytest assertion rewriting; no test failed.

### Browser, live provider, and workflow status

No browser automation tool is available in this environment, and no approved test-account credentials or disposable migrated browser environment were provided. No authenticated browser workflow was run. Read-only checks found React (`127.0.0.1:5173`) and Streamlit (`127.0.0.1:8501`) roots responding HTTP 200 and the API health endpoint (`127.0.0.1:8001/health`) returning `{"status":"ok"}`. However, the API's live OpenAPI schema does not contain `/v1/weather/alert-preferences`, `/v1/weather/alert-preferences/{field_id}`, `/v1/weather/alerts`, or `/v1/weather/alerts/{alert_id}/status`; direct requests to the preference and history list routes returned 404. `/v1/weather/forecasts` returned 401 without credentials, as expected for its protected route. This confirms the API currently listening on port 8001 is out of date or otherwise inconsistent with this source tree. It was not restarted because its effective database target and purpose are not known, and no migration was applied.

React component tests exercise saved-field selection, explicit save consent, device-location denial, forecast presentation, preference updates, and no scheduling/generation request. Backend/unit tests simulate stale-cache fallback, malformed provider payloads, invalid coordinates, field ownership, and private history. These do not verify a live Open-Meteo request, browser permission behavior, persistence across a real sign-in, or the Streamlit UI at runtime. Streamlit code was not changed and its workflow remains unverified in this phase.

The rule registry remains empty; no agricultural alerts were generated or activated. Manual/device coordinates remain coordinate-based and are not represented as verified farm locations. No deployment, production-readiness, or real-user verification is claimed.

### Required before applying `0015`


The API owner must also confirm the target process and database for port `8001`. After the database environment is identified and any approved migration is completed, stop the stale API process and start the current application with the intended `CROP_PULSE_DATABASE_URL`; then confirm that its OpenAPI schema contains the alert routes before browser verification. Do not reuse the process until its configuration is known.

## Phase 4B read-only live API identity addendum — 2026-10-22

### Confirmed source registration

`backend/api.py` constructs `app = FastAPI(title="CropPulse Rwanda Farmer Records API", version="1.0.0")` directly; weather handlers are decorated on this app, not on a separately imported router. The current source registers `POST /v1/weather/forecast`, `GET /v1/weather/forecasts`, `GET /v1/weather/alert-preferences`, `PUT /v1/weather/alert-preferences/{field_id}`, `GET /v1/weather/alerts`, and `PATCH /v1/weather/alerts/{alert_id}/status` (alongside the weather bulletin and climate-data routes). The alert handlers depend on `current_farmer`; the preference update accepts `WeatherAlertPreferenceUpdate` and alert status uses `WeatherAlertStatusUpdate`. Models `WeatherAlertPreference` and `WeatherAlert` are defined in `backend/models.py`. The route definitions are unconditional module-level decorators; no conditional alert-router inclusion or configuration gate was found. Importing the current source app and enumerating `app.routes` confirmed all six expected endpoints. No extra router registration is required.

### Live process and schema evidence

Read-only `netstat -ano` identified PID `16264` listening at `127.0.0.1:8001`; `Get-Process` identified the process as `python` and its executable as `C:\Users\Student\AppData\Local\Programs\Python\Python312\python.exe`. Windows denied access to the process command line, parent PID, and associated CIM process details (`Get-CimInstance Win32_Process` returned access denied). Consequently its parent process, working directory, entry point/module, inherited `CROP_PULSE_DATABASE_URL`, and project copy cannot be confirmed from this session. No unsanitized command line or process environment was printed.

Unauthenticated read-only requests returned `/health` HTTP 200 with `{"status":"ok"}` and `/openapi.json` HTTP 200. The live OpenAPI metadata reports the same title and version as the current source. It lists `/v1/weather/forecast`, `/v1/weather/forecasts`, `/v1/weather/bulletins`, `/v1/weather/climate-data`, and the bulletin document route, but omits the two alert preference paths and both alert history/status paths. Direct GET requests to `/v1/weather/alert-preferences` and `/v1/weather/alerts` returned 404; `/v1/weather/forecasts` returned 401, consistent with a protected path being present. No alternate weather prefix was found in the live schema.

### Diagnosis and confidence

Confirmed: the process serving port 8001 is a Python 3.12 process whose live schema is missing source-defined, unconditional routes. Confirmed: its schema title/version match the source's generic metadata, which does not identify a checkout. The source route definitions and direct source-app route enumeration rule out a conditional omission in this checkout. **Most likely explanation:** the listener loaded an older or different application module/source tree that predates these routes. Confidence is **moderate** for a stale/different loaded app, but low for distinguishing an older process in this checkout from a process launched in another checkout or a different application with copied title/version. The denied command-line/CIM access prevents stronger attribution. Neither matching schema metadata nor a healthy response proves that the current source file serves the listener.

### Database identity

The current source's `backend.db.database_url()` reads `CROP_PULSE_DATABASE_URL` at runtime and falls back to `sqlite:///./data/croppulse_phase1.sqlite3`; Alembic's `backend/migrations/env.py` independently reads the same environment variable and fallback. The Streamlit launcher sets a default database URL for a child API only when it starts that child; it does not establish the environment of an already running listener. In this inspection shell the variable was unset, but that says nothing about PID 16264's environment. Because its command line/process environment and working directory were inaccessible, the live database target, its Alembic revision, and environment classification remain **unknown**. Revision `0014` previously observed in the project default SQLite file cannot be attributed to PID 16264.

### Safe next step

An operator with permission to inspect the service should identify PID 16264's sanitized launch command, parent/launcher, working directory, and effective database target without disclosing secrets; confirm which project copy and environment it is intended to serve; and confirm whether that database contains disposable development data or records requiring preservation. Only after those confirmations and the separately required verified backup should a restart or migration be considered. This phase made no process, source, configuration, or database changes and did not connect to any database.

## Database initialization and controlled launch note

`backend/db.py::database_url()` reads `CROP_PULSE_DATABASE_URL` from the process environment when called; absent that variable it returns `sqlite:///./data/croppulse_phase1.sqlite3`, a relative path resolved from the process working directory. SQLAlchemy engine construction is lazy and does not itself create tables. Importing `backend.api:app` builds route/middleware objects and does not call `get_engine()` for schema creation. During Uvicorn lifespan startup, `backend/api.py` calls `Base.metadata.create_all(get_engine())` only when `CROP_PULSE_AUTO_CREATE_SCHEMA` is exactly `1`. That setting can create missing tables, but `create_all` does not add missing columns to an existing table and is not a substitute for Alembic. The repository launcher explicitly sets auto-create to `0` for an API child it starts. `/health` opens the configured engine and executes `SELECT 1` (read-only readiness check).

No backend `.env` loading mechanism (`python-dotenv` or `load_dotenv`) was found. `.env.example` is documentation/sample configuration and is not automatically loaded by `backend.db`; in this shell no real root `.env` file was present and `CROP_PULSE_DATABASE_URL` was unset. `frontend/.env.local` is used by Vite for browser-facing settings, not by the FastAPI process's database module. A direct Uvicorn process inherits variables from its launching shell, Windows service, IDE, or wrapper. `run_streamlit.ps1`, when starting a new API child, temporarily sets an explicit default SQLite URL and `CROP_PULSE_AUTO_CREATE_SCHEMA=0`; when port 8001 is already occupied, it reuses the listener instead and cannot reconfigure that process.

The documented current-source launch command, from the project root, is:

```powershell
Set-Location 'C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda'
$env:CROP_PULSE_AUTO_CREATE_SCHEMA = '0'
.\.venv\Scripts\python.exe -m uvicorn backend.api:app --host 127.0.0.1 --port 8001
```

Before running it, the operator must set `CROP_PULSE_DATABASE_URL` in that same PowerShell process to the confirmed intended target and set the required API signing/CORS values there; do not print those values. From that same shell, the effective target can be checked without connecting to it by parsing `backend.db.database_url()` with SQLAlchemy's `make_url` and displaying only the backend and, for SQLite, the resolved file path (never `str(url)`, username, password, query, or the full DSN). This establishes the configuration a newly launched process will inherit; it cannot retrospectively establish PID 16264's configuration. After identifying the target, `/health` performs a read-only `SELECT 1` readiness check, but routes requiring migration `0015` will not be usable until that migration is separately backed up, approved, and applied.

A controlled restart is **not yet safe to perform now** because the listener's target database and environment are unknown. After those are confirmed, an approved backup is verified, and `CROP_PULSE_AUTO_CREATE_SCHEMA=0` is explicitly set, restarting the intended current source can be controlled without auto-creating tables. Before migration `0015`, its alert routes may appear in OpenAPI but database operations that reference the new schema can fail; do not mistake that for a successful feature workflow. Do not migrate or restart until the data owner confirms the target identity/purpose and the backup is recoverable.
