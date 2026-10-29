# CropPulse Rwanda — Gate 1G: Controlled Maintenance and Live Database Identification

**Audit date:** 2026-10-26 (Africa/Johannesburg)  
**Project root:** `C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda`  
**Scope:** Read-only candidate database inventory and a proposed, separately authorized maintenance plan. No service or database was changed.

## Verified current state

At the time of this check, `netstat -ano -p tcp` showed these listeners:

| Service as previously identified | Listener | PID | What this check proves |
|---|---|---:|---|
| API | `127.0.0.1:8001` | 21152 | A process owns this local TCP listener; its source, working directory and database remain unproven. |
| Streamlit | `0.0.0.0:8501` | 24140 | A process owns this all-IPv4 listener. This plan does not inspect or change it. |
| Vite | `127.0.0.1:5173` | 11512 | A process owns this local TCP listener. This plan does not inspect or change it. |

These observations do not independently prove process ownership by CropPulse. Earlier Gate 1F reports that Windows process metadata access was denied for relevant fields. The Gate 1D isolated API test on `127.0.0.1:18001` is documented as stopped; it was not relaunched for this plan.

The Gate 1E correction reports the current API's OpenAPI includes the weather-alert endpoints. Gate 1D's earlier route omission was a PowerShell schema-property inspection false negative. Route parity does not establish the running API's source or database.

## Candidate database inventory and provenance

The following metadata was collected read-only with Python `sqlite3`, opening each file using a URI with `mode=ro`. The checks queried `PRAGMA integrity_check`, table names/count, and `alembic_version` only; no application rows were selected. Modification times are filesystem timestamps and are not proof of ownership or authoritative status.

| Canonical path (relative to project root) | Size | Modified (local) | Revision | Tables | Integrity | Provenance/evidence |
|---|---:|---|---|---:|---|---|
| `data/croppulse_phase1.sqlite3` | 19,402,752 B | 2026-10-26 11:49:40 | `0015_weather_alert_foundation` | 24 | `ok` | Local candidate described by Phase 4 report. Latest project data file found; neither file name, timestamp nor schema identifies it as the live or intended authoritative DB. |
| `data/croppulse_local.sqlite3` | 8,192 B | 2026-10-21 08:01:56 | none | 0 | `ok` | Empty/legacy SQLite file per Phase 4 and backend docs; not a viable current app database based on inspected schema. Do not use it as a substitute. |
| `.backups/before-saved-weather-forecasts-20261022-092122.sqlite3` | 19,271,680 B | 2026-10-22 09:13:54 | `0012_weather_bulletins` | 20 | `ok` | Filename suggests pre-change snapshot; origin, consistency procedure and restore provenance not verified. |
| `.backups/before-weather-outlook-records-20261022.sqlite3` | 19,271,680 B | 2026-10-22 09:37:03 | `0013_saved_weather_forecasts` | 21 | `ok` | Filename suggests pre-change snapshot; not verified as authoritative or restorable production backup. |
| `.backups/croppulse_phase1-before-crop-health-f2b1bc4d.sqlite3` | 1,540,096 B | 2026-10-21 23:55:41 | `0009_crop_health_cases` | 19 | `ok` | Historical pre-change named file; provenance and relation to current DB unproven. |
| `.backups/croppulse_phase1-before-password-recovery-20261020.sqlite3` | 155,648 B | 2026-10-20 16:25:07 | `0003_roles_review_and_admin` | 10 | `ok` | Historical pre-change named file; not a current-schema backup. |
| `.backups/croppulse_phase1-before-weather-bulletins.sqlite3` | 1,540,096 B | 2026-10-22 08:54:58 | `0011_crop_health_ai_screening` | 19 | `ok` | Historical pre-change named file; provenance and restore procedure unproven. |
| `.backups/croppulse_phase1_before_0008_20261021.sqlite3` | 286,720 B | 2026-10-21 10:11:52 | `0007_fields_and_evidence` | 16 | `ok` | Migration-named historical snapshot; not current schema. |
| `.backups/croppulse_phase1_before_0009_crop_health_20261021.sqlite3` | 307,200 B | 2026-10-21 14:38:08 | `0008_streamlit_handoff` | 17 | `ok` | Migration-named historical snapshot; not current schema. |
| `.backups/croppulse_phase1_pre_0006_20261020.sqlite3` | 192,512 B | 2026-10-20 20:21:05 | `0005_self_service_account` | 11 | `ok` | Migration-named historical snapshot; not current schema. |
| `.backups/croppulse_phase1_pre_0007_20261020.sqlite3` | 241,664 B | 2026-10-20 20:29:30 | `0006_private_messaging` | 14 | `ok` | Migration-named historical snapshot; not current schema. |
| `data/backups/croppulse_phase1_before_weather_alerts_20261022_174642.sqlite3` | 19,271,680 B | 2026-10-22 17:46:42 | `0014_weather_bulletin_records` | 22 | `ok` | Weather-alert-named pre-change candidate. Backup chain, ACLs, encryption, and restore have not been proven. |
| `data/backups/croppulse_phase1_before_weather_alerts_20261022_174716_292005.sqlite3` | 19,271,680 B | 2026-10-22 17:47:16 | `0014_weather_bulletin_records` | 22 | `ok` | Similar named pre-change candidate. Duplicate size/revision does not prove identical contents or authoritative lineage. |
| `.backups/pre-react-migration-20261016/croppulse_phase1.sqlite3` | 81,920 B | 2026-10-16 17:09:14 | `0002_revocable_sessions` | 6 | `ok` | Explicitly historical migration backup; obsolete schema. |
| `.backups/pre-react-migration-20261016/croppulse_local.sqlite3` | 16,384 B | 2026-10-16 17:09:14 | none | 3 | `ok` | Explicitly historical legacy DB; not the current schema. |

Additional SQLite files under `.test-runtime`, `.backend-check-tmp`, and `.pytest-tmp` are test, migration, or smoke-check artifacts. The three files in `.test-runtime/phase4-recovery-3f5e0732384149d7b6201b3677958bc4/` are explicitly synthetic recovery-test source/backup/restore copies at revision `0015`, each 475,136 bytes and integrity `ok`. Phase 4 documents synthetic-only content and an isolated SQLite backup/restore check. The artifact directory ACL could not be verified as restrictive; these files are not protected backups of real user data. Other runtime/migration test artifacts are not production candidates.

### What the inventory establishes

- The current local candidate and multiple historical snapshots are structurally readable and pass SQLite's integrity check. That check does not prove provenance, completeness, confidentiality, or that a file belongs to the running service.
- The historical filenames and revisions are consistent with incremental development/migration snapshots. No signed database manifest, trusted backup catalog, production configuration, service record, or owner attestation in the reviewed evidence designates one of these files as authoritative.
- PID 21152's process CWD, launch target, environment, imported module path, and effective SQLAlchemy connection remain unavailable. `backend.db.database_url()` uses `CROP_PULSE_DATABASE_URL` if present and otherwise `sqlite:///./data/croppulse_phase1.sqlite3`; a relative SQLite URL resolves against that process's working directory. The repository launcher sets a local relative URL only when it starts a new API; when port 8001 already has a responding API, it reuses it. Thus the launcher's default is not evidence about PID 21152.
- Source configures schema creation only when `CROP_PULSE_AUTO_CREATE_SCHEMA=1`; startup otherwise does not call `create_all`. This is a source-level fact, not proof of the live process's environment. Alembic source is at `0015_weather_alert_foundation`; that does not prove any candidate/live DB is compatible or migrated.

**Conclusion:** Available evidence cannot distinguish which candidate, if any, is authoritative. Do not choose by filename, recency, file size, revision, or health result. The intended DB must be identified by the accountable service/data owner and corroborated against service configuration, known data continuity, backup history, and the running system.

## Maintenance prerequisites and approval checklist

Do not schedule the cutover until every prerequisite below is documented and reviewed:

- [ ] Service owner confirms the exact API service/process, its launch supervisor, the intended project source tree, and the canonical database target. If unresolved, stop deployment work.
- [ ] Data owner explicitly designates the authoritative database and confirms expected schema revision/data continuity without exposing personal records.
- [ ] Owner identifies an approved maintenance window, user impact, recovery contact, and write-freeze procedure. Confirm there is exactly one writer before and after cutover; SQLite must never be shared by two API writers during overlap.
- [ ] A consistent backup is made from the identified DB to a protected destination with verified ACLs, encryption at rest, access ownership, timestamp, and cryptographic checksum. SQLite backup API or a supported quiesced snapshot is preferred. Do not copy a live SQLite main file while writes can occur; account for WAL/journal files or use the SQLite backup mechanism.
- [ ] Restore the backup to a distinct isolated path, never over the source or candidate. Verify integrity, foreign-key consistency, expected revision and non-sensitive owner-approved data invariants. Record the exact restore command and successful open/read-only check.
- [ ] Data owner approves a tested rollback path, and operator proves it can restore the previous service command/configuration without overwriting the database.
- [ ] Capture the pre-window listener map, PID/start time, owner/supervisor, executable, working directory, sanitized launch parameters, API health/OpenAPI path set, database identity evidence, DB revision/size/checksum, and current backup location. Keep private values in an access-controlled operations system, not this report.
- [ ] Ensure no schema migration is included in this maintenance action. Migration work needs its own reviewed plan and approval after database identity and recovery are established.

Current status: the real-data authoritative target, a verified protected backup, and a real-data isolated restore rehearsal are not established. The Phase 4 synthetic restore is not a substitute.

## Ordered execution procedure (proposal only)

1. **Freeze and record.** At the approved window, the service owner announces a write freeze and verifies no API/background process is writing. Record exact current listeners and process identities using approved elevated Windows tooling. Do not terminate by process name or port alone.
2. **Confirm target.** Resolve the owner-approved DB path/endpoint from the authoritative service configuration. For SQLite, resolve to canonical absolute path. Compare it against the agreed data continuity evidence and confirm no second API will write to it. If configuration or target differs from approval, stop.
3. **Back up and rehearse.** Make a consistent, protected backup, checksum it, restore it to a separate isolated location, and verify integrity/revision and owner-approved non-PII invariants. If any check fails, do not stop the existing API.
4. **Preserve rollback state.** Archive the exact old service definition/launch command and secure config reference with appropriate access controls. Record the old PID, supervisor identity, listener binding, and operator. Do not put secrets into console transcripts or report files.
5. **Authorize the service action separately.** Stop only the verified old API using its owning supervisor's graceful service procedure; confirm its PID no longer owns the target listener. Do not stop Streamlit or Vite unless their owners separately approve it. Confirm port 8001 is free before starting a replacement.
6. **Launch the intended API.** From the confirmed project root and its `.venv\Scripts\python.exe`, launch `backend.api:app` with the exact owner-approved database URL set in the API process environment. Use `CROP_PULSE_AUTO_CREATE_SCHEMA=0`; do not use a guessed database path or enable table creation. Keep the replacement bound to the approved interface/port. Secrets remain supplied through the approved secret store/process configuration, never command-line arguments or logs.
7. **Verify before writes/traffic.** Before routing users or permitting writes, record safely: `sys.executable`, `sys.prefix`, current working directory, `backend.api.__file__`, listener PID/binding, engine dialect, sanitized canonical database target (SQLite `PRAGMA database_list` or approved PostgreSQL identity), Alembic revision and read-only integrity checks. Confirm the DB path equals the signed-off target, schema matches expected `0015_weather_alert_foundation` unless separately approved otherwise, auto-create is disabled, health is healthy, and OpenAPI contains the current expected routes. A mismatch is a stop condition.
8. **Canary and compare.** Only after the data owner approves identity checks, permit a controlled canary. Compare pre/post revision, integrity, schema, DB size/hash, and owner-approved aggregate invariants. Hash equality is expected only before writes; after authorized writes, investigate differences with non-sensitive metrics and audit data. Do not dump private rows. Ensure only one writer remains.
9. **Close window.** Record operator, timestamps, approval, backup/checksum location, tested restore result, process identity, route set, and comparison outcome. Resume writes only after the service/data owner signs off.

## Backup and restore requirements

There is no evidence of a protected backup service for the intended live DB. Repository migration snapshots and synthetic recovery artifacts do not meet this requirement. Before maintenance, the database owner must select the identified authoritative target, a destination separate from the project directory, an encrypted/access-controlled backup method, retention policy, checksum record, and tested restore operator. Verify both integrity and application-level schema/consistency in the restored copy. Do not use `data/croppulse_phase1.sqlite3` merely because it is current and healthy. Never restore a backup over the source file as a rollback shortcut.

The prior Phase 4 report records a successful restore rehearsal only for a fresh synthetic DB. It also records that ACL hardening was not verified, no real-data restore occurred, and no RPO/RTO was measured. Consequently, backup/restore readiness for farmer records remains **unproven**.

## Rollback steps

Rollback is a service-configuration reversal, not a database overwrite:

1. If pre-write identity checks fail, keep the replacement out of user traffic and do not allow writes.
2. Stop only the replacement PID through its verified service supervisor; confirm the listener is released.
3. Restore the preserved old service definition, environment reference, binding, and launch command. Do not guess missing secrets or database settings.
4. Restart the prior service only under the separate maintenance authorization; verify the old PID/service owns the expected listener and compare its health/OpenAPI to the captured baseline.
5. If any writes may have reached either DB, freeze writes and ask the data owner to reconcile before switching service. Do not copy/restore a DB automatically; preserve both files and logs for investigation.
6. If the former API cannot be safely reconstituted from preserved configuration, leave the service stopped and escalate to the owner rather than point it at a candidate database.

## Explicit stop conditions

Abort before stopping the current API if the authoritative database remains unidentified; owner approval is absent; a consistent protected backup or isolated restore rehearsal fails; backup ACL/encryption is not verified; rollback command/configuration is not preserved; process ownership cannot be tied to the listener; another writer could overlap; expected schema is unclear; or the maintenance window lacks a responsible operator. Abort the replacement before writes or traffic if source, interpreter, working directory, database target, revision, auto-create setting, health, or routes mismatch the approved values. Do not respond by selecting another database or running a migration.

## Remaining release blockers

- The authoritative database and live API source/runtime identity are unresolved.
- No protected backup and restore rehearsal of the identified real database is documented.
- No production deployment target or owner-approved remote configuration is identified.
- Hosted security, authenticated browser workflows, privacy/retention operations, provider licensing, and agricultural evidence approval remain separate open release gates as summarized in `docs/final-development-day-release-report.md`.
- The existing local API's weather-alert route response has since been observed as current; the earlier discrepancy was a schema-check reporting error. That does not resolve source or database identity.

## Commands/checks performed

Read-only checks for this report:

- `netstat -ano -p tcp | Select-String ':(8001|8501|5173)\s+.*LISTENING'` — recorded current listener addresses and PIDs.
- PowerShell listing of `data`, `.backups`, Gate 1 reports, migration files, and relevant config/source.
- `.venv\Scripts\python.exe -B -` with Python `os.walk`, `Path.resolve/stat`, and SQLite `mode=ro` connections over `data`, `.backups`, and named test artifact folders; queried only integrity, schema table names/count, and Alembic revision. No user rows were read.
- Read-only review of Gate 1 through 1F reports, `docs/phase-4-readiness-verification.md`, `docs/backend-phase-1.md`, `run_streamlit.ps1`, `backend/db.py`, `backend/api.py`, and `backend/migrations/env.py`.

The inventory is limited to discoverable project-local SQLite files; it is not a search of external disks, service accounts, network shares, cloud backups, or other project copies. Windows process metadata limitations from Gate 1F remain.

## Verdict

**BLOCKED — AUTHORITATIVE DATABASE UNRESOLVED**

The inventory found healthy current and historical SQLite files, but no evidence links any one of them to the live API or establishes it as the data owner's intended source of truth. Protected real-data backup and rollback are also not proven. Do not execute maintenance or proceed to migration/deployment until those blockers are resolved and the maintenance action receives separate explicit authorization.
