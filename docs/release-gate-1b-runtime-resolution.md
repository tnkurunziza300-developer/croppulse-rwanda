# CropPulse Rwanda — Gate 1B: Runtime Resolution

**Audit date:** 2026-10-26 (Africa/Johannesburg)  
**Project:** `C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda`  
**Scope:** Read-only follow-up to [Release Gate 1](release-gate-1-runtime-database-identity.md). No application/configuration edits, service changes, migrations, database writes, or Gate 2 work.  
**Gate 1B verdict:** **BLOCKED**

## Executive result

Gate 1's uncertainties remain. The API responds on port 8001 and its current OpenAPI schema includes the weather-alert paths. The API process still runs the machine-level Python executable rather than the project's virtual environment. Windows did not return process metadata through CIM, WMI, or WMIC in this session. The current working directory, parent process, command line, Python import path, and process environment therefore remain unknown. Consequently, the loaded `backend.api` file and effective database target are not identified.

The local candidate `data/croppulse_phase1.sqlite3` remains structurally healthy in a read-only check; there is still no process-level evidence that it is the API's database. The frontend's local `.env` settings and generated bundle point to loopback. No production API URL is configured or known.

No restart, remediation, database write, schema creation, or migration was performed. **Do not proceed to Gate 2 until the intended API runtime and database have been identified.**

## Evidence verified

### Windows process inspection

Read-only Windows methods were checked for listeners on ports 8000, 8001, 8501, and 5173:

| Listener | PID | Executable / start time | Parent, command line, working directory, environment |
|---|---:|---|---|
| Port 8000 | — | No listener observed | Not applicable |
| `127.0.0.1:8001` | 21152 | `C:\Users\Student\AppData\Local\Programs\Python\Python312\python.exe`; 2026-10-26 10:31:09 | **UNVERIFIED** |
| `0.0.0.0:8501` | 24140 | `C:\Users\Student\AppData\Local\Programs\Python\Python312\python.exe`; 2026-10-26 10:36:25 | **UNVERIFIED** |
| `127.0.0.1:5173` | 11512 | `C:\Users\Student\AppData\Local\nodejs\node.exe`; 2026-10-26 08:50:49 | **UNVERIFIED** |

The listener set and PIDs were unchanged from Gate 1 at the 2026-10-26 12:00 +02:00 check. Evidence supports only the socket-to-PID mapping and executable image paths; it does not identify imported Python source or runtime configuration.

Methods and limitations:

- `netstat -ano -p tcp` maps listening addresses and ports to PIDs. It does not report process ancestry, CWD, environment, or Python imports.
- `Get-Process -Id ... | Select Id,ProcessName,Path,StartTime` returned the executable image paths and start times. The `System.Diagnostics.Process` properties available here do not provide a target process's current working directory, environment block, parent PID, or command line.
- `Get-CimInstance Win32_Process` and `Get-WmiObject Win32_Process` returned no process records for the listeners.
- `WMIC.exe` is installed, but its read-only `Win32_Process` queries also returned no records for these PIDs. No raw command line was printed.
- Process Explorer and Sysinternals Handle utilities were not installed. No debugger, process-memory inspection, environment dump, or handle-inspection utility was used.
- Even if a process command line were available, a Python `-m uvicorn backend.api:app` argument would not by itself prove which `backend.api` module was imported. The actual module `__file__` or an authoritative launch/deployment manifest would be needed. Python source module identity is not a native Windows loaded-module entry.

The API's observed Python executable is **not** the expected project `.venv\Scripts\python.exe`. That is a **FAILED** match to the documented project's virtual-environment launch configuration. It does not prove which source copy is loaded. The Streamlit listener is bound to all IPv4 interfaces (`0.0.0.0`), while the documented launcher binds it to `127.0.0.1`; its firewall reachability remains unknown.

### Source, startup, and database configuration

Inspected `backend/api.py`, `backend/db.py`, `backend/migrations/env.py`, `run_streamlit.ps1`, `docs/react-app-setup.md`, and frontend configuration.

- `backend/db.py::database_url()` uses the API process's `CROP_PULSE_DATABASE_URL`, otherwise `sqlite:///./data/croppulse_phase1.sqlite3`. The default SQLite path is relative to the API process CWD.
- `backend/migrations/env.py` selects the same environment variable and relative fallback for Alembic.
- `backend/api.py` only invokes `Base.metadata.create_all()` during application lifespan when `CROP_PULSE_AUTO_CREATE_SCHEMA=1`; production/staging validation rejects that setting. No import, startup, or migration was executed in this audit.
- `docs/react-app-setup.md` documents running from the project root with `\.venv\Scripts\python.exe -m uvicorn backend.api:app --host 127.0.0.1 --port 8001`, after configuring `CROP_PULSE_DATABASE_URL`. This is a reproducible **local** setup pattern. Its sample relative SQLite target is not proof of the running API's target and is not a production target.
- `run_streamlit.ps1` uses the project `.venv` and project root when it starts an API because port 8001 is free. It sets the documented local SQLite URL and `CROP_PULSE_AUTO_CREATE_SCHEMA=0` for that child process. If an API already listens on 8001, the script checks health, CORS/CSRF, and selected authentication, farm, and handoff paths, then reuses the listener. It does not verify PID executable, source path, CWD, effective DB target, or the weather-alert routes. It will not replace a passing existing listener.
- The same script refuses to start a second Streamlit service when port 8501 is already occupied and, when it does start Streamlit, requests `--server.address 127.0.0.1`. The currently observed process and bind do not match those documented launch characteristics. The actual startup method is **UNVERIFIED**.
- No Dockerfile, Compose file, Procfile, Windows service definition, or cloud-provider deployment manifest was found in the inspected root launch/configuration files. `run_streamlit.ps1` and the documented manual Uvicorn command are the identified local launch paths.

**Effective runtime DB configuration: UNVERIFIED.** The current process environment and CWD are unavailable. The API may be using the project candidate, another relative SQLite file, an absolute SQLite file, or a PostgreSQL URL. No safe evidence here distinguishes those possibilities.

### Candidate database, read-only

The candidate was rechecked using a SQLite `mode=ro` URI. No farmer or other personal rows were selected.

| Evidence | Result |
|---|---|
| Absolute path | `C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda\data\croppulse_phase1.sqlite3` |
| File size | 19,402,752 bytes |
| Last-write metadata | 2026-10-26 11:49:40 +02:00; writer/attribution unknown |
| Revision | `0015_weather_alert_foundation` |
| `PRAGMA integrity_check` | `ok` |
| `PRAGMA foreign_key_check` | 0 violations |
| Application table count | 24; weather alert preference and alert tables exist |
| `-wal` / `-shm` sidecars | Not present when checked |

This verifies the candidate file only. It does not establish the live API database identity. The file's modification time is not attributed to a process and is not treated as proof of live use.

### Weather-alert route discrepancy

The current `backend/api.py` defines the following unconditional direct FastAPI decorators:

| Source | Current live OpenAPI | Status |
|---|---|---|
| `GET /v1/weather/alert-preferences` | Present | Match |
| `PUT /v1/weather/alert-preferences/{field_id}` | Present | Match |
| `GET /v1/weather/alerts` | Present | Match |
| `PATCH /v1/weather/alerts/{alert_id}/status` | Present | Match |

At 2026-10-26 12:00 +02:00, `GET /health` returned HTTP 200 and `GET /openapi.json` returned HTTP 200, title `CropPulse Rwanda Farmer Records API`, version `1.0.0`, with 62 paths and all four alert routes. Source/schema parity for these paths is **VERIFIED** for this observation.

The earlier Gate 1 report recorded the same API PID and executable with those routes absent. The PID and start-time observations were unchanged in this follow-up, while the route observations differ. The weather routes in current source are not conditionally registered, and the launcher does not check them before reusing an existing API. Thus the launcher design explains why route presence is not a runtime identity check and could permit reuse of a different or older API. It does **not** prove why the earlier and current schemas differed. Different process internals, imported source, a reload/worker behavior, or an earlier observation discrepancy remain hypotheses; the cause is **UNVERIFIED**. No route or service changes were made.

### Frontend API URL and loopback cause

- `frontend/src/api.ts` selects `import.meta.env.VITE_API_BASE_URL` and falls back to `http://127.0.0.1:8001`.
- `frontend/.env`, `frontend/.env.local`, and `frontend/.env.example` currently set that variable to `http://127.0.0.1:8001`. `frontend/.env.production` and `.env.production.local` are absent. The Vite config does not provide a deployment host, and `package.json`'s build script is `tsc -b && vite build`.
- A read-only scan found the loopback URL in the current `frontend/dist` bundle. This is the expected local-development setting; it is not a valid remote-server target for users because `127.0.0.1` refers to each user's own machine.
- No public API origin was supplied, so no URL was guessed or inserted. For a future remote build, the deployment owner should provide the approved HTTPS API origin through the build environment or an uncommitted mode-specific `.env.production.local`, run the existing production build, and verify the generated assets contain the approved origin. `VITE_*` values are public client configuration; secrets must never be placed there. A same-origin reverse proxy can use the approved public app/API origin if that is the chosen topology.

The intended mechanism is therefore **build-time Vite configuration**, not a runtime secret or a browser credential. Production configuration remains **UNVERIFIED**.

## Commands and checks used

Read-only checks in this follow-up included:

```powershell
Resolve-Path .
netstat -ano -p tcp
Get-Process -Id 21152,24140,11512 | Select-Object Id,ProcessName,Path,StartTime
Get-CimInstance Win32_Process -Filter 'ProcessId = 21152 OR ProcessId = 24140 OR ProcessId = 11512'
Get-WmiObject Win32_Process -Filter 'ProcessId = 21152 OR ProcessId = 24140 OR ProcessId = 11512'
& "$env:WINDIR\System32\wbem\WMIC.exe" process where "ProcessId=21152" get ProcessId,ParentProcessId,ExecutablePath,CommandLine /format:list
Get-Command procexp.exe,procexp64.exe,handle.exe,handle64.exe,wmic.exe
GET http://127.0.0.1:8001/health
GET http://127.0.0.1:8001/openapi.json
```

Process query output was restricted to executable, timestamps, IDs, availability booleans, and sanitized application-target classifications. Command lines and environment values were not emitted. The SQLite read-only check used `sqlite3.connect(file_uri_with_mode_ro)`, selected only `alembic_version`, `sqlite_master` table names, and `PRAGMA integrity_check` / `PRAGMA foreign_key_check` results.

No automated test suite was run: tests cannot establish the identity of an already-running service. No browser, authenticated request, migration, start/stop, environment mutation, or configuration edit was performed.

## Findings classified

| Finding | Classification |
|---|---|
| Current project source has the described DB URL fallback and conditional auto-schema behavior | **VERIFIED** |
| Current documented local launcher uses the project virtual environment and root, and reuses an existing API based on limited HTTP checks | **VERIFIED** |
| Current listener PID/executable mapping and port binds | **VERIFIED** |
| Current API's `/health`, OpenAPI metadata, and four weather-alert paths | **VERIFIED** |
| Candidate SQLite file's identity, size, revision, table evidence, and read-only integrity results | **VERIFIED** |
| Current local frontend URL configuration and loopback URL in the generated bundle | **VERIFIED** |
| Running API executable matches the documented project virtual environment | **FAILED** |
| Running Streamlit bind matches the documented loopback bind | **FAILED** |
| Running API loaded source tree/module file | **UNVERIFIED** |
| Running API process CWD, ancestry, command line, and process environment | **UNVERIFIED** |
| Effective running API database engine and absolute target | **UNVERIFIED** |
| Candidate SQLite file is the database used by the running API | **UNVERIFIED** |
| Cause of earlier-versus-current weather-alert OpenAPI discrepancy | **UNVERIFIED** |
| Production frontend API origin and deployment suitability | **UNVERIFIED** |
| Streamlit network reachability through firewall | **UNVERIFIED** |

## Safe, reversible resolution plan

### Read-only actions first

1. The authorized Windows process/service owner should identify how PIDs 21152, 24140, and 11512 were launched. Use the owning service manager or original launch console to confirm executable, parent/service, command arguments, working directory, and deployment/source directory. Preserve the evidence in a restricted operations record; do not paste raw command lines or environment dumps into a report.
2. If an authorized process-inspection tool is used, inspect only the necessary fields. For environment inspection, read only `CROP_PULSE_DATABASE_URL` and redact username, password, token, query values, and any secret-bearing path components. Do not dump the full environment. No such tool was available in this session.
3. Determine the DB target from the actual process configuration. Resolve SQLite paths against the confirmed process CWD; for PostgreSQL record only engine, approved host, port, and database name, not credentials. If the configuration owner cannot establish the actual process environment non-disruptively, keep the identity **UNVERIFIED**.
4. Verify the loaded source using an authoritative deployment artifact/manifest or process-owner startup evidence. A separately run `python -c` command only proves what that new command would import; it does not prove what PID 21152 already loaded.
5. Once the process target is known, open that exact database read-only and compare its revision/integrity without selecting personal records. Do not use `data/croppulse_phase1.sqlite3` unless the resolved live target matches it.
6. Obtain the intended public HTTPS API origin from the deployment owner. Configure it only for the production frontend build, rebuild, and inspect the bundle for that origin. Do not publish the localhost-configured `dist` bundle to remote users.

### Controlled restart only if read-only evidence is insufficient

No restart is authorized or performed by this report. If the service owner cannot recover current source/runtime/database identity from existing startup records, use a separately approved maintenance change:

1. Record the exact listener PIDs, executable paths, service owner, existing launch parameters, current working directory if obtainable, effective database target, and secure location of the existing secret/configuration. Confirm a recovery contact and downtime window.
2. Before any stop/start, complete the separately approved backup/recovery gate against the **identified** database. Verify backup access controls and an isolated restore. This Gate 1B report does not perform or pass that gate.
3. Arrange a quiet window; confirm no active writes and notify users. Save the old launch configuration without printing secrets. Do not change the DB target or run migrations.
4. Under separate explicit authorization, gracefully stop only the identified API PID/service. Start the intended app from the project root with `.venv\Scripts\python.exe`, `backend.api:app`, the already verified database setting, and `CROP_PULSE_AUTO_CREATE_SCHEMA=0`. Do not substitute the local example DB URL for an unknown live target.
5. At startup, emit only non-secret identity evidence to a protected log: `sys.executable`, `os.getcwd()`, `backend.api.__file__`, the DB dialect and sanitized target (absolute SQLite path or redacted PostgreSQL endpoint/database), and schema auto-create state. Never log the raw URL, username, password, query string, or secret key. Then check only `/health` and `/openapi.json` and confirm the process PID and exact listener mapping.
6. If any identity/path/revision check differs, do not accept traffic. Gracefully stop only the new PID and restore the preserved previous service command/configuration and listener binding, without a migration or database restore. Recheck health and the prior route schema. If any write occurred, pause and have the data owner assess consistency before switching back; do not overwrite or “roll back” the database automatically.
7. After a successful, recorded Gate 1 identity result, request the next gate separately. Do not automatically proceed to Gate 2 or deployment.

## Remaining blockers

- Live API source/import path, working directory, parent/service, and process environment are not proven.
- Effective API database URL, engine, and absolute target are not proven; the healthy candidate file is not linked to the process.
- Historical weather-alert route discrepancy remains unexplained despite current route parity.
- Production Vite API origin is unknown; current generated frontend output targets loopback.
- Streamlit is bound to `0.0.0.0:8501`; firewall/network reachability is unknown.
- The protected backup/restore gate, hosted security gate, and authenticated browser-workflow gate remain outstanding and were not assessed here.

## Gate 1B verdict: **BLOCKED**

The evidence does not establish the intended running API source, effective runtime configuration, or database. The current local frontend build is loopback-configured rather than verified for the intended deployment. No remediation, restart, database action, or Gate 2 activity should begin until the read-only identity blockers are resolved and any separately required actions receive explicit authorization.
