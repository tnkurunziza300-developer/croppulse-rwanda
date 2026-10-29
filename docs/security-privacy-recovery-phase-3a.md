# Phase 3A — Security, privacy, and recovery notes

**Reviewed:** 2026-10-22  
**Scope:** repository source and local files in this project copy. This review did not identify the database used by any live external process, inspect server access logs, or assess a hosted environment.

## Database and protected-file inventory

The database target is selected by `CROP_PULSE_DATABASE_URL`; otherwise `backend/db.py` resolves `sqlite:///./data/croppulse_phase1.sqlite3` relative to the API process working directory. The repository also contains `data/croppulse_local.sqlite3` (legacy), timestamped SQLite copies in `data/backups/` and `.backups/`, and local API logs under `data/`. These names do not establish which database a separate running service uses. Confirm the intended process environment and working directory before backing up or restoring a real deployment.

Protect together, with permissions appropriate to their contents:

- The confirmed active database. It contains account credentials (password hashes), sessions/action-token hashes, farmer/farm/field records and coordinates, crop activities/plans/evidence, reviewer/admin decisions, private messages and read states, crop-health reports and normalized private photos, weather locations/saved forecasts/preferences/alerts, and account audit events.
- The NISR source spreadsheets and validated CSV plus `data/verified/MANIFEST.json`; weather source PDFs under `data/raw/weather_climate/`; transcribed bulletin records and provenance; and the agronomic knowledge/source/review files plus any permitted intake records. Back up only where source terms and retention permission allow it.
- The exact application release, migrations, dependency lockfiles, crop-screening model and labels, and deployment configuration needed to interpret/restore the database. Keep secrets in a separate managed secret store; do not copy plaintext secrets into ordinary backups or this repository.
- Any future private object-store content. Crop-health photos currently live in database BLOBs, so a complete database backup includes them. The NISR CSV is intentionally Git-ignored; confirm its availability independently of source control.

The local files observed during this review included both database paths above and existing backups under `data/backups/` and `.backups/`. The database target for a separately running API was not inferred from those files.

## Backup procedure

1. Identify the authoritative API process, exact database target, database engine, and source-data versions with the data owner. Never choose by filename alone.
2. Write a uniquely named backup into an access-restricted destination with inherited/reviewed Windows ACLs. Protect it with encrypted storage and separate access controls; do not overwrite a prior backup. Store the encryption key separately.
3. For SQLite, use Python's `sqlite3.Connection.backup()` API from a read-only source connection to obtain a transactionally consistent copy even if the API is active. Create the destination in the protected backup directory, verify `PRAGMA integrity_check` returns `ok`, confirm the Alembic revision and expected table set, and record a SHA-256 checksum outside the backup. Restrict/monitor writers during a recovery cutover. Do not rely on copying only the main `.sqlite3` file while WAL writers are active.
4. For PostgreSQL, use a consistent `pg_dump` custom-format backup and verify the artifact; protect roles/ownership information separately. Restore to an isolated database, never to the production target for a drill.
5. Restore into a new isolated temporary destination with restrictive permissions. Confirm integrity, schema revision, required tables, and application-level read-only smoke checks before declaring the backup recoverable. Keep dated outcomes and exceptions. Define retention with the data owner and test access to the encryption key.

The API does not schedule, monitor, encrypt, or retain backups. A single successful local restore is not proof of production disaster recovery or adequate backup frequency.

## Restore verification performed for this review

Read-only restore source: `data/backups/croppulse_phase1_before_weather_alerts_20261022_174716_292005.sqlite3`. Python opened that artifact read-only and used SQLite's online backup API to restore into a new in-memory SQLite database. The restored copy returned `PRAGMA integrity_check = ok`, reported Alembic revision `0014_weather_bulletin_records`, contained the required core tables (`farmers`, `farms`, `farm_activities`, `crop_plans`), and had farmer and farm rows present. No record contents, values, or row counts were printed. The original backup and working databases were not modified. The temporary in-memory destination was closed after verification.

This confirms that this one local backup can be opened and restored by SQLite. It does not establish that it is current, that it belongs to a live API process, that all companion source files/configuration were backed up, or that ACL/encryption/production recovery objectives are satisfied.

## Personal-data and retention inventory

| Data | Where / access behavior | Current deletion or retention behavior / gap |
|---|---|---|
| Email, display name, password hash, notice version/acceptance time, role/status | `farmers`; authenticated self and role-authorized administrative views | Password hash only; no plaintext password. No general account expiry or retention schedule. Registration email verification is absent. |
| Session IDs, expiry/revocation, action-token hashes, handoff hashes, failed-auth hashed buckets | `farmer_sessions`, `account_action_tokens`, `streamlit_handoffs`, `auth_attempts`; token values are not stored as plaintext in these tables | Sessions expire/revoke; expired action tokens/handoffs and stale auth-attempt rows do not have a complete scheduled purge policy. IP/email values contribute to a hash bucket; hashing does not make data anonymous. |
| Farm, field, district/sector, area, user-supplied coordinates | `farms`, `farm_fields`; farmer owner-scoped, with limited reviewer/admin scope | Account deletion cascades owned farm/field data. No independent coordinate retention or correction policy. Coordinates are not boundary verification. |
| Activities, harvest quantities, costs, notes, saved plans, recommendation context/evidence | `farm_activities`, `crop_plans`, `crop_plan_evidence`; owner-scoped and reviewer/admin access where workflow requires | Account/farm deletion removes linked records by cascade. No general retention schedule; free-text notes may contain unrequested sensitive details. |
| Messages, sender identity, timestamps, read state | `private_conversations`, `private_messages`; participant-only API access | Account deletion cascades the account's conversations/messages. No user message retention/export/reporting controls, no end-to-end encryption, and no defined operator retention period. |
| Crop-health symptoms, crop/farm references, affected parts/spread, photo, model candidates, reviewer updates | `crop_health_cases`, `crop_health_case_updates`; owner and currently district-authorized reviewers | Photo normalized and EXIF removed; private DB BLOB. Account/farm deletion cascades case data. No general retention schedule or verified diagnosis status. |
| Saved weather point/forecast, location source, preferences, alert history | Account-owned weather tables | Device location may be stored when a forecast is requested; field/manual/device coordinate and retention/deletion terms need explicit user-facing review. Account deletion handling depends on FK behavior and should be confirmed for all deployed revisions. |
| Admin/reviewer decisions and audit events | `activity_review_decisions`, `admin_audit_events`; restricted administrative/review access | Some records are intentionally retained after self-deletion with author/target foreign keys nulled. Self-deletion audit stores a target identifier string; retention, minimization, and re-identification risk need an approved policy. |
| Operational logs | API logs are deployment/process outputs; this repository has local API logs | Application logs inspected here avoid request bodies/tokens and log email-delivery failure purpose plus exception type. Hosted proxy/access/error logs were not inspected; query strings can contain one-time links and must be redacted. Set log access, retention, and deletion centrally. |
| Streamlit temporary entries | Streamlit session state, including market quotes, submissions, feedback, pest/extension/cooperative notes and observations | Cleared on login/logout/session clear; not durable account records. Session lifecycle and any hosting session persistence must be verified for deployment. |

Registration records acceptance of a versioned notice, but acceptance is not a legal compliance determination. The app does not define a comprehensive retention schedule, data-subject request procedure, consent withdrawal model, legal basis, residency commitment, breach-notification process, or organizational controller/support contact. These require authorized organizational and legal review before real-farmer service.

## Security review and changes

Confirmed defects fixed in this phase:

1. API startup accepted an omitted `CROP_PULSE_ENVIRONMENT` as development. Startup now requires an explicit supported environment.
2. In production/staging, `CROP_PULSE_COOKIE_SECURE=0` could override secure-cookie defaults, and absent CORS configuration inherited localhost development origins. Startup now requires explicit HTTPS CORS origins, rejects wildcard/path/userinfo origins, rejects disabling secure cookies and schema auto-creation, and secure cookies remain forced on for staging/production.
3. The API had no request-body ceiling before JSON/multipart parsing. ASGI middleware now caps request bodies at 8 MiB for body-bearing requests, including chunked requests without `Content-Length`. This allows the existing 5 MiB normalized photo limit plus multipart overhead. A reverse-proxy limit remains required to bound concurrent traffic and upstream resource use.

Other controls confirmed in source include Argon2 password hashing; signed sessions with server-side revocation; cookie CSRF checks; owner/role/district checks; generic validation/database error responses; failed-login, registration, and account-action throttles; photo content decoding, dimensions, re-encoding and EXIF removal; and database-bound account scopes. No secret, token, password, or request body was printed during this review.

`data/*.log` is now excluded by `.gitignore` because local API access logs are operational artifacts and may include sensitive URL paths/query strings. This does not erase existing logs or prevent a force-add; operators must inspect repository history and hosted log configuration separately. Application code found in this review logs only the account-mail purpose and exception class for delivery errors, and model-screening failure class; no request body/token logging was found. Uvicorn/proxy access logging remains deployment controlled.

General endpoint throttling is not implemented in the application. Add gateway/reverse-proxy rate limits for all routes, especially account actions, crop-health uploads, weather requests, and messaging. Per-process in-memory throttling would be unreliable across workers and restarts. Also verify request limits at the edge, TLS/proxy trust, dependency scanning, secret-store access, encrypted storage, log redaction, alerting, and incident response in the intended deployment.

## Unresolved privacy/security work

- Have the organization/legal owner approve the notice, data purposes, retention/deletion schedule, coordinates/photo handling, sharing/access, user rights, residency, support, and incident procedures.
- Decide and implement scheduled cleanup for expired tokens, handoffs, sessions, and authentication buckets; set retention for messages, crop-health reports/photos, farm history, and audit events.
- Inspect and configure real reverse-proxy, Uvicorn, hosting, monitoring, and analytics logs to remove query tokens, credentials, contact data, and farmer notes; no live logs were inspected here.
- Set gateway rate limits, request/concurrency limits, private encrypted database and backup storage, ACLs, key management, monitoring, and tested recovery objectives.
- Confirm every service process uses explicit environment, exact database target, secure cookies, HTTPS CORS origins, and migrations applied separately through an approved release process.

## Verification results for Phase 3A

- Focused API/security regression suite: `\.venv\Scripts\python.exe tests\windows_safe_pytest.py tests\test_react_security_api.py tests\test_backend_api.py` — **43 passed, 1 warning** (`PytestAssertRewriteWarning` for AnyIO).
- Full Python suite: `\.venv\Scripts\python.exe tests\windows_safe_pytest.py` — **153 passed, 3 failed, 1 warning**. All three failures were agronomic-intake filesystem tests at the Windows directory rename from temporary `.staging` to `records` (`PermissionError: [WinError 5]` at `utils/agronomy_intake.py:353`). An isolated agronomic-intake rerun produced **15 passed, 3 failed** with the same rename error. The immediate failing operation is established; whether the cause is this managed filesystem's ACL/rename behavior or an intake implementation issue needs separate diagnosis. No unrelated intake code was changed.
- Local backup restore: passed as recorded above; read-only source and in-memory restored target, integrity `ok`, required core tables present.
- Frontend tests/build/typecheck/lint were not rerun because no frontend source changed. No browser, live server, hosted config, migration, or production recovery test was performed.

## Phase 3A.1 follow-up — Windows-safe agronomic intake publication — 2026-10-22

The three recorded intake failures all surfaced at the final Windows directory rename from a completed staging directory into `records`, with `PermissionError: [WinError 5]`. Source inspection found file, JSON, copy, and DOCX archive handles closed before publication. The observed staging and records ACLs matched, and simple same-volume rename diagnostics succeeded, so the underlying Windows access-denied trigger was not conclusively identified. No antivirus cause is asserted.

Intake publication now assembles the unique destination directory under a `.publication_pending` marker, copies its validated package files, verifies the copied metadata, event chain, validation digest, and retained-artifact checksum, then removes the marker as the commit step. Record listing ignores pending packages. On a publication I/O failure the original hidden staging package and pending destination are retained for recovery; they cannot be listed or counted as active coverage. Existing version locks and no-overwrite checks remain in place. This avoids the failing directory-rename boundary without retry loops or weaker validation.

Regression coverage verifies publication remains hidden until all package files are copied, simulated Windows publication denial preserves recoverable data while coverage remains zero, and existing intake integrity/lifecycle checks continue to pass. No NISR CSV/manifest, active agronomic registry, SQLite database, or migration was modified. This is a local intake workflow, not a public multi-user upload service.

**Phase 3A.1 verification:** The previously failing intake cases plus publication regressions passed (**5 passed**); focused intake and knowledge tests passed (**29 passed**); full Python suite passed (**158 passed, 1 warning**) using `tests/windows_safe_pytest.py`. Frontend tests passed (**35 passed across 4 files**) with Vitest's native config loader and thread pool; default Vitest worker startup was blocked by Windows `spawn EPERM`. Frontend typecheck and lint passed. The production build result is recorded in the dated Phase 3A.1 entry in `docs/full-application-audit-phase-2.md`. No browser/live service verification or deployment was performed.
