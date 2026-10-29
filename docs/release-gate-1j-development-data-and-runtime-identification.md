# CropPulse Rwanda — Gate 1J: Development Data Designation and Read-Only Live Runtime Identification

**Date:** 2026-10-26 (Africa/Johannesburg)  
**Project root:** `C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda`  
**Scope:** Read-only review of Gate 1F–1I evidence, current API listener/health/OpenAPI, and launch/database source. This task made documentation changes only.

## 1. Executive summary

The project owner states that current records are synthetic, sample, or test data and that they personally own and operate the development project. The owner has also explicitly designated `data/croppulse_phase1.sqlite3`, resolved from the CropPulse project root, as the intended local development database (see the dated addendum below). These are **owner-provided declarations**, not independently verified properties of every database file.

The repository separately documents this file as the local development default. Prior reports identify a different empty legacy SQLite file and historical/test databases. The owner designation resolves which file is intended for local development; it does not prove that the running API uses that file.

The API listener on `127.0.0.1:8001` was observed under PID 21152. Its health endpoint returned `ok`; its OpenAPI metadata reported title `CropPulse Rwanda Farmer Records API`, version `1.0.0`, and 62 paths, including both checked weather-alert paths. The executable path and process start time are now directly observed. Windows denied detailed process, service, and scheduled-task queries, so the parent/owner, command line, working directory, imported source module, environment, and effective database remain unverified. Health and OpenAPI do not identify the database.

No Gate 1 pass, production readiness, database selection, service action, or database action is claimed.

## 2. Development-data statement and designation scope

**Owner-provided statement in the task:** current records are synthetic, sample, or test data; the project owner personally owns and operates this development project. This is accepted here as the owner's declaration. No application rows were queried to test it.

**Repository evidence:** `backend/db.py`, `.env.example`, `run_streamlit.ps1`, and setup documentation name `sqlite:///./data/croppulse_phase1.sqlite3` as the fallback/local development URL. Relative paths resolve from the API process working directory. The setup guide warns that local SQLite is not a production backup strategy.

**Designation boundary:** the owner explicitly designates `data/croppulse_phase1.sqlite3` for *local development only*. The prior inventory showed that file at revision `0015_weather_alert_foundation` with integrity `ok`, but those checks establish file structure at the inventory time only. They do not prove runtime use or content provenance.

This designation, if confirmed, does not prove that PID 21152 uses the file and does not authorize replacing, resetting, copying over, migrating, deleting, or otherwise altering any database.

## 3. Evidence table

| Source/check | Observation | Confidence | Limitation |
|---|---|---|---|
| Owner statement supplied in the Gate 1J task and Gate 1K decision | Owner says records are synthetic/sample/test, owns/operates this development project, and designates `data/croppulse_phase1.sqlite3` as the intended local development DB. | High that this is the owner's declared position. | Not independently verified against database contents and does not establish live API use. |
| `backend/db.py`, `.env.example`, `docs/react-app-setup.md`, `run_streamlit.ps1` | `data/croppulse_phase1.sqlite3` is the documented fallback/local setup URL. | Direct repository evidence. | Process environment can override it and a relative URL depends on process CWD; a launcher can reuse an existing listener without configuring it. |
| Gate 1G/H/I reports and read-only candidate inventory recorded there | Main candidate was recorded at 19,402,752 bytes, revision `0015`, 24 tables, integrity `ok`; `data/croppulse_local.sqlite3` was recorded as empty/legacy; historical snapshots and synthetic tests also exist. | Direct evidence for inventory time and documented roles. | No current re-read of DB files was needed or performed for Gate 1J; metadata is not provenance or live connection evidence. |
| `netstat -ano -p tcp` filtered to API listener | `127.0.0.1:8001` was listening under PID 21152. | Direct observation at check time. | Listener ownership does not establish process source/runtime/database. |
| `Get-Process -Id 21152` | Image name `python`; executable `C:\Users\Student\AppData\Local\Programs\Python\Python312\python.exe`; start time `2026-10-26 10:31:09` local time. | Direct observation at check time. | This is the Python executable path, not the imported project source path or effective environment/database configuration. |
| `Get-CimInstance Win32_Process -Filter 'ProcessId=21152'` | Target process metadata query returned access denied/unavailable. | Direct observation of the access limitation. | Parent PID, full executable path, command line, and other CIM fields could not be collected. No raw command line was printed. |
| `GET http://127.0.0.1:8001/health` | Response status field `ok`. | Direct read-only HTTP observation. | Health checks readiness only; it does not reveal database identity. |
| `GET http://127.0.0.1:8001/openapi.json` | API title/version reported; 62 paths; `/v1/weather/alert-preferences` and `/v1/weather/alerts` were present. | Direct read-only HTTP observation. | Compatible routes/title do not prove imported source path, process configuration, or database. Earlier route discrepancy is not evidence of DB identity. |
| `docs/release-gate-1f-live-api-identity.md` and Gate 1G/H | Prior checks could not establish PID 21152's CWD, launch target, imported module, environment, or effective SQLAlchemy target. | Existing documented findings. | No new escalation or service change was performed. |

## 4. Live API identity findings

**Directly observed:** the API listener address/PID, the `python.exe` process image name/start time, health response, and OpenAPI title/version/path set listed above.

**Repository documentation:** the project launcher uses the project `.venv` and local DB default when it starts a new API. If port 8001 already has a listener that passes its checks, the launcher reuses it. The API source reads `CROP_PULSE_DATABASE_URL` or falls back to the relative SQLite URL. These are source/launcher behaviors, not evidence about PID 21152's inherited environment.

**Unknown/inaccessible:** whether PID 21152 uses the project virtual environment, parent/supervisor, command line, CWD, source tree/module file, process environment, SQLAlchemy engine target, and absolute DB path. No existing safe diagnostic endpoint exposes that identity. No intrusive process attachment or diagnostic code was used.

## 5. Database identity finding

**Unverified.** Nothing in this read-only investigation establishes which database PID 21152 currently uses. In particular, the health check, OpenAPI routes, source default, owner declaration about synthetic data, and the prior candidate file's integrity/revision do not prove that relationship. No database connection was made during Gate 1J. No database file was opened, copied, or modified during this task.

The live database and the intended development database are separate questions. The owner can designate a local development file without that file being the current listener's target; conversely, observing a runtime target would not by itself establish the organization's intended authoritative production store.

## 6. Remaining release blockers

- Owner has not explicitly confirmed the exact canonical file intended as the local development DB based on project history.
- PID 21152's source/runtime/database identity remains unknown due process metadata access limits.
- Protected backup and real-data isolated restore evidence remain absent; the Phase 4 rehearsal used synthetic data and had unresolved ACL protection.
- Production database, host, and deployment identity remain unspecified. No Gate 1 pass or production readiness is supported.

## 7. Bounded next action and controlled verification plan

**Original next action (completed by the Gate 1K owner decision below):** obtain the project owner's explicit confirmation of the intended local development file. That confirmation resolves only the development designation, not live API identity.

If the live runtime still needs identification after that confirmation:

1. Preserve PID 21152 and all database files. Have an authorized Windows operator perform non-invasive process/service inspection and collect only sanitized fields. If the live SQLAlchemy target still cannot be proven, leave it unverified.
2. Before any proposed replacement, obtain a separate maintenance authorization, confirm process ownership and exact source/runtime, and establish a protected backup plus isolated restore of the specifically owner-approved target. The current synthetic restore does not satisfy this prerequisite.
3. For any future diagnostic launch, use an isolated synthetic test DB only, the intended project virtual environment and explicit project directory, with schema creation and migrations disabled. Verify executable, source module, CWD, listener PID, canonical DB path, revision, and read-only integrity before health/OpenAPI checks. Do not attach two API writers to a live SQLite database.
4. Stop if ownership, target path, backup provenance, restore, or rollback cannot be established. Any service replacement or production database operation requires separate explicit approval.

## 8. Changes made

Documentation only: created `docs/release-gate-1j-development-data-and-runtime-identification.md`. No source, configuration, launch script, dependency, permission, database, account, or service was changed. No tests were run because this is an audit-only task and they are not needed to document the read-only observations. The existing API listener remained running; no database files were accessed or modified during this task.

## Gate 1K addendum — intended development database decision

Reviewed Gate 1H, 1I, and 1J along with `backend/db.py`, `.env.example`, `run_streamlit.ps1`, `docs/react-app-setup.md`, `docs/backend-phase-1.md`, and migration filenames through `0015_weather_alert_foundation`.

**Repository conclusion:** the repository documents `data/croppulse_phase1.sqlite3`, resolved from the project root when launched there without an environment override, as the default local development database. The migration/setup instructions use that path. `data/croppulse_local.sqlite3` is documented as a legacy empty database. Historical `.backups/` and `data/backups/` files are migration snapshots; `.test-runtime/` includes synthetic test databases. These documented roles support the default's local-development purpose but do not record the owner's explicit selection of that exact file from project history.

**Separate, unchanged finding:** the documented default does not identify PID 21152's database. Its working directory, runtime override, imported source, and effective SQLAlchemy target remain unverified. This gate did not reopen any database, query records, retry restricted process access, call the API, or change the running service.

**The owner confirmation was pending when this section was first written; the Gate 1K decision below resolves it.**

> The project owner designates `data/croppulse_phase1.sqlite3`, resolved from the CropPulse project root, as the intended local development database.

This confirmation concerns local development only; it does not designate a production or authoritative farmer-record database and does not authorize reset, replacement, migration, deletion, or service restart.

**Exact next action:** no further owner clarification is needed for the local-development designation. To establish which database the current API uses, an authorized service owner/operator must provide sanitized runtime evidence linking PID 21152 to its source, working directory, effective configuration, and active SQLAlchemy target. Keep Gate 1 blocked until that evidence exists.

## Gate 1J runtime addendum — 2026-10-26

### Owner decision

The project owner explicitly designates **`data/croppulse_phase1.sqlite3`, resolved from the CropPulse project root, as the intended local development database.** This records the exact owner decision supplied for this addendum. It is limited to local development and does not establish that the current listener uses this file or designate a production/authoritative farmer-record database. It does not authorize database or service changes.

### Read-only evidence table

| Question | Evidence source and observation | Classification / confidence / limitation | Next action |
|---|---|---|---|
| Is the intended local development DB explicitly designated? | Owner explicitly designated `data/croppulse_phase1.sqlite3` resolved from project root. Repository setup also documents this as the default/local URL. | **Direct owner decision**, high confidence for intended local development. Not a live runtime finding. | None for the local-development designation. |
| What currently owns API port 8001? | `netstat -ano -p tcp` showed `127.0.0.1:8001` LISTENING with PID 21152. `Get-Process -Id 21152` reported process name `python`, executable `C:\Users\Student\AppData\Local\Programs\Python\Python312\python.exe`, start time `2026-10-26 10:31:09` local time. | **Directly observed**, high confidence at check time for listener/PID and process image path/start time. | Process owner/supervisor linkage remains unavailable. |
| Was full process metadata accessible? | `tasklist /v /fi "PID eq 21152"` returned `Access denied`; `Get-CimInstance Win32_Process -Filter 'ProcessId=21152'` was already recorded as access denied in prior gates. | **Directly observed limitation.** Command line, parent PID, and any process owner field remain unknown. No access restriction was bypassed. | Service owner with authorized access may provide sanitized evidence if needed. |
| Did service or scheduled-task records link the listener? | `Get-CimInstance Win32_Service -Filter 'ProcessId=21152'` and `Get-ScheduledTask` returned access denied/unavailable. Prior Gate 1 reports say service queries did not associate a service with PID 21152. | **Unknown**, low confidence for ruling out service/task launch because the queries were inaccessible. | Do not infer launch method. Authorized operator can review the supervisor records. |
| Is the actual application source directory identified? | Current project launcher/docs run `backend.api:app` from the project root when launching a new API, but reuse an existing ready listener. The running process command line/imported module could not be read. | **Documented launch behavior**, not proof of PID 21152 source. | Unverified; requires authorized runtime evidence or separately approved controlled procedure. |
| Is runtime configuration identified? | `backend.db` reads `CROP_PULSE_DATABASE_URL` or uses a relative default. Live process environment and working directory were not accessible. | **Source fact; live values unknown.** | Unverified. |
| Is the active database target conclusively identified? | No database URL/engine target is exposed by the accessible process metadata or documented read-only API diagnostics. No database was opened during this addendum. | **Unknown.** | Do not infer from the owner designation, launcher, or candidate file. |
| Is PID 21152 proven to use the owner-designated development DB? | No source/CWD/environment/engine connection evidence links PID 21152 to the file. | **No — unverified.** | Keep live database identity blocked. |

### Checks performed and preservation

- Read Gate 1H, Gate 1I, this report, `backend/db.py`, `.env.example`, `run_streamlit.ps1`, `docs/react-app-setup.md`, `docs/backend-phase-1.md`, and migration filenames. These confirm intended local default/documentation only.
- Read-only commands: `netstat -ano -p tcp`; `Get-Process -Id 21152`; `tasklist /v /fi "PID eq 21152"`; `Get-CimInstance Win32_Process -Filter 'ProcessId=21152'` (the denial was already recorded previously); `Get-CimInstance Win32_Service -Filter 'ProcessId=21152'`; and `Get-ScheduledTask` (last two returned access denied/unavailable).
- No API HTTP requests were made for this addendum; prior health/OpenAPI results were not repeated.
- No tests or Alembic commands were run. No database was opened, queried, copied, backed up, or changed. No service, port, environment, source, or configuration was changed. The listener was not stopped, restarted, or replaced.

### Concrete next action

If establishing live runtime identity is still required, the service owner or Windows operator who has authorized read access should supply sanitized evidence linking PID 21152 to its supervisor/launch target, source directory, working directory, Python executable/environment, and effective database backend/target. If those facts cannot be obtained without modifying the process, preserve the service and seek a separately approved maintenance window with backup/restore and rollback prerequisites. Do not launch a second API against the designated development database or infer that the existing PID uses it.

## Verdict

**DEVELOPMENT DATABASE DESIGNATED — LIVE DATABASE IDENTITY UNVERIFIED**

The owner has designated the local development file. The current API's source and active database remain unverified; Gate 1 has not passed.
