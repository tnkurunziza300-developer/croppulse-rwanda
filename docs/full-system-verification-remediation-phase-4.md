# CropPulse Rwanda — Full System Verification and Reliability Remediation, Phase 4

**Verification date:** 2026-10-28  
**Repository:** `C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda`  
**Readiness verdict:** **DEVELOPMENT ONLY**  
**Scope:** current source, local configuration names, listeners, migration history, read-only SQLite checks, isolated automated tests, and existing readiness/recovery evidence. No service was started or contacted; no production environment was available.

## 1. Executive summary

The repository contains a React/TypeScript farmer and administration workspace, a FastAPI account and data service, and the existing Streamlit planning and analytics interface. Both interfaces use the API; they are not yet a single fully migrated frontend. Account-backed records include farms, fields, activities, crop plans, crop-health cases, saved React forecasts, and private text conversations. Many legacy Streamlit tools remain session-only.

This phase added a local, read-only runtime/database diagnostic command and regression tests for its safety properties. It resolves relative SQLite paths from the command's working directory, refuses to create missing databases, refuses to inspect SQLite files with WAL/SHM sidecars, reads SQLite in read-only/query-only mode, and reports the migration revision against the source head. The PostgreSQL branch uses a read-only transaction and a non-secret identity fingerprint, but no PostgreSQL server was available to verify that branch. The command reports only the environment of the command that runs it; it cannot inspect an already-running API process.

The diagnostic was run with the owner-designated local development database explicitly selected. That invocation confirmed the path, connectivity, revision `0015_weather_alert_foundation`, current source-head match, SQLite integrity, and zero foreign-key violations. The file size and modification time matched the initial inspection. These results do not prove which database a separately running service would use. No application listeners were present on the checked ports during this inspection.

The complete Python suite passed **172 tests** with one pre-existing AnyIO pytest assertion-rewrite warning. The complete React suite passed **48 tests**; typecheck and lint passed. The production Vite bundle was built to a new isolated output folder, while the existing `frontend/dist` directory was left untouched. No authenticated browser workflows were performed.

Readiness remains **DEVELOPMENT ONLY**. There are zero approved agronomic rules; crop planning content remains provisional; the disease model is experimental maize-only screening, not diagnosis; weather alert generation is not active; production database identity, hosted controls, protected recovery, data rights, privacy operations, and authenticated browser workflows remain unverified or unresolved.

## 2. Repository baseline and preservation

- The project root exists and contains `backend/`, `frontend/`, `data/`, `tests/`, `utils/`, Streamlit entry points, Alembic configuration, and the audit history reviewed below.
- Git is unavailable in this environment and this project directory has no `.git` directory. A complete status/diff and classification of older pre-existing edits could not be established. No existing application source was overwritten by this phase; the only existing source edit is a focused frontend test correction described in section 10.
- Python is 3.12.10 in the project `.venv`. Installed versions reported during inspection: FastAPI 0.143.2, SQLAlchemy 2.1.4, Alembic 1.20.0, pytest 9.1.1. Frontend dependencies are pinned in `frontend/package-lock.json`; Vite 8.3.4 and Vitest 5.0.5 were reported by the executed build/test commands.
- The root `.env` is absent. Variable names only were inspected in frontend `.env` files; their non-API values were not printed. The configured development API base is loopback `127.0.0.1:8001`. No production API URL was supplied or verified.
- The Phase 3, Phase 2, Phase 3A, Phase 4 readiness, Phase 5, Phase 6, React setup, backend setup, and deployment checklist documents were reviewed. Historical findings were treated as evidence to recheck, not as current proof.

## 3. Runtime and configuration findings

### Current process observation

Read-only listener checks covered TCP ports **8000, 8001, 8501, 5173, 18001, and 15173**. No listeners were returned. No API, Streamlit, Vite, browser, or external provider was started or contacted. This establishes only that no listener was observed on those ports at the time of this check; it does not establish that a deployment or another runtime is absent.

The verification shell initially had no `CROP_PULSE_DATABASE_URL`, `CROP_PULSE_ENVIRONMENT`, `CROP_PULSE_AUTO_CREATE_SCHEMA`, or `CROP_PULSE_SECRET_KEY` set. No secret values or full environment files were printed. The API source reads `CROP_PULSE_DATABASE_URL`; without it, the default is `sqlite:///./data/croppulse_phase1.sqlite3`. Relative SQLite URLs resolve from the process working directory. The Alembic environment uses the same URL variable/default. The repository launcher sets the project working directory and child environment when it launches the API, but that does not identify an unrelated process.

`backend/api.py` validates runtime security at lifespan startup and calls `Base.metadata.create_all()` only when `CROP_PULSE_AUTO_CREATE_SCHEMA=1`; staging/production configuration rejects that setting. The diagnostic does not import the API, invoke startup, create tables, or run migrations.

### Runtime diagnostic added

`python -m backend.diagnostics` is a **local operator command**, not an authenticated endpoint. It reports the executable, working directory, repository API entry-point path, allow-listed runtime environment label, selected backend, SQLite absolute path (or PostgreSQL fingerprint), connectivity, database revision, source migration head, and SQLite integrity/FK results.

SQLite checks use an existing file in `mode=ro` with `query_only` enabled. A missing path is reported without creating a file. If `-wal` or `-shm` sidecars exist, the command refuses to inspect that SQLite target rather than risk sidecar changes. PostgreSQL is queried inside a read-only transaction; credentials and raw URLs are never printed. Unsupported backends are not contacted. A configuration or driver error is reported without echoing its details.

The command describes only its **own invocation**. It cannot establish another process's environment, module path, or active database. A separately running service still requires evidence from its launch environment or an explicitly approved in-process operator diagnostic.

## 4. Database identity, integrity, and migration findings

The project owner previously designated `data/croppulse_phase1.sqlite3` as the intended local development database. The database identity below is confirmed for this local file and explicit diagnostic invocation only.

| Candidate | Read-only result on 2026-10-28 | Interpretation |
|---|---|---|
| `data/croppulse_phase1.sqlite3` | 19,525,632 bytes; integrity `ok`; zero FK violations; revision `0015_weather_alert_foundation` | Owner-designated development candidate. Diagnostic path, connectivity and source-head match confirmed when explicitly configured. Not evidence about a live API or production database. Size and modification time matched the initial read-only inventory after diagnostics. |
| `data/croppulse_local.sqlite3` | 8,192 bytes; integrity `ok`; zero FK violations; no Alembic revision and no application tables | Legacy empty database candidate; not designated as authoritative. |
| `data/backups/croppulse_phase1_before_weather_alerts_20261022_174642.sqlite3` | 19,271,680 bytes; integrity `ok`; zero FK violations; revision `0014_weather_bulletin_records` | Historical pre-alert backup candidate. Its existence and integrity do not establish completeness, access protection, or current recovery suitability. |
| `data/backups/croppulse_phase1_before_weather_alerts_20261022_174716_292005.sqlite3` | 19,271,680 bytes; integrity `ok`; zero FK violations; revision `0014_weather_bulletin_records` | Same limitations as the preceding historical backup candidate. |
| Existing `.test-runtime/phase4-recovery-…/isolated-test.sqlite3`, `.backup.sqlite3`, and `.restored.sqlite3` | Each: integrity `ok`; zero FK violations; revision `0015_weather_alert_foundation` | Synthetic Phase 4 recovery artifacts rechecked read-only. They are not backups of the designated development database. Their inherited ACL was previously reported as broad and is not considered protected. |

The configured Alembic graph has one linear head, `0015_weather_alert_foundation`, with ancestry from `0001_phase1_records` through `0014_weather_bulletin_records`. `alembic heads` and `alembic history --verbose` confirmed the chain. The migration tests exercise historical upgrade/data-preservation paths, additive weather-alert migration behavior, and selected reversible downgrades against isolated temporary databases. Source inspection shows destructive `drop_table`/`drop_column` operations in downgrade paths; these are not safe data-preserving rollback plans.

The local development database was opened only with read-only SQLite connections for checks. No migration, table creation, database write, copy, backup, or restore was performed by this phase. The current database file's observed size and UTC modification time were unchanged from the initial inspection.

## 5. Backup and restore evidence

The Phase 4 readiness report documents a **2026-10-26 synthetic** recovery rehearsal: a new isolated database was migrated, backed up with SQLite's backup API, restored to a separate target, and the three artifacts passed integrity, FK, revision, and synthetic-record checks. This phase rechecked the three artifacts read-only and they remain structurally healthy.

That rehearsal is not a backup/restore of the owner-designated development database or production data. The prior report records that ACL hardening was denied and inherited ACLs were restored; the test artifacts are not encrypted, off-site, scheduled, or verified access-restricted. The historical `data/backups/` files also do not prove the active API's data source or recovery objective. No new backup was created because the repository's available test/backup locations do not have verified restrictive access controls. No production restore or RPO/RTO test is evidenced.

### Safe recovery procedure required before real data

1. Have the data/service owner identify the exact database target and confirm that writes are stopped or coordinated for a consistent snapshot.
2. Use a separately approved, access-controlled and, where required, encrypted backup destination. Verify ACLs and available space before writing; do not use the existing broad-ACL test directory for real records.
3. Create a uniquely named backup using the database's supported consistent-backup mechanism. Never overwrite a prior backup.
4. Restore to a new isolated target, not over the source. Verify integrity, foreign keys, schema revision, and agreed non-sensitive record invariants.
5. Record source/backup/restore identities and timestamps without recording personal data; verify the source file remains unchanged.
6. Obtain the data owner’s approval before any restore is promoted or application traffic is switched.

This procedure was **not executed** for the designated development database in Phase 4.

## 6. Authenticated workflows and authorization coverage

The full Python tests use synthetic accounts and isolated SQLite fixtures. They include route-level assertions for:

- Browser registration, sign-in/out, cookie/CSRF, session expiry/revocation, role self-assignment denial, and account recovery/email-change token behavior.
- Farmer ownership for farms, fields, activities, plans, weather records, crop-health cases/photos, and messaging.
- Crop-plan lifecycle constraints and migration preservation behavior.
- Reviewer district scope and activity/crop-health review actions.
- Administrator-only account, permission, reviewer assignment, messaging-setting and audit operations.
- Messaging participant authorization, eligibility reevaluation, unread/read behavior, and disabled-setting enforcement.
- Crop-health upload validation, unsupported-model behavior, reviewer follow-up, and non-diagnostic screening language.
- Weather validation, saved-forecast ownership, stale fallback, provider error/malformed responses, and alert preference/history behavior.

These are automated API/component tests, not browser E2E tests. No current local services were running, and no browser workflow was executed. Registration-to-data persistence, cross-user denial, role-specific review, CSRF in a real browser, React/Streamlit cookie restoration, refresh, viewport, console/network behavior, and mobile interaction remain unverified end-to-end.

## 7. React, FastAPI, and Streamlit integration

- React and Streamlit call FastAPI; neither interface opens SQLite directly.
- The source uses cookie-based browser sessions, CSRF protection for state-changing browser requests, role-based UI routes, and short-lived single-use account handoffs between React and Streamlit.
- The account session is documented as having a 30-minute lifetime. A rejected protected request returns the user to sign-in; that behavior is covered by automated tests but was not browser-tested here.
- React's local configured API base points to loopback `127.0.0.1:8001`. This is local-development configuration, not a remote deployment URL. No public domain or hosted configuration was supplied.
- Streamlit contains legacy planning, analytics and data-entry features. Persistent account records use the API; market/economics inputs, legacy pest reports, extension notes, cooperative notes, recommendation feedback and local weather observations remain session-only according to source/docs. They must not be described as durable shared records.
- Hekitari remains an external link; no SSO/API/farm-data integration was found.

No obsolete API process or duplicate server was observed on the checked local ports. Since no service was running, no live OpenAPI comparison, CORS/CSRF exchange, or live database identity check was possible.

## 8. Security and agricultural safety

Source and regression tests cover explicit runtime secrets/environment, HTTPS-only CORS allowlists and secure-cookie behavior in staging/production, CSRF, an 8 MiB application request-body cap, separate crop-photo limits, safe error responses, account-action throttles, owner/role/district authorization, and no automatic schema creation in staging/production.

These local checks do not establish hosted TLS/proxy trust, managed secret storage, exact production CORS, edge request/rate/concurrency limits, monitoring, safe access to logs/backups, incident response, penetration resistance, or general API abuse protection. Account-sensitive throttles are not general rate limiting.

The agronomic registry validator returned `valid=true`, current manifest, no findings, and **zero approved rules**. The NISR SAS CSV hash matches its manifest; the dataset remains descriptive historical context and does not validate crop guidance. Crop recommendations remain provisional. Weather alert settings/history exist, but the approved alert-rule registry is empty and no active alert-generation workflow was verified. The bundled image screening is experimental, maize-only candidate ranking with uncalibrated scores—not diagnosis or treatment guidance. No agricultural approval or specialist qualification is inferred.

## 9. Confirmed findings and remediation

### Fixed in this phase

1. **No safe local database identity diagnostic existed.** Added `backend/diagnostics.py` as a standalone local command rather than exposing internal database paths through an anonymous route. It does not create databases, run migrations, or import API startup. Regression tests establish missing-file non-creation, working-directory-relative path resolution, current migration-head reporting, read-only integrity checks, and unchanged file size/mtime for a temporary migrated fixture.
2. **The existing demo dashboard regression test was timing-sensitive and used exact text matching for text combined with farm metadata.** Updated the test to wait for the asynchronously loaded saved plan and match the farm-name substring. No application UI behavior was changed by that test adjustment.

### Confirmed but not fixed because it needs outside evidence/decisions

- Live API source and effective database identity are unconfirmed; no API process was present to inspect.
- The owner-designated development SQLite file is healthy, but no protected backup/restore target is verified.
- No production runtime/domain/database was supplied; local loopback configuration cannot be treated as production configuration.
- No approved agronomic rules, active weather alert generator, or locally validated disease diagnosis/treatment workflow exists.
- Provider/data reuse rights, privacy/retention, hosting security, SMTP delivery, and full browser workflows remain open.

No other in-scope application defect was established by the checks in this phase. No security assertion was weakened, no route/schema was changed, no agronomic rule was added, and no production setting was changed.

## 10. Files and artifacts

### Repository files changed

- `backend/diagnostics.py` — new standalone, fail-closed, read-only diagnostic command.
- `tests/test_runtime_diagnostics.py` — new isolated regression tests for diagnostic safety and path/revision reporting.
- `frontend/src/App.test.tsx` — fixed the demo overview test's async wait and substring match; no product behavior changed.
- `docs/full-system-verification-remediation-phase-4.md` — this evidence report.
- `README.md` — added a link to this report.

No other source, dependency manifest/lockfile, configuration, migration, NISR source file/manifest, agronomic registry, bulletin PDF, or model artifact was intentionally changed.

### Test/build outputs

- The Windows-safe pytest runner created its unique per-run fixture directory under `.test-runtime/pytest-data/`; those synthetic test artifacts were retained, not cleaned.
- The Vite production bundle was created under `.test-runtime/phase4-20261028-build/` with separate TypeScript typecheck performed first. Existing `frontend/dist/` remained untouched; its modification time stayed at the pre-existing 2026-10-26 value.
- The custom TypeScript build-info output was not created. The attempted `tsc -b --tsBuildInfoFile ...` command was rejected before compilation because TypeScript does not permit that option in build mode.

## 11. Verification record

Commands ran from the repository root unless stated otherwise. Full environment values, credentials, personal records, message text, farm coordinates and photo contents were not printed.

| Command/check | Result |
|---|---|
| `Get-Command git`; `Test-Path .git`; repository/doc/source inventory | Git unavailable and `.git` absent; no complete Git status/diff possible. |
| Read-only `Get-NetTCPConnection -State Listen` for ports 8000, 8001, 8501, 5173, 18001, 15173 | No listeners returned. No process was launched/stopped/restarted. |
| `\.venv\Scripts\python.exe -m alembic heads` and `... -m alembic history --verbose` | One head at `0015_weather_alert_foundation`; linear ancestry through `0001`. |
| Read-only SQLite inspection via `file:...?...mode=ro`, `PRAGMA integrity_check`, `PRAGMA foreign_key_check`, and revision read | All four `data/*.sqlite*` candidates and three existing synthetic recovery artifacts returned integrity `ok`, zero FK violations; revisions/size recorded above. No private rows were selected. |
| `CROP_PULSE_DATABASE_URL=sqlite:///./data/croppulse_phase1.sqlite3`, `CROP_PULSE_ENVIRONMENT=development`, `CROP_PULSE_AUTO_CREATE_SCHEMA=0`; `\.venv\Scripts\python.exe -m backend.diagnostics` | Exit 0. Printed explicit local invocation scope; correct absolute path; SQLite connection ok; revision and source head matched at `0015`; integrity `ok`; zero FK violations. Target size/mtime unchanged. Environment variables were removed from the shell after the command. |
| `\.venv\Scripts\python.exe tests\windows_safe_pytest.py tests\test_runtime_diagnostics.py` | **3 passed**, one AnyIO `PytestAssertRewriteWarning`. An initial targeted run exposed a relative Alembic script-location issue in the new diagnostic; it was corrected and the final focused run passed. |
| `\.venv\Scripts\python.exe tests\windows_safe_pytest.py` | **172 passed**, one AnyIO `PytestAssertRewriteWarning`, 167.13 seconds on final rerun. Fixtures/migrations ran against test-created SQLite targets under `.test-runtime`; no existing application database migration was run. |
| In `frontend`: `npm.cmd test -- --configLoader native --pool=threads --maxWorkers=1 --testTimeout=30000 src/App.test.tsx` | **32 passed** after correcting the demo test wait/matcher. Vitest logged `Not implemented: navigation to another Document`; no assertion was removed. |
| In `frontend`: `npm.cmd test -- --configLoader native --pool=threads --maxWorkers=1 --testTimeout=30000` | **48 passed across 6 files**. Same non-failing navigation diagnostic was logged. The default Windows worker startup path was not used. |
| In `frontend`: `npm.cmd run typecheck` | Passed. |
| In `frontend`: `npm.cmd run lint` | Passed. |
| `npx.cmd tsc -b --tsBuildInfoFile ..\.test-runtime\phase4-20261028.tsbuildinfo` | Failed before compilation: TS5094, `--tsBuildInfoFile` cannot be used with `--build`. No build-info file was created; existing frontend build metadata was preserved. |
| `npx.cmd vite build --configLoader native --outDir ..\.test-runtime\phase4-20261028-build --emptyOutDir false` | Passed; 2,517 modules transformed, isolated production bundle produced. Combined `npm run build` was not invoked because it writes build metadata to the existing frontend location; typecheck and production bundling were executed separately. |
| `\.venv\Scripts\python.exe -m utils.agronomy_knowledge` | Passed: pack valid/current, zero findings, zero approved rules, six open quality issues, 2,020 NISR rows. |
| NISR CSV SHA-256 compared with its manifest entry | Match. Dataset and manifest were not changed. |
| Authenticated browser workflows / responsive QA | **Not performed.** No supported browser-control session or isolated live application runtime was available. |
| Live API/OpenAPI/database identity or PostgreSQL check | **Not performed / unverified.** No listener or PostgreSQL test service was available. |
| New backup/restore of designated development database | **Not performed.** No verified protected destination exists; previous synthetic restore evidence is described above. |

The first frontend suite run after correcting the demo overview test had one test assertion failure because the rendered farm name shares a text node with district/area metadata. The assertion was corrected to match the intended substring, then the focused file and full suite passed. The initial focused diagnostics test likewise found a current-working-directory issue that was fixed before the final full Python run.

## 12. Open risks and next actions

### Critical readiness gates

1. Identify the service owner, intended hosted source artifact, API runtime, database identity, and domain. Verify the process from its actual launch context; do not infer it from the local default URL.
2. Provision and verify a protected backup target, encryption/access policy, retention, RPO/RTO and an isolated restore rehearsal before real farmer data or migrations.
3. Configure and test hosted HTTPS, trusted proxy behavior, secure cookies, exact CORS, managed secrets, edge request/rate/concurrency controls, redacted logs, monitoring and incident response.
4. Complete authenticated desktop/mobile browser workflows on an isolated staging database with disposable farmer, reviewer and administrator accounts, including cross-user/district denial and session/CSRF behavior.
5. Obtain organizational/legal approval for privacy basis, notice, retention/deletion/export, residency, access support and incident handling.
6. Resolve source-specific NISR, METEO RWANDA, Open-Meteo, and PlantVillage/model reuse terms for the intended non-commercial/commercial use.
7. Keep recommendations, disease outputs and alerts bounded until qualified local evidence review, validation and traceable approved rules exist.

### Lower-priority but necessary product work

- Decide which Streamlit session-only tools should become account-backed React workflows.
- Review Kinyarwanda terminology, accessibility, low-bandwidth and field usability with local users.
- Test real email delivery with a non-production mail sink; SMTP was not configured/tested here.
- Evaluate PostgreSQL runtime and migration behavior in an isolated service before describing that backend as operationally verified.

## 13. Final verdict

**DEVELOPMENT ONLY.** Local tests, source inspection, read-only checks, and a local diagnostic invocation provide useful engineering evidence. They do not establish live service identity, production hosting/security, protected production recovery, authenticated browser usability, legal/provider permission, privacy readiness, or validated agricultural outcomes. Phase 5 should be limited to a controlled isolated browser/staging exercise after the staging runtime and protected test data are explicitly identified. Public release or a farmer pilot remains blocked pending the critical gates above.

No production action, deployment, live API restart, migration, or write to the designated development database occurred in Phase 4.
