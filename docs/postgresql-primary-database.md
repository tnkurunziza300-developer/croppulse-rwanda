# PostgreSQL primary database

**Status:** PostgreSQL-first runtime configuration is implemented in source. The operator reports that a read-only local diagnostic verified the temporary API against `croppulse_staging_pg` using PostgreSQL/`psycopg`, schema `public`, at revision `0020_agronomy_review_workflow`. This report does not independently re-query the live process.

## Runtime architecture

```text
React browser ──HTTPS/API requests──> FastAPI ──SQLAlchemy──> PostgreSQL
Streamlit server ──authenticated API requests──> FastAPI ──same engine──> PostgreSQL
Background worker: none found in this repository
Reports: account-backed views use FastAPI; descriptive source datasets remain versioned files
```

FastAPI owns the one cached SQLAlchemy engine and session factory in `backend/db.py`. API routes use the shared `get_db()` dependency; `/health` and startup readiness use the same `get_engine()`. Alembic resolves the same `CROP_PULSE_DATABASE_URL` through `backend/migrations/env.py`. React has no database driver and communicates with FastAPI. Streamlit uses `backend/client.py` to call FastAPI; it does not connect directly to a database. No separate scheduled/background database service was found.

| Component | Database path | Verification status |
|---|---|---|
| FastAPI | Central SQLAlchemy engine configured by `CROP_PULSE_DATABASE_URL` | Source wiring implemented; current process/database identity not live-verified |
| React | FastAPI API only | Source uses API client; no database driver found in frontend |
| Streamlit | FastAPI API only | Source uses shared API client; browser/DB integration not live-verified |
| Background services | None found | No worker or scheduled DB process identified |
| Account-backed reports | FastAPI queries | Source path shares the central session dependency; no live cross-component comparison performed |
| External descriptive datasets | Versioned files, including NISR CSV | Kept outside PostgreSQL; provenance and packaging terms remain separate release checks |

## Database configuration

Every application runtime must receive `CROP_PULSE_DATABASE_URL` using the `postgresql+psycopg` driver. Missing configuration and SQLite/other database backends fail closed; there is no default SQLite application URL. Credentials belong in a private process environment or secret manager, never in source, `VITE_*` variables, command history, logs, or reports. The example file contains placeholders only.

The only application-code SQLite path is an isolated test adapter requiring all of:

- `CROP_PULSE_ENVIRONMENT=test`
- an explicit unique `CROP_PULSE_DATABASE_URL`
- `CROP_PULSE_ALLOW_SQLITE_TEST_DATABASE=1`
- a URL outside the historical `data/` directory

The adapter does not make the historical SQLite files eligible application targets. The read-only runtime diagnostics utility can inspect explicitly supplied SQLite files; that is a separate maintenance function, not an application fallback. SQLite migration/API tests use temporary synthetic databases. Historical SQLite files and backups have not been changed or imported.

`run_streamlit.ps1` validates that the configured URL resolves to PostgreSQL before starting the API. FastAPI startup validates security and database configuration, rejects automatic schema creation, and executes a read-only `SELECT 1` before serving requests. API database sessions are closed through the shared dependency. SQLAlchemy's PostgreSQL `QueuePool` is shared per normalized URL with `pool_pre_ping`; deployment-specific pool sizing and worker counts still need capacity testing.

## Schema and migration management

The repository migration head is `0020_agronomy_review_workflow`. API startup does not create tables. Apply only reviewed Alembic migrations using the same private `CROP_PULSE_DATABASE_URL`, after a protected backup and explicit approval for a database change. Do not run `alembic upgrade` against the existing staging database as part of local code verification. The PostgreSQL auto-generated reviewer foreign-key name from migration `0003` is handled by inspecting the actual reflected constraint in migration `0005`; SQLite's unnamed reflected constraint receives the configured naming-convention name. This has SQLite migration regression coverage, but has not been executed against PostgreSQL here.

## Release and preservation boundaries

- Existing PostgreSQL records and revision are not touched by this source-only implementation.
- No SQLite records were imported; historical SQLite files were not opened or changed for this work.
- Existing NISR and weather source files remain external data assets. `data/verified/MANIFEST.json` is tracked, but `data/verified/nisr_sas_2023_2026.csv` is ignored by Git; a clean checkout or release therefore lacks that CSV unless a separately approved packaging step supplies it. Do not force-add, fabricate, or silently omit it: confirm reuse terms, package the exact source file, and verify its existing manifest hash before release.
- No source data was fabricated or silently substituted.
- Streamlit's session-only forms remain temporary by design; only account-backed routes persist through FastAPI.
- No PostgreSQL backup/restore drill, live privilege audit, row-count comparison, migration execution, or authenticated cross-component browser verification was performed.

## Remaining verification

The temporary local identity endpoint, token/enable flags, and diagnostic-only tests/documentation are being removed after the operator-reported read-only identity verification. No database write or migration is part of this cleanup. The reported identity confirms the target and revision for that temporary API process only; it does not verify all farmer workflows, database privileges, backup recovery, or production readiness.

Other deployment blockers remain: protected secret management, database role least privilege, HTTPS/reverse-proxy configuration, production connection-pool sizing, protected backups and restore drills, privacy/retention decisions, provider and dataset licensing, frontend/Streamlit authenticated browser tests, and production monitoring/incident response.
