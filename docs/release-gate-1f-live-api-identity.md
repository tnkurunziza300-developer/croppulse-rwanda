# CropPulse Rwanda — Gate 1F: Live API Process and Database Identity

**Date:** 2026-10-26 (Africa/Johannesburg)  
**Project root:** `C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda`  
**Scope:** Read-only process, launcher, history, endpoint and database-configuration investigation. No process was signaled; no source, environment, configuration or database was modified.  
**Verdict: BLOCKED — PROCESS EVIDENCE INSUFFICIENT**

## Executive finding

At 2026-10-26 12:39 +02:00, PID `21152` still owned `127.0.0.1:8001`. `Get-Process` identified a Python process and its OS-reported executable image path and start time. Available Windows process/service queries did not provide its parent, ancestry, command line, working directory or environment. Existing health/OpenAPI endpoints provide no database identity. There is therefore no conclusive link from PID 21152 to a source tree, effective runtime configuration or database.

The current API's alert routes were found present in the corrected OpenAPI inspection documented in [Gate 1E](release-gate-1e-live-api-discrepancy.md). Gate 1E explains that the earlier missing-route finding used an incorrect PowerShell property lookup. Route availability does not establish process or database identity.

## 1. Reconfirmed listener and executable evidence

Commands:

```powershell
netstat -ano -p tcp | Where-Object {
  $_ -match 'LISTENING' -and $_ -match ':8001\s'
}
Get-Process -Id 21152 | Select-Object Id,ProcessName,Path,StartTime
```

Result at 12:39 +02:00:

| Property | Observation |
|---|---|
| Listener | `127.0.0.1:8001` |
| PID | `21152` |
| Process name | `python` |
| OS-reported executable image | `C:\Users\Student\AppData\Local\Programs\Python\Python312\python.exe` |
| Process start | 2026-10-26 10:31:09 |

This executable path is an OS image-path observation only. Gate 1D showed that invoking the project `.venv\Scripts\python.exe` can still result in `Get-Process.Path` reporting the base Python image path on this host. It does not prove that PID 21152 is outside the project venv.

## 2. Windows process, ancestry, service and launcher evidence

Read-only methods attempted:

- `Get-Process` provided PID, name, image path and start time, but no process CWD or parent property.
- `Get-CimInstance Win32_Process` for PID 21152 failed with `CimException` / access denied. The query was restricted to non-command-line metadata; no raw command line was requested for output.
- `tasklist /fi "PID eq 21152" /fo list` returned access denied.
- `wmic process ... get ProcessId,ParentProcessId,ExecutablePath,CreationDate /format:list` failed with an alias error.
- `Get-CimInstance Win32_Service -Filter 'ProcessId=21152'` failed with `CimException`; `sc.exe queryex` did not identify a service association. A Windows service relationship is therefore not established.
- Process Explorer and Handle were not installed. No debugger, memory dump, process injection or signaling was attempted.

Consequently, PID 21152's parent PID, process ancestry, launch command, working directory, inherited environment and Python import path remain **unverified**.

### Launcher, shell history and logs

Inspected `run_streamlit.ps1`. It uses `$PSScriptRoot` as the project root and `.venv\Scripts\python.exe`. If it starts an API, it launches `backend.api:app` with that working directory and sets `CROP_PULSE_DATABASE_URL` to the relative local SQLite URL with `CROP_PULSE_AUTO_CREATE_SCHEMA=0`. If port 8001 already has a listener, it checks a limited set of health/CSRF/CORS/auth/farm/handoff behavior and reuses it; it cannot change or report that existing process's environment or DB. The current script's readiness check does not prove process identity.

The current user's PowerShell history was searched in memory only for launch-related tokens. The output contained only aggregate flags: it includes references to Uvicorn, `backend.api`, port 8001, and `CROP_PULSE_DATABASE_URL`; it did not include a `run_streamlit` command. No history line was emitted. PSReadLine history entries here provide no usable timestamp/process association, so these commands cannot be attributed to PID 21152; the database override's value was not displayed.

The launcher's documented temp logs `croppulse-api-8001.log` and `croppulse-api-8001-error.log` exist but their last write was 2026-10-20, before PID 21152's recorded 2026-10-26 start. The stdout log is empty; the stderr log is 411 bytes and has no PID 21152 reference. Only metadata and boolean pattern matches were reported; log contents were not printed. These logs do not identify the current process.

## 3. Source, working directory and database configuration

Inspected `backend/db.py`, `backend/migrations/env.py`, `run_streamlit.ps1`, and project launch documentation.

`backend.db.database_url()` returns `os.environ['CROP_PULSE_DATABASE_URL']` when set; otherwise it returns `sqlite:///./data/croppulse_phase1.sqlite3`. For a relative SQLite URL, SQLAlchemy resolves `./data/croppulse_phase1.sqlite3` relative to the API process's current working directory. Thus, only if the process starts with the project root as CWD and leaves the URL unset would the fallback resolve to this project copy's `data/croppulse_phase1.sqlite3`. A relative override is likewise CWD-dependent; an absolute SQLite URL identifies its file directly. PostgreSQL URLs identify a server/database rather than a local file and must be sanitized before reporting.

No backend `load_dotenv` mechanism was identified in inspected source. A process can inherit environment values from its terminal, IDE, service manager or launcher. The launcher assigns the local DB URL only in the branch where it launches a new API; the reuse branch leaves the existing process untouched. No fact available here reveals PID 21152's effective `CROP_PULSE_DATABASE_URL` or CWD, so its DB cannot be inferred from the source default or candidate database.

`get_engine()` lazily constructs an engine from the URL current in the process environment; `/health` connects and runs `SELECT 1`. That confirms connectivity only. No existing supported diagnostic route reports the engine URL, canonical SQLite filename, server/database identity or Alembic revision. `/openapi.json` reveals route/schema metadata only. No API database connection or farmer table was queried for this report.

The imported Python module path cannot be recovered through ordinary Windows executable-image metadata: Python source modules are not native executable images. The current API has no safe source-path/DB-identity endpoint. Reading process memory or injecting diagnostic code would violate the task's constraints and was not attempted.

## 4. Verified facts versus hypotheses

### Verified

1. PID 21152 currently owns the loopback listener `127.0.0.1:8001`.
2. It is a Python process with the recorded OS image path and start time.
3. The current source selects DB URL from `CROP_PULSE_DATABASE_URL`, otherwise from a relative SQLite default.
4. A relative SQLite URL depends on process CWD.
5. The launcher sets an explicit local DB URL and project CWD only when it starts the API; when it reuses a listener, it does not configure that listener.
6. Existing health/OpenAPI diagnostics do not disclose DB identity or the running module file.
7. Project shell history and launcher log evidence do not tie a particular launch command or DB target to PID 21152.
8. No database identity is confirmed for PID 21152.

### Unverified hypotheses

- PID 21152 may have been started by `run_streamlit.ps1`, another PowerShell/IDE terminal, a different project checkout, or another supervisor. The current evidence does not discriminate among them.
- It may use the project's venv, because the isolated venv-launched process showed the same OS-reported image path; it may also use the global environment. `sys.executable` for PID 21152 was not obtainable.
- It may use the default SQLite file, a different relative/absolute SQLite file, or a PostgreSQL database. No effective runtime URL or CWD was established.
- The current OpenAPI route set is compatible with current project source but does not prove the process imported that source; another build could expose the same routes.

## 5. Recommended next action: controlled maintenance-window identity check

Start with an authorized Windows administrator/service owner performing read-only process inspection, if their privileges allow. Inspect only PID 21152; obtain parent, executable, start time, CWD and launch target. If environment inspection is available, extract only the DB target and redact userinfo, passwords, query secrets and tokens. Do not dump environment blocks or command lines into reports. This may narrow the configuration without disrupting service, but still may not prove which Python module file or database the live SQLAlchemy engine actually opened.

If those facts remain unavailable, use a separately approved maintenance window. Required sequence:

1. Confirm the service owner and which source tree and database are intended. Do not assume the candidate SQLite file is live.
2. Identify the database using approved process/service configuration and establish a consistent backup plus successful isolated restore before service interruption. Do not run a migration as part of identity diagnosis.
3. Record PID 21152, listener, owner/supervisor, sanitized launch settings, CWD/entry point if known, and the exact rollback command. Agree on a maintenance window and pause writes through the owner.
4. Preserve the existing launch configuration. Start a controlled process from the approved project root and venv on an unused loopback port, with an explicit, owner-confirmed database URL and auto-create disabled. First open the DB read-only and report `sys.executable`, `sys.prefix`, CWD, `backend.api.__file__`, sanitized target identity, engine dialect, revision and integrity; abort before traffic on any mismatch.
5. Verify health/OpenAPI from that identified process, without farmer-data queries or writes. Do not route users until owner review.
6. Only with separate approval, replace the old listener. If checks fail, stop only the newly launched PID, restore the preserved prior service command/configuration, and verify the original listener returns. Do not restore/overwrite a database as a code rollback. If any writes occurred, have the owner assess consistency before reversal.

This procedure is a recommendation only. No maintenance window, backup, restart, process inspection escalation or database operation was performed or authorized by Gate 1F.

## Commands and checks performed

- `netstat -ano -p tcp` filtered to the 8001 LISTENING row.
- `Get-Process -Id 21152` for non-secret process metadata.
- `Get-CimInstance Win32_Process` / `Win32_Service` with command-line data excluded; access denied.
- `tasklist` for the target PID; access denied.
- WMIC and `sc.exe queryex` read-only metadata attempts; WMIC alias error and no service association.
- `Get-Command` for Process Explorer and Handle.
- Safe aggregate-only PowerShell history search and launcher-log metadata/pattern check; no raw history or logs emitted.
- Source/document inspection of `backend/db.py`, `backend/migrations/env.py`, `run_streamlit.ps1`, and the Gate 1E report.

No authenticated API request, SQL connection, database write, migration, service action, process signal, permission change, source/configuration edit or secret disclosure occurred.

**Verdict: BLOCKED — PROCESS EVIDENCE INSUFFICIENT**
