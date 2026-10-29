# CropPulse Rwanda — Gate 1M: Disposable API Test Environment Plan

**Prepared:** 2026-10-26 (Africa/Johannesburg)  
**Project root:** `C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda`  
**Scope:** Source and documentary review; no environment was created and no service or database was started, opened, queried, copied, or modified.

## Executive recommendation

For the narrowly scoped API verification (source identity, health, and OpenAPI routes), use a **new empty SQLite file in an owner-approved, access-restricted disposable workspace**, then launch the API with an explicit absolute SQLite URI using `mode=ro` and `uri=true`. Do not copy or run against the previously documented fixture. An empty database has no application records and does not require migrations for the checks in scope: API startup with `CROP_PULSE_AUTO_CREATE_SCHEMA=0` does not create tables, `/health` runs only `SELECT 1`, and `/openapi.json` is generated from the in-memory route definitions.

This is safer than the fixture copy because the existing fixture's content/integrity are unverified and its current inherited ACL grants `Authenticated Users` Modify. A new empty test DB still needs an explicitly approved path, restrictive ACL verification, source/venv read-only access, process identity checks, and fresh listener checks. No setup or launch is authorized by this plan.

## Verified source and configuration evidence

- `backend.api:app` is the FastAPI application entry point. Use the project virtual environment at `.venv\Scripts\python.exe` and the project root as the working directory so Python imports the intended `backend` package.
- `backend.db.database_url()` reads `CROP_PULSE_DATABASE_URL`; only if absent does it fall back to `sqlite:///./data/croppulse_phase1.sqlite3`. Relative SQLite paths resolve against the process working directory. Therefore a future run must set an absolute explicit URI and assert the SQLAlchemy engine's `PRAGMA database_list` target before issuing requests.
- `backend/migrations/env.py` also reads `CROP_PULSE_DATABASE_URL`, falling back to the same local development database URL. The migration scripts use Alembic operations on the configured connection; source search found no second migration database connection. No migration is needed or authorized for this plan.
- FastAPI lifespan calls `validate_runtime_config()` and calls `Base.metadata.create_all()` only when `CROP_PULSE_AUTO_CREATE_SCHEMA` is exactly `1`. There is no migration or scheduled/background job in the API lifespan. Set it explicitly to `0`; this disables table creation but does **not** disable route writes.
- `backend.db` creates one cached SQLAlchemy engine per URL and enables only `PRAGMA foreign_keys=ON` on SQLite connections. API database sessions use this configured engine. Other database tools (`backend.admin_cli`, import utilities, Alembic) are separate commands and are not invoked by importing/running `backend.api:app`.
- Route review confirms many mutation endpoints call `commit()` or `delete()`. SQLite `mode=ro` is therefore required as a connection-level guard even though only safe GET endpoints will be called. Test the API against a test-only target; any write attempt should fail rather than be persisted.
- `GET /health` opens the configured engine and executes only `SELECT 1`. `GET /openapi.json` is served from the FastAPI route schema and does not access the DB. Do not call `/v1/browser-auth/csrf`, authenticated endpoints, or other routes for this verification.
- `backend.api` has no startup migration, task scheduler, background task, or second SQLite connection. Source imports the weather adapter (whose cache is in memory and which calls the provider only when its forecast function is invoked) and the crop-health model module (which loads model files only when screening is requested). Do not invoke weather or crop-health operations. Run Python with `-B` and `PYTHONDONTWRITEBYTECODE=1` to avoid bytecode writes.
- `run_streamlit.ps1` is not suitable: it can reuse an existing API on port 8001, and it also starts Streamlit. The future isolated API must be launched directly and bound to `127.0.0.1` only.
- SQLite may use a rollback journal and may need `-wal`/`-shm` files depending on the selected DB's journal mode and SQLite behavior. The source does not set a journal mode. Use a new disposable directory so any database or sidecar effects cannot land beside a protected project DB. Do not infer the journal mode of an unopened existing DB.

## Existing fixture decision

The prior Phase 4 report documents `.test-runtime/phase4-recovery-3f5e0732384149d7b6201b3677958bc4/isolated-test.sqlite3` as a synthetic recovery DB with `TEST_ONLY` rows. The latest readiness review resolved it to:

```text
C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda\.test-runtime\phase4-recovery-3f5e0732384149d7b6201b3677958bc4\isolated-test.sqlite3
```

Read-only metadata/ACL inspection found inherited access, including `Authenticated Users: Modify`, on the file and directory. Integrity and current contents were deliberately not checked. **Do not copy this fixture as the default strategy and do not run the API against it.**

### Alternatives

| Approach | Benefits | Risks/limitations | Decision |
|---|---|---|---|
| A. Copy the documented synthetic fixture into a new restricted workspace | Carries an existing schema and test-only rows; can be useful if later tests require persisted application data. | Current source fixture ACL is broad; contents/integrity are unverified in this review; SQLite sidecar consistency must be considered; copy and integrity check are additional authorized operations. | Defer. Only use if a later test needs the fixture's schema or synthetic rows and its owner authorizes copy and validation. Never copy the owner-designated development DB. |
| B. Create a new empty SQLite file in a restricted disposable workspace | No user/test records to preserve; no existing source DB is reused; sufficient for the sole `/health` and OpenAPI checks; SQLite read-only mode limits route-level writes. | Does not verify DB schema/migration compatibility or any persistence workflow. Creation still writes one new test file and must be separately authorized. | **Recommended for this bounded health/routes verification.** No migration or `create_all` is required for these endpoints. |

The API route schemas are registered at import. The health check's `SELECT 1` works on an empty SQLite DB; this conclusion follows from the inspected handler and SQL behavior, not from a runtime test in this task. If a future verification scope includes authenticated data workflows, that is a different test plan requiring a disposable schema and synthetic fixtures.

## Future setup and execution sequence (not executed)

### Preconditions and isolation boundary

Before asking to execute, the owner/operator must approve a concrete disposable workspace path outside all existing database directories and outside the web-served frontend tree. This report intentionally does not invent the path. Confirm the path does not exist or is an empty, explicitly disposable directory; inspect its parent ACL before creating anything. Create it with inheritance disabled and access limited to the test operator and required system administrators. Do not change ACLs on current project or database files.

For strongest isolation, run under an OS identity or Windows Sandbox/VM that can read the project source and venv but can write only to the approved disposable workspace and dedicated scratch/cache directory. The isolated process must have no write access to `data/croppulse_phase1.sqlite3`, other existing database files, or the unknown DB used by PID 21152. If the unknown live DB cannot be identified or access restrictions cannot be demonstrated, do not claim system-wide non-interference and do not launch. Keep the current listeners untouched.

### Proposed command template

These commands are a template only and must not be run without separate authorization, a selected path, and verified ACLs. `$testRoot` is deliberately a placeholder, not an asserted existing path. Use a fresh PowerShell process, set `$root` to the verified project root, and set `$testRoot` only to the approved external disposable workspace.

```powershell
$root = 'C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda'
$python = Join-Path $root '.venv\Scripts\python.exe'
$testRoot = '<OWNER_APPROVED_RESTRICTED_DISPOSABLE_WORKSPACE>'
$testDb = Join-Path $testRoot 'health-routes-only.sqlite3'
$port = 18001

# Before any creation: resolve/validate root and interpreter; inspect target and parent ACL;
# abort if the workspace is not the approved empty disposable directory.
# Capture listener maps for 8001/8501/5173 and require 18001 to be free.
# Verify required imports using this interpreter; do not install missing dependencies here.

$env:PYTHONDONTWRITEBYTECODE = '1'
$env:CROP_PULSE_ENVIRONMENT = 'test'
$env:CROP_PULSE_AUTO_CREATE_SCHEMA = '0'
$env:CROP_PULSE_SECRET_KEY = (& $python -B -c "import secrets; print(secrets.token_urlsafe(48))").Trim()
```

The selected test DB should be created only after approval, from that venv's Python standard library `sqlite3` API at the exact approved path, with no schema or rows. Then immediately close it and configure a SQLite read-only URI for the API. The source and prior Gate 1D run demonstrate SQLAlchemy's compatible URI construction:

```python
from sqlalchemy.engine import URL
readonly_url = URL.create(
    "sqlite+pysqlite",
    database=f"file:{test_db_path.as_posix()}",
    query={"mode": "ro", "uri": "true"},
).render_as_string(hide_password=True)
```

Set `CROP_PULSE_DATABASE_URL` to that URL in the child process only. Before startup, use a read-only SQLite connection and SQLAlchemy `PRAGMA database_list` to confirm the resolved target equals `$testDb`; confirm it does not equal the canonical path for `data/croppulse_phase1.sqlite3` or any inventoried protected DB. Because the DB is empty, do not run migration or `create_all`. Verify startup config explicitly has auto-create `0`, module path is `<root>\backend\api.py`, executable is `<root>\.venv\Scripts\python.exe`, CWD is `$root`, and all required imports are available. Any mismatch aborts before launch.

After all preflight checks pass and separate launch authorization is granted, start only:

```powershell
& $python -B -m uvicorn backend.api:app --host 127.0.0.1 --port 18001 --workers 1
```

Run it in the foreground in the isolated test terminal. Capture the resulting PID and map `127.0.0.1:18001` to that PID using read-only listener inspection; confirm executable, command, and CWD where Windows permits. Do not use `run_streamlit.ps1`, `Start-Process` reuse logic, or a process-name-based kill.

From a separate terminal, send only:

```powershell
Invoke-RestMethod 'http://127.0.0.1:18001/health' -TimeoutSec 5
$schema = Invoke-RestMethod 'http://127.0.0.1:18001/openapi.json' -TimeoutSec 5
$paths = @($schema.paths.PSObject.Properties.Name)
$paths -contains '/v1/weather/alerts'
$paths -contains '/v1/weather/alert-preferences'
```

After checks, stop only the captured foreground test process using Ctrl+C in its own terminal. Confirm port 18001 is free and the captured PIDs for ports 8001, 8501, and 5173 remain unchanged. Compare pre/post path, size, and last-write metadata for each protected database and any existing SQLite sidecars that can safely be inventoried without opening them. Confirm the new test DB remains unmodified by the read-only API and note any new sidecars; preserve and investigate any unexpected change rather than deleting it. If a protected database cannot be identified or its metadata cannot be compared, report that limit and stop.

### Missing facts and abort conditions

- An owner-approved external test workspace path and proof of restrictive ACLs do not exist yet.
- The effective database of the current API on port 8001 remains unknown; OS-level denial of access to that DB cannot be proven until its identity is established. The proposed OS sandbox boundary must therefore block access to existing project databases and the unknown live target, or the test remains blocked.
- The exact project venv dependency inventory was not executed because running Python/import checks was prohibited. In a future authorized setup, import-check dependencies before creating the test DB. Do not install or modify dependencies as part of the test without separate approval.
- This plan proves only readiness for health and route metadata checks. It does not establish schema compatibility, DB persistence, authenticated workflow behavior, or production readiness.

Abort if the approved directory is ambiguous, exists with unrecognized content, ACLs are inherited/broad, required dependencies are missing, a protected DB can be written by the test identity, `CROP_PULSE_DATABASE_URL` is missing or resolves elsewhere, auto-create is not exactly `0`, the imported source/venv/CWD mismatch, port 18001 is occupied, an existing listener PID changes, a required endpoint behaves unexpectedly, or protected/test DB metadata changes. Do not repair by deleting files, changing permissions, substituting the dev DB, or killing an unidentified process.

## Future authorization boundary and single next action

This plan authorizes no directory creation, ACL change, database creation/copy, integrity check, test, API startup, or process shutdown. The single next action is for the owner to approve a specific restricted disposable workspace and OS isolation boundary for creating an empty health/routes-only SQLite file; setup and launch approvals should remain separate. If the owner instead requires persistence/schema tests, prepare a distinct plan for a synthetic migration-created DB and synthetic records.

No runtime, filesystem permission, source, configuration, or database changes were made for this report.

**Verdict: DISPOSABLE TEST SETUP PLAN READY — OWNER AUTHORIZATION REQUIRED**
