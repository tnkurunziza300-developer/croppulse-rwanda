# CropPulse Rwanda — Gate 1L: Controlled Runtime Transition and Recovery Plan

**Prepared:** 2026-10-26 (Africa/Johannesburg)  
**Project root:** `C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda`  
**Scope:** Source/document inspection and a proposed isolated local verification / later maintenance procedure. No transition was performed.

## 1. Executive decision

The project supports a separate, loopback-only FastAPI process from its project virtual environment, with an explicit SQLite URL and schema auto-creation disabled. The prior Phase 4 report documents an existing synthetic test database at migration `0015`; a read-only preflight can reject it if the file, path, integrity, or revision does not match.

This option can verify the current project-managed code in isolation. It cannot identify which source or database the existing PID 21152 uses. The currently observed Python executable is the global Python installation, not `.venv\Scripts\python.exe`; its imported source, working directory, and effective database remain unknown. The current API and database must remain untouched until separate authorization and safeguards are in place.

**Verdict: PLAN READY FOR OWNER REVIEW — NO RUNTIME CHANGES AUTHORIZED**

This is not a release-readiness or production-readiness verdict. The plan has an explicit stop if the documented synthetic database cannot be safely verified at execution time.

## 2. Verified launch architecture

### Project launch path

- Backend entry point: `backend.api:app` (FastAPI title `CropPulse Rwanda Farmer Records API`, version `1.0.0`). The documented virtual environment is `.venv\Scripts\python.exe`.
- `run_streamlit.ps1` uses `$PSScriptRoot` as project root. If port 8001 is free, it starts `backend.api:app` at `127.0.0.1:8001` from that root and sets local database/security environment values. If a listener already occupies 8001 and passes its health/route checks, the launcher **reuses it**; it cannot establish that listener's source, CWD, environment, or database. It also launches Streamlit on 8501, so this launcher is not appropriate for an isolated API-only check.
- `backend.db.database_url()` reads `CROP_PULSE_DATABASE_URL`, else returns `sqlite:///./data/croppulse_phase1.sqlite3`. The relative SQLite path resolves from the process working directory. Engine creation is lazy.
- API startup validates `CROP_PULSE_ENVIRONMENT` and `CROP_PULSE_SECRET_KEY`. In the lifespan, `Base.metadata.create_all()` runs only if `CROP_PULSE_AUTO_CREATE_SCHEMA` is exactly `1`; with it set to `0`, startup does not create schema. Startup does not run Alembic migrations. `/health` executes `SELECT 1`; `/openapi.json` reports route metadata.
- There is no `.env` auto-loading in the inspected DB/API path; the API receives its settings from the process environment. The intended explicit URL must be set in the same PowerShell process before launching Python.
- React reads `VITE_API_BASE_URL` at build time from `frontend/src/api.ts`, falling back to `http://127.0.0.1:8001`. Streamlit reads `CROP_PULSE_API_URL`. Neither UI setting identifies the API's database. Production requires an approved HTTPS API/proxy origin at build/runtime; no public URL is supplied here.

### Current listener observations

Read-only `netstat -ano -p tcp` showed at inspection time:

| Port | Listener | PID | Relevance |
|---:|---|---:|---|
| 8001 | `127.0.0.1` | 21152 | Existing API to preserve. |
| 8501 | `0.0.0.0` | 24140 | Existing Streamlit to preserve; all-IPv4 binding is a separate security concern. |
| 5173 | `127.0.0.1` | 11512 | Existing Vite dev server to preserve. |
| 18001 | No listener observed | — | Candidate isolated test port only; recheck immediately before any separately authorized launch. |

For PID 21152, `Get-Process` returned `C:\Users\Student\AppData\Local\Programs\Python\Python312\python.exe` and start time `2026-10-26 10:31:09` local time. This establishes the executable image path, not the imported module or process environment. `tasklist /v`, CIM process/service inspection, and scheduled-task enumeration were inaccessible; command line, parent/owner, CWD, service/task association, and environment remain unknown.

Earlier, the API health check returned `ok`, and its OpenAPI schema reported 62 paths including the two weather-alert routes. Those requests were not repeated during this task. Neither health nor route parity proves source or database identity.

## 3. Existing runtime and data uncertainties

- The owner-designated `data/croppulse_phase1.sqlite3` is for local development. It must not be used for this isolated API test.
- PID 21152 may use another source tree or another SQLite/PostgreSQL target. No direct evidence establishes its active DB.
- The owner reports project records are synthetic/sample/test data, but the currently running process target is unknown. Therefore the data reachable by PID 21152 cannot be classified from that statement alone. Preserve all candidate files and treat an unidentified DB as containing data worth preserving until the service/data owner establishes otherwise.
- The known Phase 4 artifact is `.test-runtime/phase4-recovery-3f5e0732384149d7b6201b3677958bc4/isolated-test.sqlite3`, documented as a synthetic recovery-test DB at revision `0015_weather_alert_foundation`. Its ACL was not verified as restrictive. It is a test-only candidate, never a replacement for the owner-designated development DB or any live DB.

## 4. Proposed isolated verification (not executed)

Purpose: establish that the current project source and venv can serve health/OpenAPI on an unused loopback port when explicitly configured to the existing synthetic test database. This does **not** verify or replace the listener on port 8001.

Use a fresh PowerShell session from the project root, and only after separate owner approval to launch this isolated process. Do not run `run_streamlit.ps1`. The following commands are a proposed sequence; none was executed:

```powershell
$root = 'C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda'
$python = Join-Path $root '.venv\Scripts\python.exe'
$testDb = Join-Path $root '.test-runtime\phase4-recovery-3f5e0732384149d7b6201b3677958bc4\isolated-test.sqlite3'
$port = 18001

if (-not (Test-Path -LiteralPath $python)) { throw 'Project venv missing; abort.' }
if (-not (Test-Path -LiteralPath $testDb)) { throw 'Previously documented synthetic DB missing; do not create or substitute one.' }
if (Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue) { throw 'Test port occupied; abort.' }

$env:CROP_PULSE_ENVIRONMENT = 'development'
$env:CROP_PULSE_SECRET_KEY = (& $python -B -c "import secrets; print(secrets.token_urlsafe(48))").Trim()
$env:CROP_PULSE_DATABASE_URL = 'sqlite:///' + $testDb.Replace('\','/')
$env:CROP_PULSE_AUTO_CREATE_SCHEMA = '0'
Push-Location $root
```

Run this preflight **before Uvicorn**. It imports the app but does not enter FastAPI lifespan. The explicit path must match the already-existing synthetic file; failures abort without starting a service.

```powershell
$preflight = @'
import os, sqlite3, sys
from pathlib import Path
from sqlalchemy.engine import make_url
import backend.api
from backend.db import database_url, get_engine

root = Path.cwd().resolve()
expected = Path(sys.argv[1]).resolve(strict=True)
assert Path(sys.executable).resolve() == (root / '.venv' / 'Scripts' / 'python.exe').resolve()
assert Path(backend.api.__file__).resolve() == (root / 'backend' / 'api.py').resolve()
url = make_url(database_url())
assert url.get_backend_name() == 'sqlite'
assert Path(url.database).resolve(strict=True) == expected
assert os.environ.get('CROP_PULSE_AUTO_CREATE_SCHEMA') == '0'

ro = sqlite3.connect(expected.as_uri() + '?mode=ro', uri=True)
try:
    integrity = ro.execute('PRAGMA integrity_check').fetchone()[0]
    revision = ro.execute('SELECT version_num FROM alembic_version').fetchone()[0]
    assert integrity == 'ok' and revision == '0015_weather_alert_foundation'
finally:
    ro.close()

with get_engine().connect() as connection:
    main_file = next(row[2] for row in connection.exec_driver_sql('PRAGMA database_list') if row[1] == 'main')
    assert Path(main_file).resolve() == expected
    assert connection.exec_driver_sql('SELECT version_num FROM alembic_version').scalar_one() == revision

print('Python:', Path(sys.executable).resolve())
print('Working directory:', root)
print('API module:', Path(backend.api.__file__).resolve())
print('Database target:', expected)
print('Revision:', revision, '| integrity:', integrity)
'@
& $python -B -c $preflight $testDb
if ($LASTEXITCODE -ne 0) { Pop-Location; throw 'Identity/schema/integrity preflight failed; do not launch.' }
```

If preflight succeeds, the future approved test launch would be foreground in that same PowerShell session:

```powershell
& $python -B -m uvicorn backend.api:app --host 127.0.0.1 --port 18001 --workers 1
```

From another terminal, make only these read-only GET checks and verify their results; do not sign in or call write-capable endpoints:

```powershell
$health = Invoke-RestMethod 'http://127.0.0.1:18001/health' -TimeoutSec 5
$schema = Invoke-RestMethod 'http://127.0.0.1:18001/openapi.json' -TimeoutSec 5
$paths = @($schema.paths.PSObject.Properties.Name)
$health.status
$schema.info.title
$paths -contains '/v1/weather/alerts'
$paths -contains '/v1/weather/alert-preferences'
Get-NetTCPConnection -State Listen -LocalPort 18001
```

Capture the PID owning 18001 and confirm it is the new test process before cleanup. Stop it only by pressing **Ctrl+C in the original foreground terminal**. Confirm 18001 has no listener afterward and that ports 8001/8501/5173 still map to their captured original PIDs. Close the disposable PowerShell session to discard its temporary secret/environment values. If the test DB is inaccessible, wrong revision, invalid, or the path does not match, abort; do not create a DB, migrate, or substitute the owner-designated development DB.

**Safety limit:** the synthetic DB's ACL was not verified, and the API engine itself is not configured read-only. The proposed preflight performs only integrity/metadata SELECT/PRAGMA operations; the API checks are restricted to health (`SELECT 1`) and OpenAPI. Do not allow browser traffic, authentication attempts, or other clients to reach this test instance. If that limitation is unacceptable, do not launch until an approved isolated synthetic DB with verified ACL and read-only test configuration exists.

## 5. Backup and restore prerequisites before any transition on port 8001

An isolated API test does not require nor authorize copying the existing DB. Before replacing PID 21152 or migrating any DB:

1. Obtain authorized, sanitized runtime evidence for PID 21152: source, executable/venv, CWD, launch supervisor/configuration, environment source, and effective database backend/target. Do not guess from the fallback URL.
2. Determine with the data owner whether that exact target contains unique records worth preserving. Because it is currently unidentified, treat it as potentially valuable. Do not inspect private rows; use owner-approved non-sensitive inventory/aggregate checks only after identity and access approval.
3. For every identified DB that could contain records to preserve, create a consistent, access-controlled encrypted backup outside the project/web root under separate authorization. For SQLite, quiesce writers or use SQLite's supported online backup method; account for WAL/journal files. Record checksum, access controls, retention, and custody.
4. Restore that backup to a different isolated location and verify integrity, foreign-key constraints, schema revision, and owner-approved non-sensitive invariants. The synthetic Phase 4 restore does not satisfy this requirement.
5. Document and rehearse rollback of the old service command/configuration without overwriting the database. Obtain explicit maintenance approval and a write-freeze/one-writer plan. No migration is included in the transition unless separately proposed and approved.

## 6. Transition, rollback, and stop conditions

No actual replacement command is approved by this planning task because PID 21152's owner/supervisor and target DB are unknown. After separate owner authorization and completion of Section 5, an operator may plan a maintenance window to:

1. Capture listener/PID and service ownership for 8001, 8501, and 5173; confirm which clients depend on the API. Agree downtime and freeze writes.
2. Preserve the old service definition, secure configuration reference, launch command, and verified DB backup/restore evidence. Ensure only one process can write to a SQLite DB.
3. Gracefully stop only the verified API service under its actual supervisor; do not stop Streamlit or Vite without separate approval. Confirm 8001 is released.
4. Start the intended project `.venv` API from the verified project root with an explicit owner-approved DB URL and `CROP_PULSE_AUTO_CREATE_SCHEMA=0`. Verify executable, CWD, module, engine database list/path, schema revision, health and OpenAPI before routing traffic or permitting writes.
5. If any identity, revision, route, or health check differs, keep traffic off and stop only the replacement process. Restore the preserved prior service definition; do not restore/overwrite a database as a code rollback. If any write may have occurred, freeze traffic and reconcile with the data owner before switching back.

**Stop immediately** if process ownership, active target, whether data must be preserved, backup/restore, rollback, one-writer control, target schema, or operator authority is unclear. Do not choose another database by filename, revision, integrity, or timestamp. If preflight or listener checks fail, leave existing processes untouched and report the exact failure.

## 7. Production blockers versus later improvements

These findings are based on `docs/final-development-day-release-report.md`, `docs/react-deployment-checklist.md`, and `docs/phase-5-controlled-browser-qa-operational-readiness.md`. They are not re-tested by this planning task.

### Release blockers before real farmer use or production

- **Deployment/API origin:** no production host/domain is identified. Configure `VITE_API_BASE_URL` at React build time and `CROP_PULSE_API_URL` for Streamlit to an approved API origin; do not use loopback for remote clients.
- **Hosted security:** verify HTTPS/TLS, trusted reverse-proxy behavior, secure cookies, exact credentialed CORS origins, secret-manager use, firewall/allowed-host boundaries, and gateway rate/concurrency limits. Source has application authentication/authorization, CSRF, and body-size controls, but hosted behavior is not verified.
- **Database reliability:** identify/provision the intended managed production DB, ensure persistence and a reviewed migration plan, and prove protected encrypted backups, access restrictions, retention, restore, RPO/RTO, and rollback. The local SQLite candidate and synthetic restore are insufficient.
- **Privacy/data protection:** approve lawful basis/consent, data residency, retention, export/deletion, support, incident handling, and safe logs for identity/contact data, farms/coordinates, messages, and crop-health photos.
- **Rights and attribution:** settle reuse/commercial terms and attribution for NISR and METEO RWANDA materials, Open-Meteo plan/terms, and crop-image/model dataset/weights before public service.
- **Workflow verification:** complete authenticated browser testing on isolated data for registration/login/logout, session/CSRF, ownership/cross-user denial, farms/plans, weather/alerts, messaging, reviewer/admin authorization, and React/Streamlit handoff. No such complete browser evidence is established here.
- **Operations and agricultural safety:** configure non-sensitive logging, monitoring, incident response, recovery ownership, dependency/security updates, and review provisional agronomic outputs/qualifications. Do not present experimental image screening as a confirmed diagnosis or treatment.

### Improvements that can be prioritized after blockers

Accessibility/local-language review, low-bandwidth/mobile optimization, broader offline support, refined operational dashboards, and additional product features are valuable follow-on work. They must not be used to defer the security, privacy, database recovery, rights, and core authenticated workflow blockers above.

## 8. Checks performed and changes

- Read `docs/release-gate-1f-live-api-identity.md`, `docs/release-gate-1g-maintenance-plan.md`, `docs/release-gate-1h-database-provenance.md`, `docs/release-gate-1i-source-of-truth-decision.md`, `docs/release-gate-1j-development-data-and-runtime-identification.md`, `backend/api.py`, `backend/db.py`, `backend/client.py`, `frontend/src/api.ts`, `frontend/vite.config.ts`, `.env.example`, `run_streamlit.ps1`, setup/deployment docs, and Phase 4 recovery notes.
- Read-only `netstat` observed listeners 8001/PID 21152, 8501/PID 24140, 5173/PID 11512; no listener on 18001 at the check time. Process access limitations are documented above. No API HTTP call was made.
- One `Test-Path` existence check read filesystem metadata for the previously documented synthetic DB path; no SQLite file was opened and no database bytes/records were read. This did not modify the file. No other database check was performed.
- No tests were run. No service was launched, stopped, signaled, or restarted. No source/configuration/dependency/environment setting or database was changed. No backup, restore, migration, or deployment was performed.

## 9. Exact next action requiring owner authorization

The project owner should review and explicitly authorize **only the proposed isolated API verification in Section 4**, or decline it. Before execution, the operator must recheck port 18001 and the existing listener map, verify the documented synthetic DB path and read-only preflight results, and abort on any mismatch. This authorization would not authorize stopping/restarting PID 21152, touching the owner-designated development DB, creating/copying a DB, migrating, deploying, or transitioning port 8001. Any replacement needs a separate maintenance approval after the live source/database and backup/restore are proven.
