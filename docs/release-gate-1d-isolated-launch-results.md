# CropPulse Rwanda — Gate 1D: Isolated API Launch Results

**Date:** 2026-10-26 (Africa/Johannesburg)  
**Project root:** `C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda`  
**Authorization scope:** One isolated, read-only local API test on `127.0.0.1:18001`, using the exact synthetic test DB named in the Gate 1D preflight plan. No other service, production setting, migration or database was authorized or changed.

## Summary

The isolated API started as PID `32648` using the project virtual-environment Python, imported `backend/api.py` from this project, and opened the exact approved synthetic SQLite database in read-only mode. Its health endpoint returned `ok`; OpenAPI returned HTTP 200 with 62 paths, including all four weather-alert routes defined in current source. The existing API on port 8001 did not expose those four paths during the same check.

The isolated server was stopped with Ctrl+C in its launch session. Its PID and port are no longer active. The original listeners remained present with unchanged PIDs. The isolated DB's size and SHA-256 remained unchanged, its revision and integrity remained valid, and no WAL/SHM sidecars appeared.

**Gate 1 remains BLOCKED.** The isolated test proves behavior for a controlled process; it does not identify the source, configuration or database of the existing API on port 8001.

## Exact verified test database

`C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda\.test-runtime\phase4-recovery-3f5e0732384149d7b6201b3677958bc4\isolated-test.sqlite3`

The Gate 1D preflight report and Phase 4/5 recovery evidence identify this as a disposable database containing synthetic test data only. It is not the candidate `data/croppulse_phase1.sqlite3`. The isolated test connection used SQLite `mode=ro`.

## Commands and checks performed

### 1. Re-read plan and confirm process state

Read `docs/release-gate-1d-isolated-launch-preflight.md`, including the exact approved test database path, startup hook behavior, and launch/rollback instructions.

Immediately before launch, ran PowerShell checks equivalent to:

```powershell
Get-NetTCPConnection -State Listen -LocalPort 18001 -ErrorAction SilentlyContinue
netstat -ano -p tcp | Select-String '8001|8501|5173|18001'
Get-Process -Id 21152,24140,11512 -ErrorAction SilentlyContinue |
  Select-Object Id,ProcessName,Path,StartTime
```

Port 18001 was free. Existing listeners were:

| Service | Listener | PID | OS-reported executable |
|---|---|---:|---|
| Existing API | `127.0.0.1:8001` | 21152 | Machine-level Python 3.12 path |
| Streamlit | `0.0.0.0:8501` | 24140 | Machine-level Python 3.12 path |
| Vite | `127.0.0.1:5173` | 11512 | Machine-level Node path |

### 2. Confirm no startup schema or migration operation

Re-inspected `backend/api.py` before launch. Its lifespan validates runtime settings and invokes `Base.metadata.create_all(get_engine())` only if `CROP_PULSE_AUTO_CREATE_SCHEMA` is exactly `1`. The test process set it to `0`. The API lifespan contains no Alembic migration call, and no migration command was run. The `/health` handler executes `SELECT 1`. SQLite was configured with `mode=ro`, so application DB writes would fail even if an unexpected write path were reached.

### 3. Preflight and launch command

Executed a PowerShell here-string into the project's interpreter from the project root:

```powershell
$root = (Resolve-Path '.').Path
$python = Join-Path $root '.venv\Scripts\python.exe'
$env:PYTHONDONTWRITEBYTECODE = '1'
@'
import os, sys, secrets, hashlib, socket
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.engine import URL
root = Path(r'C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda').resolve(strict=True)
approved = Path(r'C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda\.test-runtime\phase4-recovery-3f5e0732384149d7b6201b3677958bc4\isolated-test.sqlite3').resolve(strict=True)
candidate = (root / 'data' / 'croppulse_phase1.sqlite3').resolve()
expected_python = (root / '.venv' / 'Scripts' / 'python.exe').resolve()
if Path(sys.executable).resolve() != expected_python: raise SystemExit('ABORT: wrong Python executable')
if Path.cwd().resolve() != root: raise SystemExit('ABORT: wrong working directory')
if approved == candidate or not approved.is_file(): raise SystemExit('ABORT: target is not the verified isolated test DB')
if approved.stat().st_size == 0: raise SystemExit('ABORT: test database is empty')
with socket.socket() as probe:
    if probe.connect_ex(('127.0.0.1', 18001)) == 0: raise SystemExit('ABORT: port 18001 has a listener')
os.environ['CROP_PULSE_ENVIRONMENT'] = 'test'
os.environ['CROP_PULSE_AUTO_CREATE_SCHEMA'] = '0'
os.environ['CROP_PULSE_SECRET_KEY'] = secrets.token_urlsafe(48)
readonly_url = URL.create('sqlite+pysqlite', database=f'file:{approved.as_posix()}', query={'mode':'ro','uri':'true'}).render_as_string(hide_password=True)
os.environ['CROP_PULSE_DATABASE_URL'] = readonly_url
import backend.api as api
from backend.db import get_engine
from alembic.config import Config
from alembic.script import ScriptDirectory
module_path = Path(api.__file__).resolve()
if module_path != (root / 'backend' / 'api.py').resolve(): raise SystemExit('ABORT: imported API source path mismatch')
head = ScriptDirectory.from_config(Config(str(root / 'alembic.ini'))).get_current_head()
if head != '0015_weather_alert_foundation': raise SystemExit('ABORT: source migration head changed')
engine = get_engine()
if engine.dialect.name != 'sqlite': raise SystemExit('ABORT: unexpected database dialect')
with engine.connect() as connection:
    opened = Path(connection.execute(text('PRAGMA database_list')).one()[2]).resolve(strict=True)
    revision = connection.execute(text('SELECT version_num FROM alembic_version')).scalar_one()
    integrity = connection.execute(text('PRAGMA integrity_check')).scalar_one()
    fk_count = len(connection.execute(text('PRAGMA foreign_key_check')).fetchall())
    select_one = connection.execute(text('SELECT 1')).scalar_one()
    journal_mode = connection.execute(text('PRAGMA journal_mode')).scalar_one()
if opened != approved: raise SystemExit('ABORT: configured engine opened a different file')
if revision != head or integrity != 'ok' or fk_count != 0 or select_one != 1: raise SystemExit('ABORT: database revision or integrity check failed')
sidecars = {suffix: Path(str(approved)+suffix).exists() for suffix in ('-wal','-shm')}
digest_before = hashlib.sha256(approved.read_bytes()).hexdigest()
print('PREFLIGHT PASSED', flush=True)
print('test_pid:', os.getpid(), flush=True)
print('python:', Path(sys.executable).resolve(), flush=True)
print('cwd:', Path.cwd().resolve(), flush=True)
print('api_module:', module_path, flush=True)
print('database:', opened, flush=True)
print('database_bytes:', approved.stat().st_size, flush=True)
print('database_sha256_before:', digest_before, flush=True)
print('revision:', revision, flush=True)
print('migration_head:', head, flush=True)
print('integrity:', integrity, flush=True)
print('foreign_key_violations:', fk_count, flush=True)
print('select_1:', select_one, flush=True)
print('journal_mode:', journal_mode, flush=True)
print('wal_shm_preexisting:', sidecars, flush=True)
print('auto_create_schema:', os.environ['CROP_PULSE_AUTO_CREATE_SCHEMA'], flush=True)
print('migration_command: none', flush=True)
print('starting isolated API on 127.0.0.1:18001 with read-only SQLite URI', flush=True)
import uvicorn
uvicorn.run(api.app, host='127.0.0.1', port=18001, access_log=False, log_level='warning')
'@ | & $python -B -
```

The Python code was executed as one here-string (not as a saved source file). The full checks completed before `uvicorn.run`; any mismatched executable, CWD, module path, database path, migration head, revision, integrity result or port availability terminated before server start. The ephemeral signing key was generated in process memory and never printed or persisted.

Preflight output:

| Identity/check | Result |
|---|---|
| Test process PID | `32648` |
| Python `sys.executable` | `C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda\.venv\Scripts\python.exe` |
| Working directory | `C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda` |
| Imported API module | `C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda\backend\api.py` |
| Bound address | `127.0.0.1:18001` |
| Effective SQLAlchemy file | Exact approved synthetic DB path above |
| Source migration head | `0015_weather_alert_foundation` |
| DB Alembic revision | `0015_weather_alert_foundation` |
| DB size before | 475,136 bytes |
| DB SHA-256 before | `5b455fff8548712c8601e2f5576011afc36825b40a15c8239c9dd11b521c7588` |
| SQLite journal mode | `delete` |
| WAL / SHM before | Neither existed |
| `PRAGMA integrity_check` | `ok` |
| `PRAGMA foreign_key_check` | 0 violations |
| Read-only `SELECT 1` | `1` |
| Auto schema creation | Disabled (`0`) |
| Migration command | None |

Windows `Get-Process` reports the executable image for PID 32648 as the machine-level Python 3.12 binary. The same process printed `sys.executable` as the project's `.venv\Scripts\python.exe`; the controlled command invoked that exact virtual-environment executable, and the preflight asserted the same `sys.executable`. On Windows the venv launcher may resolve to the base interpreter image; the reported Python runtime path and project environment are the evidence used here.

### 4. HTTP and route verification

Sent unauthenticated GET requests only:

```powershell
Invoke-RestMethod 'http://127.0.0.1:18001/health' -TimeoutSec 10
Invoke-RestMethod 'http://127.0.0.1:18001/openapi.json' -TimeoutSec 10
```

Health returned HTTP 200 with `status: ok`. OpenAPI returned HTTP 200, title `CropPulse Rwanda Farmer Records API`, version `1.0.0`, 62 paths.

The controlled instance's OpenAPI paths matched current route declarations:

| Method | Path | Isolated API 18001 | Current source |
|---|---|---|---|
| GET | `/v1/weather/alert-preferences` | Present | Present |
| PUT | `/v1/weather/alert-preferences/{field_id}` | Present | Present |
| GET | `/v1/weather/alerts` | Present | Present |
| PATCH | `/v1/weather/alerts/{alert_id}/status` | Present | Present |

For comparison, GET `/openapi.json` at the existing `127.0.0.1:8001` returned a schema in which all four paths were absent. This confirms the discrepancy is between that existing process and the controlled current-project process. It does not establish why: the existing process's source tree, launch context and DB remain unknown.

### 5. Stop and post-test verification

Stopped the foreground test server with Ctrl+C in its launch session; no `Stop-Process` call was needed. The Python process/session exited. Post-test read-only checks confirmed:

- PID `32648` was no longer running and port 18001 had no listener.
- Original listener PIDs 21152, 24140 and 11512 were still present on 8001, 8501 and 5173 respectively.
- Test DB remained 475,136 bytes with SHA-256 `5b455fff8548712c8601e2f5576011afc36825b40a15c8239c9dd11b521c7588`.
- No `-wal` or `-shm` file appeared.
- Read-only post-check returned revision `0015_weather_alert_foundation`, integrity `ok`, and zero foreign-key violations.

No farmer rows, credentials or private records were queried or displayed. No source file, configuration file, frontend build, candidate database, test database content, migration, existing process or existing listener was changed.

## Results and unresolved risks

**Isolated test:** Passed for source/interpreter/CWD/database identity, read-only DB integrity, health, OpenAPI and cleanup. The OpenAPI route check proves the test server used a source build exposing the expected alert endpoints.

**Existing API:** Still unidentified. PID 21152 continues to run using the global Python image; its project source, CWD, runtime environment and effective database are not established. Its current OpenAPI omits the four alert routes. No conclusion is made about whether its database is the candidate SQLite file.

**Gate 1:** **BLOCKED, not passed.** Passing this isolated test is not evidence linking the existing deployment-intended API process to the intended source and database. The next step is to obtain approved process-level evidence or a separately authorized controlled maintenance restart after the intended live database and backup/recovery plan are established. No production restart, migration, deployment or Gate 2 action is authorized by this isolated-test approval.
