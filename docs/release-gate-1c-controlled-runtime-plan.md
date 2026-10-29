# CropPulse Rwanda — Gate 1C: Controlled Runtime Identification Plan

**Audit date:** 2026-10-26 (Africa/Johannesburg)  
**Project directory:** `C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda`  
**Scope:** Read-only comparison of Gate 1 and Gate 1B evidence, current launcher/source configuration, and frontend build configuration. This document proposes a future identification procedure; it does not execute it.

**Verdict:** **BLOCKED — PLAN ONLY; EXECUTION NOT AUTHORIZED**

## Confirmed facts and unresolved uncertainties

The preceding reports, [Gate 1](release-gate-1-runtime-database-identity.md) and [Gate 1B](release-gate-1b-runtime-resolution.md), agree on the following observations:

| Item | Confirmed observation | Still unverified |
|---|---|---|
| API listener | `127.0.0.1:8001`, PID 21152, global Python 3.12 executable at `C:\Users\Student\AppData\Local\Programs\Python\Python312\python.exe` | Parent, raw launch arguments, working directory, environment, imported module path and effective DB target |
| Streamlit listener | `0.0.0.0:8501`, PID 24140, same global Python executable | Parent, launch arguments, working directory, environment and relationship to the API |
| Vite listener | `127.0.0.1:5173`, PID 11512, Node executable at `C:\Users\Student\AppData\Local\nodejs\node.exe` | Parent, launch arguments and working directory |
| Port 8000 | No listener was observed in the checks recorded by the earlier reports | Current later state was not asserted by those reports |
| API HTTP behavior | Health and OpenAPI responded; observed OpenAPI title/version were `CropPulse Rwanda Farmer Records API` / `1.0.0`, with 62 paths and the four weather-alert paths | Which source tree and runtime produced this schema |
| Candidate database | Project candidate `data/croppulse_phase1.sqlite3` was checked read-only; 19,402,752 bytes, revision `0015_weather_alert_foundation`, SQLite integrity `ok`, zero FK violations | Whether the running API opens this file; it remains a candidate only |
| Frontend | Local configuration and existing `frontend/dist` bundle contained `http://127.0.0.1:8001` | Approved production API origin and production deployment artifact |

The reports document failed or unavailable standard Windows process metadata queries (`Get-CimInstance`, WMI and WMIC did not provide the requested process details). Process Explorer and Handle were unavailable. Consequently no evidence currently proves that PID 21152 loaded this repository's `backend.api`, used its `.venv`, started in the project root, or reads the candidate database.

The four alert paths were absent in a previously reported live schema and present in later observations and in current source. The source defines the alert routes unconditionally and includes their router; no conditional route registration was identified in the inspected configuration. The change in observation is consistent with a different process or runtime over time, but it does not distinguish that from another source tree, application instance, or configuration. The cause remains **unresolved**.

## Read-only inspection results

### Launcher and process reuse

`run_streamlit.ps1` is the local launcher inspected in Gate 1B. When it finds a listener on the API port it checks health, CSRF/CORS behavior and a subset of authentication, farm and handoff paths, then reuses that listener. Its checks do not establish the listener PID's source path, Python executable, parent, current directory or database target, and do not test the full weather-alert route set. Therefore a healthy response and passing launcher route checks can come from an unrelated API process. A route response proves interface behavior at that address, not process identity.

When it starts its own API, the script uses the project root and `.venv` Python and sets a local relative SQLite URL with auto-create disabled. That documented launch branch is safer than reuse for a future controlled start, but the currently running service was not proven to have been started by that branch. No command in this task starts it.

### Database selection in source

The inspected `backend/db.py` and `backend/migrations/env.py` select `CROP_PULSE_DATABASE_URL` when set, otherwise use `sqlite:///./data/croppulse_phase1.sqlite3`. A relative SQLite path resolves against the process working directory. Static source and a candidate-file integrity check do not reveal the environment or working directory of PID 21152 and cannot establish its effective path.

`backend/api.py` conditionally calls schema creation only when `CROP_PULSE_AUTO_CREATE_SCHEMA=1`; production/staging settings reject that mode. The proposed controlled start below explicitly requires auto-create off and does not run migrations. This is a source-level finding, not evidence about the live process's environment.

### Frontend build configuration

`frontend/src/api.ts` reads `import.meta.env.VITE_API_BASE_URL`, falling back to `http://127.0.0.1:8001`. The local `.env` files and example use loopback; no `.env.production` or `.env.production.local` was found in the prior inspection. Vite substitutes `VITE_*` values at **build time**. The existing bundle therefore embeds the local fallback and is not a production bundle for an unknown remote host.

For a future deployment, an authorized operator must obtain the actual HTTPS API origin from the deployment owner and provide it at build time through the project's Vite environment mechanism (for example, a protected build environment variable or a locally maintained production env file that is not committed). Then inspect the built assets to confirm the approved origin is embedded and no loopback API URL remains. `VITE_*` values are public client-side values: never put secrets, credentials or tokens in them. No remote origin is guessed, no env file is changed, and no build is performed here.

## Proposed controlled startup procedure (not executed)

This procedure requires a separate explicit authorization before any service action. First identify the service owner/supervisor and the intended database with the operator; do not treat the candidate SQLite file as intended by default.

1. **Record and preserve the present state.** Re-read listener-to-PID mappings for ports 8000, 8001, 8501 and 5173; record timestamps and executable paths. Obtain the current service owner/supervisor's approved launch definition and rollback command without printing secret values. Do not alter the existing processes.
2. **Prepare data protection before any restart.** Identify the exact database, storage mode and active writers. A separately approved, consistent backup and isolated restore verification must be complete before any change that could disrupt service or database access. If database identity or backup recovery is unresolved, stop here. Do not create a replacement DB or migrate.
3. **Choose an unused, controlled test port and isolated verification target.** Prefer a temporary copy of a known database made with the database vendor's consistency-safe backup method, or a newly provisioned isolated test DB containing no real farmer data. Never point a diagnostic instance at the unknown live database. Do not proceed until the owner confirms the test target and cleanup/retention plan.
4. **Stage the exact runtime configuration securely.** From the requested project root, use the repository's `.venv\Scripts\python.exe`; explicitly set `CROP_PULSE_DATABASE_URL` to the verified isolated target, `CROP_PULSE_AUTO_CREATE_SCHEMA=0`, and environment mode to a non-production test mode. Keep credentials out of command history, console output and reports. Do not run Alembic or schema creation.
5. **Start only the isolated instance after approval.** Launch `backend.api:app` on the approved unused loopback port with working directory exactly the project root. Do not stop or replace PID 21152. Capture the new PID and parent in the service console or approved process-inspection tool.
6. **Identify before accepting writes.** Verify the new process executable is the project's virtual-environment Python; working directory is the project root; module path resolves to this project's `backend\api.py`; import path contains no unintended project copy; launch port is the selected test port; and the sanitized effective DB target matches the approved isolated target. Confirm auto-create is off and no migrations were invoked. If any check is unavailable or mismatched, do not permit writes and stop the verification.
7. **Make only read-only preflight calls.** Request health and OpenAPI from the new loopback port; verify expected route paths. Using the running app's configured SQLAlchemy engine, perform only a read-only identity query (SQLite canonical file path plus `PRAGMA user_version`/Alembic revision in read-only mode; PostgreSQL equivalent should identify the server/database in a read-only transaction). Avoid selecting farmer tables or returning private records. Compare the connection target to the independently approved test target. Do not run a registration, write, migration or table-creation request.
8. **Archive sanitized evidence.** Record timestamp, PID, executable, CWD, module `__file__`, import path summary, port, safe DB target identity, DB revision/integrity evidence, health/OpenAPI status and exact commands. Redact URL userinfo, passwords, query parameters and all personal data.
9. **Keep the existing runtime untouched pending review.** The isolated instance does not prove that the current API uses that target. To identify the current PID conclusively, the service owner must approve a controlled maintenance window and use an authorized process-inspection method or a planned restart with an approved, non-invasive runtime identity signal. Do not attach a debugger, dump process memory, or read raw environment values as a shortcut.

### Pre-write database identity checks

Before any application write is allowed in a future controlled instance, all of these must match:

- The selected source tree is the requested absolute project path; `backend.api.__file__` resolves within it.
- `sys.executable` resolves to that project's `.venv\Scripts\python.exe`; `os.getcwd()` equals the project root.
- The process's effective configuration is read from the running process context without exposing credentials. For SQLite, resolve the URL to a canonical absolute path and compare it to the owner-approved target. For PostgreSQL, redact credentials and verify host, port, database name and server identity against an owner-approved value.
- The SQLAlchemy engine actually opened by the application reports the expected dialect and connects read-only to the expected database identity. The configuration string alone is not proof of a successful connection to that database.
- Auto-create is disabled; no migration ran. The target's migration revision/schema evidence is inspected read-only and is compatible with the source. Any mismatch is a hard stop.
- Health/OpenAPI responses are obtained from the identified PID's selected port, and the schema matches the intended source's registered routes.

For a SQLite production target, do not run an independent check against a guessed path and infer API identity. Independently inspect candidate files only in read-only mode, and establish the API connection's canonical filename through a safely exposed, reviewed runtime diagnostic or service-side logs after separate authorization. This document does not add such diagnostics.

## Safe isolated verification test

Use an isolated target that contains no real farmer records. Confirm its identity independently before launch. Start the intended code on a separate loopback port with schema auto-creation disabled. Through the app's existing SQLAlchemy engine, issue a read-only connection check and collect only:

- SQLAlchemy dialect;
- canonical SQLite filename (or sanitized server/database identity for a server DB);
- Alembic revision and schema/table names or counts, without row contents;
- SQLite `integrity_check` and foreign-key check results, when applicable.

Compare these results with the isolated target's independently recorded identity and expected schema. The test passes only if both point to the same isolated target and no write or schema mutation occurred. A healthy endpoint, candidate DB integrity result, or configured URL alone is insufficient. This is a designed test, not one performed for this report.

## Service-preservation and rollback plan

- Keep the current listeners and data untouched while read-only identification and owner review proceed.
- Before a separately authorized replacement, document the old PID, executable, supervisor/start command, port bindings, sanitized configuration identity, database identity if established, and operator responsible. Keep the existing process available until the replacement has passed its checks and the change is approved.
- If the new isolated process fails identification, do not route users to it. Gracefully stop only the newly launched PID using its recorded PID/service handle, preserve logs, remove no database or backup, and confirm existing listener mappings remain unchanged.
- For a future production cutover, use a separately reviewed maintenance procedure: stop writes through the service owner, verify a tested backup/restore, change only the intended supervisor configuration, start the intended process, verify identity before traffic, and retain the previous launch configuration for reversal. No database rollback is automatic. If writes occur after cutover, stop and have the owner assess consistency before reverting service; never overwrite the database to “roll back” code.
- This task performs none of these service actions and does not authorize a restart.

## Evidence required to pass Gate 1

Gate 1 remains blocked until evidence from the actual running API establishes all of the following, without relying on health alone:

1. Listener PID and parent/supervisor are tied to the approved launch definition.
2. Executable, Python environment, current working directory, import path and `backend.api.__file__` identify the intended project copy.
3. Effective runtime settings are identified safely, including auto-create/migration behavior.
4. The application engine's actual database connection is tied to the owner-approved database target and expected schema/revision. For SQLite, this includes the absolute canonical file path; for PostgreSQL, a sanitized server/database identity.
5. OpenAPI routes from that identified process correspond to the intended source, resolving the prior weather-alert discrepancy with evidence.
6. The frontend production build embeds the deployment owner's approved HTTPS API origin and contains no loopback fallback.

The current evidence meets none of the process-to-source-to-database linkage requirements conclusively. The candidate SQLite file is healthy but is not linked to the API.

## Remaining deployment blockers

- API PID 21152 source tree, CWD, parent, launch arguments, Python environment and effective DB are unknown.
- The historical weather-alert route discrepancy has no proven root cause.
- No production API origin is provided; current frontend configuration and bundle target loopback.
- The Streamlit process is bound to `0.0.0.0`; its intended exposure and process relationship require a separate deployment review.
- Backup/restore, hosted production security, and authenticated browser workflows are not covered by this Gate 1C plan and remain open release evidence items. Gate 2 is not started.

## Checks performed for this plan

Read-only source/report/configuration inspection is based on the preceding Gate 1 and Gate 1B records and their listed commands. No service was launched, stopped or restarted; no environment/configuration/source/database file was edited; no migration, schema creation, authenticated request or database write was performed. No secret or farmer record was included.

**Verdict: BLOCKED — PLAN ONLY; EXECUTION NOT AUTHORIZED**
