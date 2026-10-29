# CropPulse Rwanda — Isolated Runtime Verification Readiness

**Review date:** 2026-10-26 (Africa/Johannesburg)  
**Project root:** `C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda`  
**Scope:** Read-only review of the Gate 1L plan, project source, launcher configuration, and existing fixture documentation. No service was launched or contacted; no database was opened, queried, copied, or changed.

## Decision

The project source supports a separate FastAPI process on `127.0.0.1:18001`, and the prior Phase 4 report documents a synthetic test database that was previously used by an isolated API run with SQLite `mode=ro`. The owner-designated development database is a different file and must be excluded explicitly.

The test fixture's restrictive ACL is not verified. Also, `CROP_PULSE_AUTO_CREATE_SCHEMA=0` prevents schema creation, but it does not make the entire API read-only: registered authenticated and unauthenticated routes can still attempt writes. A read-only SQLite URI should cause those writes to fail, but local clients can still reach the loopback listener. Until the fixture's current path/ACL and local access conditions are verified before execution, this review does not authorize or recommend starting the service.

## Verified source and configuration facts

- FastAPI entry point is `backend.api:app`, imported from the project root. The intended interpreter is `.venv\Scripts\python.exe`.
- `backend.db.database_url()` reads `CROP_PULSE_DATABASE_URL`; absent that value it uses the relative default `sqlite:///./data/croppulse_phase1.sqlite3`, resolved against the process working directory.
- The API does not load `.env` itself in the inspected startup path. Set the environment in the launch PowerShell process.
- API lifespan validates `CROP_PULSE_ENVIRONMENT` and `CROP_PULSE_SECRET_KEY`. It calls `Base.metadata.create_all()` only when `CROP_PULSE_AUTO_CREATE_SCHEMA` is exactly `1`; it has no Alembic migration call. Setting it to `0` disables schema creation but does not disable writes from API routes.
- The prior isolated launch report records a stronger read-only setup using a SQLAlchemy SQLite URI with `mode=ro` and `uri=true`. It verified source, database path, revision, integrity, health, and routes, then stopped the test process. That is historical evidence for that run, not proof of the fixture's current ACL or current byte-level state.
- The prior Phase 4 report designates `.test-runtime/phase4-recovery-3f5e0732384149d7b6201b3677958bc4/isolated-test.sqlite3` as a fresh disposable database, migrated to `0015_weather_alert_foundation`, containing only `TEST_ONLY` synthetic records. Its backup and restore copies are separate synthetic artifacts. The same report explicitly says restrictive ACL verification failed and was not claimed.
- `run_streamlit.ps1` is unsuitable for this test: it can reuse an existing API on port 8001 and also starts Streamlit. Use direct Uvicorn startup only in a separately authorized run.
- The owner-designated development DB is `data/croppulse_phase1.sqlite3`; it is not the test fixture. Never use it for this isolated test.

## Fixture identity and current-state limits

Documented fixture path, relative to the project root:

```text
.test-runtime/phase4-recovery-3f5e0732384149d7b6201b3677958bc4/isolated-test.sqlite3
```

The test-only role is supported by the Phase 4 recovery report and Gate 1D preflight/results, not inferred from the filename. This review did not open or inspect the DB. Current integrity, revision, ACL, and metadata were not verified here and must be checked again immediately before any future run using read-only methods. There is no dedicated signed manifest for this DB.

One read-only `Test-Path` existence check was made against the documented file path during review; it read filesystem metadata only. No DB contents or bytes were accessed. The earlier Gate 1L plan also records this metadata-only check. No test DB metadata change was made by this review.

## Required fail-closed preflight for a future authorized run

Do not execute this sequence as part of this review. A future operator must use a fresh PowerShell window and abort before startup if any assertion fails:

1. Resolve and assert the project root, `.venv\Scripts\python.exe`, and the exact documented fixture path. Require the resolved test path to differ from the resolved `data\croppulse_phase1.sqlite3` path. Require the fixture to exist, be a regular non-empty file, and have a documented test-only provenance. Do not create or substitute a file.
2. Recheck ports `8001`, `8501`, `5173`, and `18001` with read-only listener inspection. Require 18001 to have no listener. Record current PIDs for 8001/8501/5173 and compare them after cleanup.
3. Verify all required Python modules (`fastapi`, `uvicorn`, `sqlalchemy`, and project imports) exist in the project venv before server startup. Abort if any import fails.
4. Verify the fixture ACL using read-only Windows ACL inspection. Because the API remains write-capable at the route layer, require a controlled local session where untrusted local processes cannot access the loopback listener or test file. If this cannot be established, do not launch.
5. Use `CROP_PULSE_ENVIRONMENT=test`, a fresh ephemeral `CROP_PULSE_SECRET_KEY` held only in the process environment, `CROP_PULSE_AUTO_CREATE_SCHEMA=0`, and an explicit absolute SQLite URI for the fixture with `mode=ro` and `uri=true`. Do not set or use the development DB fallback. Assert the resolved configured URL and SQLAlchemy `PRAGMA database_list` target are the exact fixture path before starting Uvicorn.
6. With a read-only SQLite connection, require `PRAGMA integrity_check` to return `ok`, the Alembic revision to equal the source migration head, and `PRAGMA foreign_key_check` to return no rows. Any missing table, mismatch, inaccessible file, unexpected sidecar, or ambiguity is an abort. No migrations or schema creation are permitted.
7. Assert the imported module is exactly `<project-root>\backend\api.py`, `sys.executable` is exactly the project venv Python, and the working directory is exactly the project root. Require `CROP_PULSE_AUTO_CREATE_SCHEMA` to equal `0` before the app lifespan starts.
8. Start only the intended process, foreground, with one worker and host `127.0.0.1`, port `18001`. Do not use `run_streamlit.ps1`; do not bind `0.0.0.0`; do not stop or reuse any existing listener.

The prior Gate 1D result contains a concrete PowerShell/Python sequence for the preflight and launch. It uses a read-only SQLite URI and abort assertions. Treat it as a template only: update no paths by guesswork, and re-run all checks immediately before any separately authorized execution.

## Future process and cleanup verification

- Capture the test PID from the foreground test process and independently map the listener on `127.0.0.1:18001` to that PID. Confirm its executable, command, and CWD against the expected project venv/root where Windows permits. If identity cannot be established, stop checks and do not send requests.
- Make only `GET /health` and `GET /openapi.json` to the isolated port. Confirm the health result and expected paths, including `/v1/weather/alerts` and `/v1/weather/alert-preferences`. Do not authenticate, open the UI against it, or call any write-capable endpoint.
- Stop only the captured foreground test process with Ctrl+C in its own terminal. Do not use a broad process-name kill. Confirm port 18001 is unbound afterward.
- Recheck listeners and require ports 8001, 8501, and 5173 to still map to their pre-run PIDs. A mismatch is an abort/investigation condition; do not attempt to “fix” it by stopping a process.
- Compare pre/post filesystem metadata for the fixture and any pre-existing `-wal`, `-shm`, and `-journal` sidecars: path, existence, size, and last-write timestamp. Unexpected change or new sidecars means preserve the artifacts and investigate; do not delete them. Read-only SQLite mode should prevent DB writes, but this comparison is still required.

## Explicit abort conditions

Abort before launch if the port is occupied; any original listener identity differs from the captured state; the venv, source path, fixture path, dependency, ACL, or local isolation is uncertain; the DB path equals the development DB; the URI is not read-only; auto-create is not explicitly `0`; revision/integrity/source-head checks fail; a sidecar or metadata baseline is ambiguous; or any configuration value would fall back to the default DB. Abort during the test if the listener maps to an unexpected PID, required routes are absent, or any database metadata changes.

## Checks performed and limitations

- Inspected `docs/release-gate-1l-controlled-runtime-transition-plan.md`, Gate 1D preflight/results, Phase 4 readiness evidence, `backend/api.py`, `backend/db.py`, `run_streamlit.ps1`, and related launch references.
- Read-only listener inspection observed `127.0.0.1:8001` PID 21152, `0.0.0.0:8501` PID 24140, and `127.0.0.1:5173` PID 11512; no listener was observed on port 18001 at inspection time. Listener state can change and must be rechecked immediately before a future run.
- The metadata-only fixture existence check is disclosed above. No API endpoint was contacted, no database contents were opened/read, no tests or migrations were run, and no service was launched, stopped, or signaled.
- Source inspection cannot prove the fixture's present integrity, ACL, loaded runtime identity, or absence of another local client. Those checks require fresh, read-only runtime/OS evidence before an authorized run.

## Changes

This document records a readiness review only. No source, configuration, environment, service, or database was changed.

**Initial review status:** blocked pending fixture ACL and isolation evidence. The findings below supersede that initial status.

## Addendum — Isolated test safety review (2026-10-26)

### Fixture provenance, resolved path, and access controls

The Phase 4 readiness report identifies this fixture as a fresh disposable SQLite DB migrated to `0015_weather_alert_foundation` and seeded only with `TEST_ONLY` synthetic farmer/farm rows. Gate 1D preflight/results describe the same path as the approved isolated test target. This documentary chain establishes the fixture's intended purpose as synthetic and disposable. It does not independently establish what bytes are in the current file; this review did not open it and did not verify its integrity.

The exact resolved path from a read-only filesystem metadata lookup is:

```text
C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda\.test-runtime\phase4-recovery-3f5e0732384149d7b6201b3677958bc4\isolated-test.sqlite3
```

Metadata observed: 475,136 bytes, `Archive` attribute, last-write UTC `2026-10-26 06:49:24`. The containing directory has the same owner as the file and inherits access rules. The file and directory ACLs both include `NT AUTHORITY\Authenticated Users: Modify`; `BUILTIN\Users` has read/execute on the file and directory. Other inherited Modify entries were present. Thus the fixture and its directory are not restricted to the project owner. No ACL changes were made. A read-only listing found no `isolated-test.sqlite3-wal`, `-shm`, or `-journal` sidecar at inspection time; this is only a point-in-time filename/metadata observation.

**Finding:** documentary provenance supports “synthetic test fixture,” but current content/integrity is unverified. Current access controls do not establish isolation from other authenticated local users/processes. Do not run the application against this original fixture.

### Database writes, other files, and startup behavior

- `backend.db.database_url()` selects one SQLAlchemy URL from `CROP_PULSE_DATABASE_URL`, falling back to the relative development DB only if that variable is absent. Relative SQLite paths resolve from process CWD. SQLAlchemy engine creation is lazy. The inspected application persistence uses this engine/session; migrations are separate Alembic commands and are not invoked by API startup.
- FastAPI lifespan validates environment/secret configuration. It calls `Base.metadata.create_all()` only when `CROP_PULSE_AUTO_CREATE_SCHEMA` is exactly `1`; it does not run migrations. Setting it explicitly to `0` prevents that startup schema-creation path, but does not prevent route-level writes.
- Route inspection found numerous commits and mutations across registration/login throttling, handoffs, weather records/preferences/status, messaging, reviewer/admin actions, farms/plans, and crop-health reports. Therefore “GET only” is not a sufficient write boundary by itself. The health route performs only `SELECT 1` on the configured engine. `/openapi.json` is generated from the route schema and does not access the database. Do not call other endpoints for this test.
- The engine can be configured with SQLite URI `mode=ro` and `uri=true`, as used in the prior isolated-run report. This prevents SQLite write transactions through that connection and should make route commits fail rather than persist. It is a defense in depth, not a complete host security boundary. Use it against a disposable copy, never the original fixture. Verify the engine's `PRAGMA database_list` resolves to that copy before serving any request.
- Source search found no API startup migration, scheduled task, background task, or second `sqlite3.connect`/SQLAlchemy engine path. The weather adapter has an in-memory cache and makes external requests only when called. Crop-health image data is stored in the configured DB; model loading/inference is request-triggered. Avoid those routes. Run Python with bytecode writing disabled (`-B` / `PYTHONDONTWRITEBYTECODE=1`) and direct any runtime scratch/cache output to a designated disposable location if a later environment requires it. Import/startup behavior was established by source inspection only; this task did not import or start the application.
- With a checked explicit URL, the application source inspected here has no normal route path that opens the development DB in parallel. However, source inspection cannot prove that a future process environment is immutable or identify the unknown database used by the existing API. Process identity and the active PID 21152 target remain outside this test's scope.
- The requested “unrelated project data” protection is not currently established: the project tree is writable to authenticated users, and TensorFlow or other imported dependencies may have their own runtime cache behavior not exercised here. A later test must run with the source tree read-only and a controlled disposable scratch/cache location, or in an equivalent isolated OS environment. No source files or caches were written by this review.

### Minimum safe future test setup (separate authorization required)

1. Do not use the original documented fixture or `data/croppulse_phase1.sqlite3`. In a separately authorized setup task, make a byte-for-byte disposable copy of the documented synthetic fixture at a newly approved test-only destination. Do not invent or create that destination during this review. Record source and copy paths, sizes, timestamps, and SHA-256 before/after the copy; verify the source metadata/hash remains unchanged. Then run the approved integrity/revision/FK checks against the copy only. If any check fails or the copy's provenance is ambiguous, discard no artifacts and stop for owner review.
2. Establish OS isolation before launch. The test identity must have read/execute access to the intended project source and venv, access only to the disposable DB copy and scratch/cache directory for writes, and no write access to `data/croppulse_phase1.sqlite3` or any identified existing development/live DB. Because the live API database is unknown and this project’s current ACLs are broad, if the operator cannot prove that protected databases and unrelated project files are not writable by the test identity, use an isolated Windows VM/Sandbox with only the approved source mounted read-only and the disposable DB copy supplied separately. Do not weaken or change any current ACL as part of this review.
3. In a fresh process, assert exact venv executable, project source module path, working directory, and explicit absolute SQLite URI. Set `CROP_PULSE_AUTO_CREATE_SCHEMA=0`; set the SQLite URL to the disposable copy with `mode=ro` and `uri=true`. Fail closed if the variable is missing, the URI is not read-only, the resolved engine database path differs, or it resolves to the development DB. Do not run Alembic or any schema creation.
4. Before launch, capture listener PID mappings for 8001, 8501, 5173, and 18001. Require 18001 free. Verify required venv dependencies by import-only checks, then verify copied DB integrity/revision via a separate read-only connection. Any error aborts before Uvicorn.
5. Launch the project API only on `127.0.0.1:18001`, one worker, in the controlled environment. Capture the PID and verify its executable, source path, CWD, command, and listener ownership. Request only `GET /health` (confirmed `SELECT 1`) and `GET /openapi.json` (route metadata only). Do not browse the UI, authenticate, or call other routes.
6. Stop only the captured foreground process using Ctrl+C in its launch terminal. Confirm 18001 is closed and original listeners still map to their pre-test PIDs. Compare pre/post metadata and hashes for the disposable DB copy and its SQLite sidecars; also confirm the protected development DB metadata and any identified live DB metadata are unchanged. If their identities cannot be identified or monitored, that is a stop condition rather than an assumption.
7. If any test DB write is attempted, SQLite read-only should reject it. Treat any new/changed sidecar or DB metadata as a failed containment check: preserve artifacts and investigate; do not delete or “clean up” automatically.

The copy creation, copy validation, ACL/OS isolation setup, database integrity check, and service launch are not authorized by this review. They require a separate bounded approval. The current fixture ACL is an observed reason to keep this task blocked, not a reason to change permissions now.

### Bounded next action

The single next action is to request separate owner authorization for a **disposable synthetic database setup only**: choose and approve a restricted test destination/OS boundary, create a disposable copy of this documented fixture, and verify that copy's provenance, integrity, revision, ACL, and unchanged source metadata. Do not launch the API in that setup task. A later launch requires its own approval after the copy and isolation evidence passes.

No API was contacted, no database was opened or queried, no test/migration/startup command was run, no service was started/stopped/restarted/signaled, no file contents were modified, and no permissions were changed. This review did perform read-only path resolution, file/directory metadata and ACL inspection, a sidecar-name listing, and source/document inspection.

**Verdict: BLOCKED — TEST DATABASE ISOLATION NOT ESTABLISHED**
