# CropPulse Rwanda — Gate 1H: Authoritative Database Provenance Investigation

**Audit date:** 2026-10-26 (Africa/Johannesburg)  
**Project root:** `C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda`  
**Scope:** Read-only review of project documentation, configuration, logs/records discoverable in the repository, migration history, and the database inventory recorded in Gate 1G. No service or database was changed.

## Executive finding

Project setup documentation explicitly uses `data/croppulse_phase1.sqlite3` as the **local development** database default and provides migration/account setup examples using that URL. It explicitly distinguishes local SQLite from production and warns that the file is not a production backup strategy. This is evidence for the intended local development target, but it does not establish that this is the live API's database, the database the organization intends to retain as its source of truth, or the authoritative repository of farmer records.

No reviewed technical or documentary record identifies a data owner-approved authoritative database. The API listener's runtime database remains unverified. The synthetic Phase 4 recovery drill does not constitute a backup/restore rehearsal for real farmer records. No database is selected or promoted by this report.

## Candidate inventory

The metadata below was collected in Gate 1G through read-only SQLite URI connections (`mode=ro`). Only file metadata, `PRAGMA integrity_check`, table names/count, and `alembic_version` were inspected. No personal records were queried or displayed. Modification times are local filesystem timestamps. Integrity means SQLite found no structural corruption; it does not prove ownership, completeness, provenance, backup quality, or connection to the live service.

| Canonical path (relative to project root) | Size | Modified (local) | Revision / tables | Integrity | Provenance evidence and assessment |
|---|---:|---|---|---|---|
| `data/croppulse_phase1.sqlite3` | 19,402,752 B | 2026-10-26 11:49:40 | `0015_weather_alert_foundation` / 24 | `ok` | `.env.example`, `backend/db.py`, `run_streamlit.ps1`, and React setup docs use this as the default/local development URL. This is the strongest evidence of intended *local development* use. There is no owner attestation or PID-to-file evidence. It is not thereby proven authoritative for deployment or current live records. |
| `data/croppulse_local.sqlite3` | 8,192 B | 2026-10-21 08:01:56 | no Alembic version / 0 | `ok` | Docs identify this as a legacy empty DB and warn not to point Alembic at it. Evidence weighs against it being the current application DB. |
| `.backups/before-saved-weather-forecasts-20261022-092122.sqlite3` | 19,271,680 B | 2026-10-22 09:13:54 | `0012_weather_bulletins` / 20 | `ok` | Pre-change-looking name and older schema; no signed manifest, owner designation, or restore result tied to real records. Not the current live target by any proven evidence. |
| `.backups/before-weather-outlook-records-20261022.sqlite3` | 19,271,680 B | 2026-10-22 09:37:03 | `0013_saved_weather_forecasts` / 21 | `ok` | Historical-looking snapshot. No verified lineage or owner-approved restore evidence. |
| `.backups/croppulse_phase1-before-crop-health-f2b1bc4d.sqlite3` | 1,540,096 B | 2026-10-21 23:55:41 | `0009_crop_health_cases` / 19 | `ok` | Historical pre-change-looking snapshot; older schema and unknown relation to any live service. |
| `.backups/croppulse_phase1-before-password-recovery-20261020.sqlite3` | 155,648 B | 2026-10-20 16:25:07 | `0003_roles_review_and_admin` / 10 | `ok` | Historical named snapshot; old schema. No evidence it is an authoritative live copy. |
| `.backups/croppulse_phase1-before-weather-bulletins.sqlite3` | 1,540,096 B | 2026-10-22 08:54:58 | `0011_crop_health_ai_screening` / 19 | `ok` | Historical named snapshot; old schema and unverified lineage. |
| `.backups/croppulse_phase1_before_0008_20261021.sqlite3` | 286,720 B | 2026-10-21 10:11:52 | `0007_fields_and_evidence` / 16 | `ok` | Migration-named historical snapshot; not a current-schema candidate. |
| `.backups/croppulse_phase1_before_0009_crop_health_20261021.sqlite3` | 307,200 B | 2026-10-21 14:38:08 | `0008_streamlit_handoff` / 17 | `ok` | Migration-named historical snapshot; not a current-schema candidate. |
| `.backups/croppulse_phase1_pre_0006_20261020.sqlite3` | 192,512 B | 2026-10-20 20:21:05 | `0005_self_service_account` / 11 | `ok` | Migration-named historical snapshot; not a current-schema candidate. |
| `.backups/croppulse_phase1_pre_0007_20261020.sqlite3` | 241,664 B | 2026-10-20 20:29:30 | `0006_private_messaging` / 14 | `ok` | Migration-named historical snapshot; not a current-schema candidate. |
| `data/backups/croppulse_phase1_before_weather_alerts_20261022_174642.sqlite3` | 19,271,680 B | 2026-10-22 17:46:42 | `0014_weather_bulletin_records` / 22 | `ok` | Weather-alert pre-change name; no signed backup manifest, owner designation, or real-data restore proof. |
| `data/backups/croppulse_phase1_before_weather_alerts_20261022_174716_292005.sqlite3` | 19,271,680 B | 2026-10-22 17:47:16 | `0014_weather_bulletin_records` / 22 | `ok` | Similar name, size, revision and close timestamp do not establish identical contents or a trusted backup chain. |
| `.backups/pre-react-migration-20261016/croppulse_phase1.sqlite3` | 81,920 B | 2026-10-16 17:09:14 | `0002_revocable_sessions` / 6 | `ok` | React migration audit identifies this as an implementation backup; old schema. It is historical recovery evidence, not the current target. |
| `.backups/pre-react-migration-20261016/croppulse_local.sqlite3` | 16,384 B | 2026-10-16 17:09:14 | no Alembic version / 3 | `ok` | Historical legacy DB copy; documentation says not to use the legacy file for current migrations. |
| `.test-runtime/phase4-recovery-3f5e0732384149d7b6201b3677958bc4/isolated-test.sqlite3` | 475,136 B | 2026-10-26 08:49:24 | `0015_weather_alert_foundation` / 24 | `ok` | Phase 4 explicitly identifies this as a fresh synthetic `TEST_ONLY` recovery source. Not real farmer data and not an authoritative candidate. |
| `.test-runtime/phase4-recovery-3f5e0732384149d7b6201b3677958bc4/isolated-test.backup.sqlite3` | 475,136 B | 2026-10-26 08:49:24 | `0015_weather_alert_foundation` / 24 | `ok` | Backup of the synthetic source only. ACL protection was not verified. Not a production backup. |
| `.test-runtime/phase4-recovery-3f5e0732384149d7b6201b3677958bc4/isolated-test.restored.sqlite3` | 475,136 B | 2026-10-26 08:49:24 | `0015_weather_alert_foundation` / 24 | `ok` | Isolated restore of the synthetic backup only. Not evidence of real-data recovery. |

Other files under `.test-runtime`, `.backend-check-tmp`, and `.pytest-tmp` are migration/test/smoke-check artifacts. Gate 1G inventoried these and did not treat them as production candidates. The repository contains no reviewed database-side manifest that maps a candidate to a service or data owner. `data/verified/MANIFEST.json` is a manifest for the NISR agricultural statistics CSV, not a manifest for farmer/application databases.

## Existing documentary and technical evidence

### Facts

- `backend/db.py` and `backend/migrations/env.py` read `CROP_PULSE_DATABASE_URL`, falling back to `sqlite:///./data/croppulse_phase1.sqlite3`. The relative SQLite path is resolved from the process working directory.
- `.env.example` labels this fallback as the local SQLite default. The project setup guide uses it in local commands for API, migrations and administrator provisioning; it says these must use the same URL.
- `run_streamlit.ps1` sets that SQLite URL only when it launches a new local API. When port 8001 already has an API listener that passes readiness checks, it reuses that process and does not establish or replace its environment.
- Setup documentation says to stop API writers before copying SQLite, keep backups restricted, and run an integrity check. It states `.backups/` is local, gitignored, and not off-site or encrypted. It warns that restoring an older backup can remove records written since the backup.
- The documented pre-react migration snapshot is described as an implementation audit backup. Migration-named files and filenames indicate development operations but are not signed, owner-approved records of the current source of truth.
- The available migration chain proceeds from `0001_phase1_records` to `0015_weather_alert_foundation`. A schema revision is not identity evidence; multiple test and historical files also have revisions in this chain.
- Gate 1 through Gate 1G report that PID 21152's working directory, module path, inherited DB setting, and actual SQLAlchemy target were not established. Health and OpenAPI checks do not identify the database.
- The isolated Phase 4 restore test used a newly created synthetic database. It does not verify backup/recovery of any candidate with real farmer records. Its artifact ACL was not verified as restrictive.
- The repository copy has no `.git` directory, as documented in the final development report. Thus commit history and database-related source-control history are not available in this copy. Prior local shell-history review did not tie launch commands to the current PID.

### Evidence that supports `data/croppulse_phase1.sqlite3` as a local development database

- It is the source's default when no environment override is provided.
- The setup instructions explicitly use it for local migration and app setup.
- The current candidate schema matches the source migration head and passed its structural integrity check.

### Evidence against treating that evidence as proof of authoritative/live status

- The same source permits an environment override; process CWD also affects relative SQLite paths.
- The launcher may reuse an unrelated already-running API without reconfiguring it.
- The documentation calls this local development setup and expressly says local SQLite is not a production backup strategy.
- No PID-to-module-to-engine-to-canonical-file evidence exists for the running API.
- No data owner has designated the file, its purpose, its expected owner/account set, or its retention status. The file's size, most recent timestamp and revision cannot supply that decision.

### Logs and operational records

Repository launch/log references are dated local development artifacts and previous reports say they do not establish the current PID's launch. No reviewed service registration, deployment manifest, environment record, backup catalog, database manifest, or owner-approved change record links PID 21152 to a database. The local logs and history available to this workspace cannot prove the effective database or organizational intent. No raw log lines containing process environment or credentials were copied into this report.

## Proven facts versus hypotheses

| Statement | Status |
|---|---|
| `data/croppulse_phase1.sqlite3` is the documented default for local development. | **PROVEN by source and setup docs.** |
| The candidate is structurally readable and at source head `0015`. | **PROVEN for that file at the Gate 1G inspection time only.** |
| PID 21152 uses that candidate. | **UNPROVEN.** |
| The candidate is the organization's intended authoritative farmer-record database. | **UNPROVEN; requires accountable data-owner decision and corroborating provenance.** |
| The older `.backups` files are complete, consistent, protected production backups. | **UNPROVEN.** Filenames and integrity checks alone are insufficient. |
| The Phase 4 synthetic restore proves farmer-data recovery. | **FALSE.** It proves only a restore of a fresh synthetic DB, with ACL protection unresolved. |
| Some historical backups may derive from earlier copies of the same development database. | **POSSIBLE HYPOTHESIS only; no cryptographic lineage or data-owner confirmation was established.** |

## Backup and restore status

The repository has SQLite snapshots with historical migration revisions and local backup procedures. Gate 1G checked candidate integrity but did not perform restores of these snapshots or verify their access restrictions. Setup docs expressly state the local `.backups/` directory is not encrypted or off-site. The only reported restore rehearsal used synthetic data under `.test-runtime`; restrictive ACL protection could not be verified. No protected backup and successful isolated restore of the data owner's identified farmer database is documented.

This is a separate blocker from provenance: even after an owner identifies the source of truth, that database still needs an approved, consistent backup and a successful restore rehearsal to a different isolated target before maintenance.

## Required data-owner decision

The authoritative-database designation belongs to the organization/person accountable for CropPulse farmer data (the formally appointed data owner or records custodian), with the service owner/operator supplying technical runtime evidence. A developer or operator can explain configuration but cannot infer organizational ownership from a filename, latest write, schema revision, integrity check, or successful health response.

The data owner must establish whether the intended source is one of these local files, a different local copy, an external/network/managed database, or no current database approved for real farmer records. If evidence cannot distinguish candidates, the safest outcome is to pause release and preserve all copies unchanged until the owner resolves lineage. Do not merge or promote candidate files as part of this investigation.

## Minimum approval record before any database is accepted as authoritative

Store the approval in the organization's controlled change/data-governance record, not solely in the project repository. It should contain:

1. The approving data owner's identity/role, organization, approval date/time, and any required second approver.
2. The exact canonical database identity: absolute path for SQLite, or sanitized provider/instance/database identity for a managed database. Keep credentials out of the record.
3. The intended environment and purpose (local development, test, staging, or production); whether real farmer records may exist there; data owner/custodian and retention policy.
4. Provenance supporting the designation: source of the file/service configuration, known continuity/creation history, any matching checksums or trusted backup records, and why other candidates are excluded or retained as historical.
5. Service owner evidence tying the intended API process configuration to the approved source and DB. For the live service, include source path, executable/environment, working directory, process/supervisor identity, and resolved effective DB target with secrets redacted.
6. Current schema revision and compatibility decision. Do not include migrations in this gate; any migration needs separate review and authorization.
7. Backup record: creation method/time, checksum, protected destination and ACL/encryption verification, retention, operator, and successful isolated restore evidence for this exact database.
8. Rollback/recovery plan, responsible operator, maintenance authorization, and decision if recovery changes any records after the backup point.

## Stop conditions and safest next action

Stop release and maintenance planning before service interruption if the data owner cannot identify the intended database from trusted operational records. Preserve all files and existing services; do not test a guessed DB with write-capable app flows, apply migrations, copy over a candidate, or let multiple API processes write to the same SQLite file.

Next action: obtain the accountable data owner's written designation (or written statement that no candidate can currently be designated) and the service owner's sanitized runtime/configuration evidence. If they designate a DB, perform a separately approved protected backup and isolated restore rehearsal for that exact target. Only then prepare a separate maintenance authorization. This report itself authorizes none of those operations.

## Checks performed

- Read `docs/release-gate-1g-maintenance-plan.md`, Gate 1 through Gate 1F reports, `docs/final-development-day-release-report.md`, `docs/react-app-setup.md`, `docs/backend-phase-1.md`, `README.md`, `data/README.md`, `.env.example`, `run_streamlit.ps1`, `backend/db.py`, `backend/migrations/env.py`, and the migration filenames through `0015`.
- Listed backup and database artifact names and reviewed their already-recorded Gate 1G metadata. The Gate 1G metadata query used read-only SQLite mode and queried only file metadata, integrity, table names/count, and migration version.
- Searched repository documentation/configuration for the database URL, candidate filenames, backup/restore guidance, and authoritative designation. `data/verified/MANIFEST.json` was identified as an NISR data manifest, unrelated to database lineage.
- Confirmed there is no `.git` directory in this project copy. Some recursive repository searches report access denied on temporary pytest directories; those directories are not needed to determine documentary authority. No database connection, process action, migration, write, or private-record query was performed during Gate 1H.

## Verdict

**BLOCKED — PROVENANCE EVIDENCE INSUFFICIENT**

There is documentary support for one local development default, but no data-owner designation or runtime evidence links that database to the running API or establishes it as the authoritative record store. Protected backup and real-data restore are independently unproven. No candidate was selected, promoted, migrated, or modified. Gate 1 remains blocked.
