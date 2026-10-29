# CropPulse Rwanda — Release Gate 1: Live Runtime and Database Identity

**Audit date:** 2026-10-26 (Africa/Johannesburg)  
**Project directory:** `C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda`  
**Scope:** Read-only verification of current local listeners, API/source identity, database configuration and candidate SQLite metadata, weather-alert routes, and frontend API-base configuration.  
**Gate 1 verdict:** **BLOCKED**

## Executive result

The current API at `127.0.0.1:8001` responds with HTTP 200 and exposes the weather-alert routes. Those facts do not prove which source tree it loaded or which database it uses. Its listening process runs a global Python executable rather than this project's `.venv`; Windows process queries in this session did not return its command line, parent process, working directory, or environment. Therefore the loaded application and effective database target cannot be established conclusively.

The candidate database at this project's `data/croppulse_phase1.sqlite3` is healthy in read-only checks, is 19,402,752 bytes, and reports revision `0015_weather_alert_foundation`. It is a candidate only. No evidence links it to the current API process.

The current frontend development settings point to the local API at `http://127.0.0.1:8001`. The current `frontend/dist` bundle also contains that loopback URL. No production API origin or `.env.production` file was found, so production frontend configuration is unverified and the current local bundle is not established as a deployment artifact.

## 1. Commands and checks performed

All process, HTTP, source, and database operations below were read-only. No account, authenticated request, SQL write, migration, schema creation, service action, environment change, or permission change was performed. No farmer data or secret values were printed.

| Check | Result |
|---|---|
| Resolve current directory with `Resolve-Path .` | `C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda`, matching the requested project directory. |
| Inspect `docs/final-development-day-release-report.md` | Reviewed prior release blockers and the earlier runtime/route observations. |
| Inspect `backend/api.py`, `backend/db.py`, `backend/migrations/env.py`, `run_streamlit.ps1`, `frontend/src/api.ts`, and `frontend/vite.config.ts` | Confirmed source route decorators, DB URL selection, conditional schema creation, Alembic URL selection, documented launcher behavior, and frontend API-base selection as described below. |
| `netstat -ano -p tcp` filtered to listening ports 8000, 8001, 8501, and 5173 | No listener on 8000. Listeners observed on ports 8001, 8501, and 5173; details below. |
| `Get-Process -Id <listener PIDs> | Select Id,ProcessName,Path,StartTime` | Returned executable paths and process start times below. |
| `Get-CimInstance Win32_Process ...` and `Get-WmiObject Win32_Process ...` for listener PIDs | No process metadata returned. The raw command line was not emitted. Parent, command line, working directory, and process environment remain unavailable. |
| `GET http://127.0.0.1:8001/health` | HTTP 200. Read-only request. |
| `GET http://127.0.0.1:8001/openapi.json` | HTTP 200 at 2026-10-26 11:51 +02:00; API title/version and route set recorded below. |
| Inspect frontend env-file names and only `VITE_API_BASE_URL` | `.env` and `.env.local` both resolve to the local API origin. `.env.production` and `.env.production.local` were absent. No other environment values were printed. |
| `rg -l -F 'http://127.0.0.1:8001' frontend\dist\assets` | Found the loopback origin in the current generated frontend bundle. |
| Resolve candidate SQLite file, inspect file metadata, and open SQLite URI with `mode=ro` | Absolute path, file size, revision, schema evidence, and integrity results below. No farmer rows were selected. |
| `\.venv\Scripts\python.exe -m alembic heads` | Source migration head is `0015_weather_alert_foundation`; this did not connect to or modify the candidate or a live database. |

An initial PowerShell attempt to parse `netstat` columns failed locally because its whitespace split treated the protocol label as a port. It did not alter system state. A corrected regular-expression parser returned the listener mapping below.

## 2. Expected versus observed runtime identity

### Expected from this project's documented launcher

`run_streamlit.ps1` resolves the project root from `$PSScriptRoot`, uses `.venv\Scripts\python.exe`, starts `uvicorn backend.api:app` with that project root as the working directory, and, when it starts a new API itself, supplies the local relative SQLite URL and disables automatic schema creation. It checks and reuses an existing API listener instead of replacing it. The documented standalone API command likewise uses the project virtual environment and project root.

In source, `backend/db.py::database_url()` selects the process value of `CROP_PULSE_DATABASE_URL`, falling back to `sqlite:///./data/croppulse_phase1.sqlite3`. That SQLite path is relative and resolves against the API process working directory. `backend/migrations/env.py` uses the same environment variable and relative fallback for Alembic.

`backend/api.py` runs `Base.metadata.create_all(get_engine())` only in the application lifespan when `CROP_PULSE_AUTO_CREATE_SCHEMA=1`. Staging/production validation rejects that setting. No application import, server start, or migration was performed during this gate.

### Current listeners

Observed on 2026-10-26 at approximately 11:50 +02:00:

| Port / listener | PID | Executable and start time | Command line / parent / CWD / process environment |
|---|---:|---|---|
| 8000 | — | No listener observed | Not applicable |
| `127.0.0.1:8001` API | 21152 | `C:\Users\Student\AppData\Local\Programs\Python\Python312\python.exe`; started 10:31:09 | **Unverified.** Windows CIM/WMI queries returned no process metadata. |
| `0.0.0.0:8501` Streamlit | 24140 | `C:\Users\Student\AppData\Local\Programs\Python\Python312\python.exe`; started 10:36:25 | **Unverified.** Windows CIM/WMI queries returned no process metadata. |
| `127.0.0.1:5173` Vite | 11512 | `C:\Users\Student\AppData\Local\nodejs\node.exe`; started 08:50:49 | **Unverified.** Windows CIM/WMI queries returned no process metadata. |

The API's observed executable is not this project's `.venv\Scripts\python.exe`, and the Streamlit listener's `0.0.0.0` bind differs from the documented launcher's `127.0.0.1` bind. These are **FAILED** matches to the documented local launcher identity. They do not by themselves prove that the imported API source is from a different project copy. The actual API source/import path remains **UNVERIFIED**.

The Streamlit `0.0.0.0:8501` bind listens on all IPv4 interfaces. Firewall and network reachability were not examined in this Gate 1 audit. No stop, rebind, or other service operation was attempted.

## 3. Live OpenAPI versus inspected source

The inspected `backend/api.py` defines the following handlers directly on the FastAPI application; no separate router inclusion is required for these paths:

| Source definition | Live OpenAPI method/path | Comparison |
|---|---|---|
| `@app.get("/v1/weather/alert-preferences")` | `GET /v1/weather/alert-preferences` | Match |
| `@app.put("/v1/weather/alert-preferences/{field_id}")` | `PUT /v1/weather/alert-preferences/{field_id}` | Match |
| `@app.get("/v1/weather/alerts")` | `GET /v1/weather/alerts` | Match |
| `@app.patch("/v1/weather/alerts/{alert_id}/status")` | `PATCH /v1/weather/alerts/{alert_id}/status` | Match |

The current OpenAPI response reported title `CropPulse Rwanda Farmer Records API`, version `1.0.0`, and 62 paths. All four weather-alert paths and methods currently appear in it.

The earlier Phase 6 report recorded the alert paths absent and identified PID 21152 running the same global Python executable. This audit again observed PID 21152, but the routes are now present. No current process metadata reveals a new PID, source directory, reload mechanism, imported module path, or conditional runtime configuration that explains the difference. The evidence supports **current source/schema route parity** for these four endpoints; it does **not** distinguish whether the earlier discrepancy came from a different application instance/source, a changed process/import state, or an earlier observation error. Root cause is **UNVERIFIED**. No change was made to resolve it.

## 4. Database identity and candidate integrity

### Effective database used by the running API

**UNVERIFIED.** The API source allows `CROP_PULSE_DATABASE_URL` to override the default. The current process environment and working directory could not be read through the available supported Windows process queries. Therefore the effective engine, absolute SQLite path (if SQLite is used), or PostgreSQL target cannot be established. The default project path must not be treated as the live database identity.

### Candidate database checked read-only

| Evidence | Result |
|---|---|
| Canonical path | `C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda\data\croppulse_phase1.sqlite3` |
| File size | 19,402,752 bytes |
| File last-write metadata observed | 2026-10-26 11:49:40 +02:00; attribution is unknown and no inference about the API's connection is made. |
| Alembic revision | `0015_weather_alert_foundation` |
| `PRAGMA integrity_check` | `ok` |
| `PRAGMA foreign_key_check` | 0 violations |
| Non-sensitive schema evidence | 24 application tables; includes `alembic_version`, `farms`, `farm_fields`, `crop_plans`, `weather_alert_preferences`, `weather_alerts`, `private_conversations`, and `private_messages`. |
| SQLite sidecar metadata | No `-wal` or `-shm` sidecar was present at the time checked. |

The SQLite connection used a `file:...?...mode=ro` URI. Only schema names, revision, file metadata, and integrity PRAGMAs were read. No account, farm, message, or other private records were queried. These results verify this candidate file only, not a live API connection.

## 5. Frontend API base URL

- `frontend/.env` and `frontend/.env.local` both set `VITE_API_BASE_URL` to `http://127.0.0.1:8001`; the source default in `frontend/src/api.ts` is the same local origin. This is consistent with the local Vite/API setup observed on ports 5173 and 8001.
- No `frontend/.env.production` or `.env.production.local` file was present. No production hostname was supplied, so the intended production API origin cannot be verified.
- The existing `frontend/dist` output contains the literal local loopback API origin. A browser accessing such a bundle from another machine would resolve `127.0.0.1` on that browser's own device, not to the CropPulse server. The bundle is therefore verified as local-development-configured, not as a production-configured artifact. Build production assets only after the deployment owner supplies the intended HTTPS API origin, then inspect the output without exposing secrets.

## 6. Findings by status

### VERIFIED

- The current working directory is the requested project tree.
- The inspected source uses `CROP_PULSE_DATABASE_URL` or a working-directory-relative SQLite fallback; Alembic uses the same setting.
- Automatic table creation is conditional on `CROP_PULSE_AUTO_CREATE_SCHEMA=1`; the reviewed deployment configuration expects Alembic migrations instead.
- Current API health is HTTP 200 and current OpenAPI includes all four source-defined weather-alert methods/paths.
- The candidate SQLite file passes read-only integrity checks at revision 0015, with zero foreign-key violations.
- Current frontend development configuration targets the local API; the generated bundle contains that same loopback origin.

### FAILED

- The running API executable does not match the documented project's `.venv` Python executable. The Streamlit listener also differs from the documented launcher's loopback bind. The source/import path is not identified, so this is a failed documented-runtime match, not proof of a different source tree.
- The checked `frontend/dist` bundle is local-loopback configured and is not verified as suitable for a remote deployment.

### UNVERIFIED

- API command line, parent process, current working directory, environment, Python import path, and loaded `backend.api` file.
- Effective database URL/engine and absolute database target for the running API.
- Whether the candidate SQLite file is the database used by PID 21152.
- Root cause of the earlier missing weather-alert paths despite current live/source parity.
- Production frontend API base URL and intended deployment API origin.
- Firewall/network reachability of the all-interface Streamlit listener.
- Production database migration compatibility. Source head is 0015, but the production database identity and revision are unknown.

## 7. Exact next actions and remaining risks

1. The authorized process/service owner should use the service manager or the original launch console to provide sanitized evidence for PID 21152: executable, exact module/script target, project working directory, parent/service identity, and whether `CROP_PULSE_DATABASE_URL` is set. Do not copy raw environment dumps or connection URLs into tickets or reports.
2. From that same authoritative configuration, derive only the database engine and sanitized target. For SQLite, resolve the relative path against the confirmed process working directory and compare its canonical absolute path with the candidate above. For PostgreSQL, identify the approved server/database without printing usernames, passwords, or query credentials. If the process owner cannot recover this information without changing the service, keep Gate 1 blocked; do not add a diagnostic route or restart under this audit.
3. Record the source file path/release artifact hash from the process owner or service deployment manifest and compare it with this repository's intended release artifact. Do not infer it from the executable name or OpenAPI title.
4. Have the deployment owner supply the production HTTPS API origin; configure it only in the approved production build environment, rebuild, and verify the generated bundle contains that origin rather than loopback. Do not add credentials to `VITE_*` variables.
5. Once runtime/source/database evidence is independently confirmed, review the intended DB revision and migration plan under the separate backup and migration approval gate. No migration or recovery action was performed here.
6. Keep Gate 2 backup/recovery, Gate 3 hosted security, and Gate 4 authenticated browser workflows **not assessed by this report**. This report does not mark them passed.

## Gate 1 verdict: **BLOCKED**

A PASS requires evidence linking the running API to this intended source artifact, its effective runtime configuration, and the intended database. Only the local candidate file and current API route schema were verified. That required linkage is absent; do not proceed to remediation, database migration, or Gate 2 based on this result alone.
