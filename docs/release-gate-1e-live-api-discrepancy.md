# CropPulse Rwanda — Gate 1E: Existing API Discrepancy Investigation

**Date:** 2026-10-26 (Africa/Johannesburg)  
**Project root:** `C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda`  
**Scope:** Read-only investigation of the existing API on port 8001 and the route difference recorded in the Gate 1D isolated test.  
**Verdict: BLOCKED — FURTHER AUTHORIZED DIAGNOSTICS REQUIRED**

## Executive result

The existing API listener remains PID `21152` at `127.0.0.1:8001`. Its health endpoint succeeds. A corrected OpenAPI inspection at 2026-10-26 12:35 +02:00 finds all four weather-alert paths in its 62-path schema. The controlled API test on port 18001, recorded in the Gate 1D results, also contained all four paths and was proven to use this project's source and isolated synthetic database.

The earlier Gate 1D report said the existing API lacked the four paths. Investigation found that the comparison command used `$schema.paths.PSObject.Name -contains $path`; on the same live response this expression incorrectly reports the routes absent. Using `$schema.paths.PSObject.Properties.Name -contains $path` reports all four present. The prior “missing routes” observation is therefore most likely a PowerShell OpenAPI-property extraction error, not a confirmed API route discrepancy. The same PID and process start time are still observed. The exact route set at the earlier report timestamp cannot be independently reconstructed, so this is a strong explanation rather than proof of the historical response.

Current source registers the weather-alert operations directly on `backend.api:app` with unconditional FastAPI decorators. No `include_router` or conditional registration is needed for these four routes. A safe existing endpoint that discloses the running process's database identity was not found. Health checks only database reachability with `SELECT 1`; OpenAPI reports paths and schemas.

Windows process metadata access did not establish PID 21152's parent, working directory, command line, environment or imported Python module. The existing database identity remains unknown. No secret values or farmer records were exposed, and no process, source, configuration or database was changed.

## 1. Current listener and API evidence

### Listener check

Commands used:

```powershell
netstat -ano -p tcp | Where-Object {
  $_ -match 'LISTENING' -and $_ -match ':(8000|8001|8501|5173|18001)\s'
}
Get-Process -Id 21152,24140,11512 -ErrorAction SilentlyContinue |
  Select-Object Id,ProcessName,Path,StartTime
```

Observed listeners:

| Port | Listener | PID | Process image/path evidence |
|---:|---|---:|---|
| 8000 | None observed | — | — |
| 8001 | `127.0.0.1` | 21152 | `python.exe`, OS-reported base interpreter path `C:\Users\Student\AppData\Local\Programs\Python\Python312\python.exe`; start time 2026-10-26 10:31:09 |
| 8501 | `0.0.0.0` | 24140 | `python.exe`, same OS-reported base interpreter path; start time 2026-10-26 10:36:25 |
| 5173 | `127.0.0.1` | 11512 | `node.exe`; start time 2026-10-26 08:50:49 |
| 18001 | None observed | — | Isolated test process PID 32648 had been stopped after Gate 1D |

The three original PIDs and bindings were unchanged from the Gate 1D cleanup check. No process was stopped, restarted or signaled.

### Existing API requests

Commands used (unauthenticated GET only):

```powershell
Invoke-RestMethod 'http://127.0.0.1:8001/health' -TimeoutSec 5
$schema = Invoke-RestMethod 'http://127.0.0.1:8001/openapi.json' -TimeoutSec 8
```

Results at 2026-10-26 12:35 +02:00:

- `/health`: HTTP 200, `status: ok`.
- OpenAPI: HTTP 200, title `CropPulse Rwanda Farmer Records API`, version `1.0.0`, 62 paths.
- `/v1/weather/alert-preferences`: present (`GET`).
- `/v1/weather/alert-preferences/{field_id}`: present (`PUT`).
- `/v1/weather/alerts`: present (`GET`).
- `/v1/weather/alerts/{alert_id}/status`: present (`PATCH`).

The corrected key lookup was:

```powershell
$names = @($schema.paths.PSObject.Properties.Name)
$names -contains '/v1/weather/alerts'
```

The defective expression used in the earlier check was:

```powershell
$schema.paths.PSObject.Name -contains '/v1/weather/alerts'
```

It returned false for a route that the corrected lookup showed present in the same schema response. The local API responds directly on loopback; successful route checks still do not identify its source tree or database.

## 2. Comparison with isolated test and current source

The [Gate 1D isolated test report](release-gate-1d-isolated-launch-results.md) records process PID 32648 running at `127.0.0.1:18001`, using the project virtual environment, working directory and `backend/api.py`, with the exact synthetic database opened read-only. Its health returned `ok`; OpenAPI had 62 paths and all four alert routes. Its database hash and size remained unchanged. The process was stopped and port 18001 is no longer listening.

Current source inspection used:

```powershell
Select-String -Path backend\api.py -Pattern '^app = FastAPI|^@app\.get\("/health"\)|^@app\.(get|put|patch)\("/v1/weather/(alert-preferences|alerts)|include_router|^async def lifespan|create_all|get_engine\(\)'
```

Confirmed source structure:

- `backend/api.py` constructs `FastAPI(...)` at line 204.
- The health operation is a direct `@app.get("/health")` route at line 269; it executes `SELECT 1` through `get_engine()` and returns `{"status":"ok"}`.
- The alert operations are direct decorators at lines 560, 586, 643 and 653: GET preference list, PUT preference update, GET alert history, and PATCH alert status.
- The source search found no `include_router` registration. These routes are attached directly to the app and are not conditionally mounted.
- The lifespan creates tables only when `CROP_PULSE_AUTO_CREATE_SCHEMA` is exactly `1`; it does not conditionally register routes. No migration runs as part of that source lifespan.

The Gate 1D report's different-route claim is not supported by the flawed PowerShell property lookup. The corrected current request finds the same four routes in the existing API and isolated API schemas. The live PID and start time are unchanged since the earlier checks; the available evidence no longer indicates a route discrepancy, though the historic response body was not retained.

## 3. Windows process identification attempts

Read-only checks performed:

- `Get-Process` confirmed PID, process name, executable image path and start time.
- `Get-CimInstance Win32_Process` for PID 21152 failed with `CimException: Access denied`; prior Gate 1/1B checks also recorded no useful CIM/WMI/WMIC process details.
- `wmic process ... get ProcessId,ParentProcessId,ExecutablePath,CreationDate /format:list` failed with `process - Alias not found` on this machine.
- `tasklist /fi "PID eq 21152" /fo list` returned `ERROR: Access is denied`.
- `Get-Command procexp.exe,handle.exe,handle64.exe` found none of those utilities. WMIC was present, but its process query was not usable.

No raw process command line or process environment was printed. Parent PID, process command line, working directory, `CROP_PULSE_DATABASE_URL`, `CROP_PULSE_AUTO_CREATE_SCHEMA`, and the Python module import path are **unverified**.

### Executable-path qualification

The earlier audit reports treated the OS-reported Python executable path as evidence that existing API PID 21152 did not use the project venv. Gate 1D provides a relevant control: its API was invoked with the exact `.venv\Scripts\python.exe`, asserted `sys.executable` under the project `.venv`, and imported the project API; nevertheless, Windows `Get-Process` reported the base Python 3.12 image path for that test process too. Therefore the OS-reported image path alone does **not** distinguish a venv-launched process from a global-interpreter launch on this host. The earlier inference should be considered unproven. It does not establish that PID 21152 used the venv either.

## 4. Launcher and startup evidence

`run_streamlit.ps1` uses the project `.venv\Scripts\python.exe`. If port 8001 already has a listener, its `Test-CropPulseApi` checks health, browser CSRF/CORS and a subset of login, farm and handoff paths, then reuses that listener. It does not check the four weather-alert paths or process identity. Thus the launcher can accept an API whose OpenAPI differs from current source.

When the launcher starts a new API itself, it sets its configured local database URL, disables schema auto-creation, starts `backend.api:app` from `$PSScriptRoot`, and binds port 8001. Those facts describe that branch of the script; they are not evidence that the currently running PID used it. No launcher was run in this investigation.

## 5. Existing diagnostics and database identity

No existing safe diagnostic route was found that returns the database filename, server/database identity, migration revision or SQLAlchemy engine target. `/health` runs `SELECT 1`, which proves only that some configured database connection is reachable. `/openapi.json` exposes API metadata and routes, not DB identity.

`backend.db.database_url()` uses the process environment variable `CROP_PULSE_DATABASE_URL`, falling back to a relative SQLite path. Resolving the fallback requires the process working directory. Neither the effective environment value nor the CWD of PID 21152 is available. **The database used by the existing API is unknown.** No database was opened or inspected in this investigation.

## 6. Verified facts and unresolved explanations

### Verified facts

1. PID 21152 currently owns the listener at `127.0.0.1:8001`.
2. Its current health endpoint responds successfully.
3. At 12:35, its 62-path OpenAPI schema includes all four expected alert paths.
4. A flawed PowerShell property expression used in the earlier absent-route comparison returns false for these keys; the correct `.PSObject.Properties.Name` expression returns true on the same response.
5. The controlled project API on port 18001 previously included all four paths and was stopped cleanly.
6. Current project source registers all four routes directly and unconditionally.
7. `run_streamlit.ps1` can reuse an existing API after a limited readiness check that does not test process identity.
8. The API's DB health route reveals reachability only; no existing DB identity diagnostic was found.
9. The current process's source, CWD, parent, environment and database are not proven.

### Competing hypotheses (not established)

- **OpenAPI inspection defect — high confidence for the reported mismatch:** The previous check used `.PSObject.Name`; testing both expressions against the current response reproduces false absence versus true presence. This likely explains the earlier report, but the old response body was not retained, so the historical observation cannot be fully revalidated.
- **Different or older source/app process:** Still possible because PID 21152's import path is unknown, but current route presence no longer supports the claim that the live server is missing these operations.
- **Reuse of an unrelated API by the launcher:** The launcher can reuse a listener after limited checks. This remains a potential identity risk, but no evidence proves that this launcher started or reused the present process.
- **Different import path/configuration:** A different working directory or Python import path could resolve `backend.api` from another tree; both remain unknown.
- **Stale OpenAPI schema cache:** No current evidence supports this; the corrected live response contains the routes.
- **Port or proxy mismatch:** The local listener is mapped to PID 21152, which rules out a separate local proxy process owning that socket. It does not reveal what application code PID 21152 serves.

The apparent route discrepancy is likely a measurement error in the prior PowerShell check. Runtime and database identity remain unresolved independently of that correction.

## 7. Least-risk next action

Correct the route audit record using the safe property enumeration above; no API restart is warranted to fix this apparent route-reporting error. For the remaining Gate 1 identity question, request an authorized Windows administrator or service owner to perform a **read-only process inspection** of PID 21152 using an approved elevated Windows management method or approved Process Explorer. Collect only the fields needed: PID/parent PID, executable, start time, CWD, launch target and the presence/value of `CROP_PULSE_DATABASE_URL` after redaction. Never copy raw command lines or environment dumps into reports. This may identify the service owner, launch path and configured database target without changing the process.

That process inspection may still not prove the Python module file or the database actually opened by SQLAlchemy. Python module paths are not normal Windows loaded-image entries, and this application has no diagnostic endpoint for engine identity. If read-only inspection cannot prove those facts, the next step is a **separately authorized controlled maintenance window**, not an unreviewed restart.

Prerequisites for that later maintenance action:

1. Confirm the service owner and the exact intended source tree and database; do not infer the DB from the candidate SQLite file or a fallback path.
2. Establish a consistent backup and verified restore path for the identified DB before disrupting service. Gate 1E did not assess or perform backup/recovery.
3. Record PID 21152, parent/supervisor, listener, sanitized settings, current service command and the owner-approved rollback command.
4. Plan a maintenance window and prevent writes during cutover. Do not apply migrations in this identification phase.
5. Use an approved startup procedure that reports `sys.executable`, CWD, `backend.api.__file__`, sanitized effective DB identity, engine dialect and read-only revision/integrity before traffic is enabled; disable auto-create. Test on an unused loopback port against the approved DB opened read-only first.
6. Only after identity and rollback are reviewed should the owner authorize a service replacement. Preserve the old launch configuration and database; if checks fail, stop only the newly launched PID and restore the prior service command. Never overwrite/restore the database as a code rollback.

No restart, process signal, diagnostic endpoint, database connection, migration or remediation is authorized or performed here.

## Commands and checks performed

- Re-read all five listed Gate 1 through Gate 1D reports.
- `netstat -ano -p tcp` filtered to listeners on 8000, 8001, 8501, 5173 and 18001.
- `Get-Process -Id 21152,24140,11512` for process path and start time.
- `Get-CimInstance Win32_Process` with process command line excluded from output; query denied with `CimException`.
- WMIC process metadata query with command line excluded; command failed with an alias error.
- `tasklist` by target PID; returned access denied.
- `Get-Command` for Process Explorer and Handle; neither was installed.
- `GET /health` and `GET /openapi.json` on `127.0.0.1:8001`, no credentials; corrected path enumeration via `.PSObject.Properties.Name`.
- Source inspection of `backend/api.py`, `backend/db.py`, and `run_streamlit.ps1`.

All checks were read-only. No source, configuration, environment, permission, process, database or farmer data was changed or exposed. The Gate 1D result report's statement that the existing API omitted these four routes should be treated as a likely false negative from the property-check expression; the latest live response contains them.

**Verdict: BLOCKED — FURTHER AUTHORIZED DIAGNOSTICS REQUIRED**
