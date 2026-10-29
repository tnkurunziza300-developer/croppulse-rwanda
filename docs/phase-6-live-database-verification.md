# CropPulse Rwanda — Phase 6: Live Database Connection Verification

**Check date:** 2026-10-26  
**Project:** `C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda`  
**Verdict:** **Live database identity unconfirmed.**

## Conclusion

The API responding on `127.0.0.1:8001` is reachable and identifies itself as `CropPulse Rwanda Farmer Records API`, version `1.0.0`. A listener was identified as PID 21152, running `C:\Users\Student\AppData\Local\Programs\Python\Python312\python.exe`.

The responding API cannot be reliably tied to the project's `data/croppulse_phase1.sqlite3` file from the available read-only process information. The live process working directory, startup command/entry point, and process environment were not available. In particular, the process's effective `CROP_PULSE_DATABASE_URL` is unknown. The database path in source is a default conditional on both the process environment and working directory; it is not proof of the live target.

The candidate database file was checked read-only and is healthy at migration `0015_weather_alert_foundation`. This is evidence about that file only, not the database used by the live API.

## Source configuration and initialization

`backend/db.py` defines:

- `database_url()` returns the process environment's `CROP_PULSE_DATABASE_URL` when present; otherwise it returns `sqlite:///./data/croppulse_phase1.sqlite3`.
- `get_engine()` builds or reuses a SQLAlchemy engine keyed by that URL. A relative SQLite URL is resolved against the process working directory by SQLite/SQLAlchemy.
- `get_session_factory()` binds sessions to that engine, and `get_db()` opens and closes a session for a request.

`backend/api.py` exposes `backend.api:app`. The app lifespan validates runtime configuration. It calls `Base.metadata.create_all(get_engine())` only when `CROP_PULSE_AUTO_CREATE_SCHEMA=1`; production/staging validation rejects that setting. Otherwise schema changes are intended to be applied through Alembic. The `/health` handler opens the configured engine and executes `SELECT 1`; its successful response confirms database reachability for the process but does not disclose database identity.

The repository launcher `run_streamlit.ps1` starts `backend.api:app` with the project's `.venv` Python and sets its working directory to the project root. If it starts the API without an existing listener, it sets the default SQLite URL and `CROP_PULSE_AUTO_CREATE_SCHEMA=0` for that child. The live listener's executable is not this `.venv` Python. This differs from the documented launcher path, but does not establish which source copy or database the process uses.

## Checks performed

All checks were read-only. No SQL write, migration, server restart, configuration change, or application edit was performed.

| Check | Evidence/result |
|---|---|
| Resolve project root | `C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda` |
| Inspect `backend/db.py`, API lifespan, health handler, and `run_streamlit.ps1` | Confirmed environment override, relative default, conditional `create_all`, read-only health query, and documented launcher behavior described above. |
| `Get-NetTCPConnection -State Listen -LocalPort 8001` | Returned no row in this shell. |
| `netstat -ano -p tcp` filtered for `127.0.0.1:8001` | Reported a listener, PID 21152. The differing results are recorded; the PID was also accessible with `Get-Process`. |
| `Get-Process -Id 21152` | Process name `python`; executable `C:\Users\Student\AppData\Local\Programs\Python\Python312\python.exe`; start time reported as 2026-10-26 10:31 local time. This is outside the project's `.venv`. |
| `Get-CimInstance Win32_Process -Filter "ProcessId=21152"` | Did not return process metadata. No raw command line or environment values were printed. |
| `GET http://127.0.0.1:8001/health` | HTTP 200; JSON status `ok`. |
| `GET http://127.0.0.1:8001/openapi.json` | HTTP 200; title `CropPulse Rwanda Farmer Records API`, version `1.0.0`, 62 paths. OpenAPI contains no database identity. |
| Read-only SQLite check for `data/croppulse_phase1.sqlite3` | Canonical path resolved to this project copy; `PRAGMA integrity_check=ok`, zero `PRAGMA foreign_key_check` violations, Alembic revision `0015_weather_alert_foundation`. No farmer data was queried or printed. |

## Limitations and evidence assessment

The supported process queries available in this session provided the listener PID and executable path, but not its parent process, command-line arguments, current working directory, or process environment. The `Win32_Process` query returned no metadata. `Get-Process` does not expose another process's current directory or environment. The process environment may contain a database URL with credentials, so it was not accessed through unsupported memory inspection or printed.

Because the working directory and `CROP_PULSE_DATABASE_URL` for PID 21152 are unknown, it is not possible to determine whether that process resolves the relative default to this project's SQLite file, uses another SQLite file, or connects to a different database engine. The global Python executable is evidence that the documented launcher was not used in its usual `.venv` configuration; it is not evidence sufficient to identify the imported source tree or database.

The successful health request and current OpenAPI schema establish that an API responded on loopback, not that it is running this project's current source or using the candidate database. The candidate SQLite file's integrity and revision do not establish a live connection to it.

## Safest next step

An operator with access to the exact shell/service configuration that launched PID 21152 must confirm, without sharing credentials:

1. The process's Python entry point and project working directory.
2. Whether `CROP_PULSE_DATABASE_URL` was set in that process. If unset, resolve the default relative to that process's working directory. If set, identify only the database engine and sanitized target; redact username, password, tokens, and query secrets.
3. For SQLite, compare the resulting canonical absolute file path with `C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda\data\croppulse_phase1.sqlite3`.

If the original launcher context cannot be inspected, a separate approved diagnostic may be needed in the API process itself that reports only a sanitized database identity. Do not add such a route, restart the service, or alter the database as part of this read-only phase. No migration or restart approval is implied by this report.
