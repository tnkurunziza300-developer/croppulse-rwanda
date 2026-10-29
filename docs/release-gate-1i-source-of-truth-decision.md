# CropPulse Rwanda — Gate 1I: Source-of-Truth Decision and Evidence Checklist

**Prepared:** 2026-10-26  
**Project:** `C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda`  
**Purpose:** Decision package based on Gate 1H and prior release evidence. It does not select a database or authorize maintenance.

## Candidate comparison

The metadata below is from the read-only inventory recorded in [Gate 1G](release-gate-1g-maintenance-plan.md) and [Gate 1H](release-gate-1h-database-provenance.md). `integrity=ok` is a SQLite structural check only; it does not prove ownership, completeness, provenance, protection, or API use.

| Candidate | Documented role / evidence | Backup and restore status | Unresolved question |
|---|---|---|---|
| `data/croppulse_phase1.sqlite3` — 19,402,752 B; 2026-10-26; rev `0015`; 24 tables; integrity `ok` | `backend/db.py`, `.env.example`, `run_streamlit.ps1`, and setup docs use it as a local development default. This is evidence for local development use only. | No protected backup or real-data restore for this exact DB is documented. | Does the data owner designate it as the source of truth? Does PID 21152 actually use it? Is its data current and retention-approved? |
| `data/croppulse_local.sqlite3` — 8,192 B; no Alembic revision; 0 tables; integrity `ok` | Documented legacy/empty DB; setup docs warn against using it for current migrations. | No applicable restore evidence. | Confirm it remains a legacy artifact; do not promote it. |
| Historical files in `.backups/` and `data/backups/` — revisions `0002`–`0014`; integrity `ok` | Filenames indicate pre-migration or pre-feature snapshots. Names and schema revisions do not establish lineage or current authority. | No trusted catalog, protected storage verification, or real-data isolated restore documented. `.backups/` is documented as local, not encrypted/off-site. | Which, if any, are known-good recovery points for an owner-designated source? |
| `.test-runtime/phase4-recovery-.../isolated-test.sqlite3`, `.backup.sqlite3`, `.restored.sqlite3` — each 475,136 B; rev `0015`; integrity `ok` | Explicit `TEST_ONLY` synthetic source, backup, and restore from Phase 4. Not a real-data candidate. | Synthetic restore mechanics passed; ACL protection was not verified. Does not prove production recovery. | None for authority; retain as test artifacts. |
| Other `.test-runtime`, `.backend-check-tmp`, `.pytest-tmp` databases | Test, migration, or smoke-check artifacts per Gate 1G inventory. | No production recovery evidence. | Keep classified as test artifacts. |

Historical candidate paths recorded in Gate 1H:

- `.backups/before-saved-weather-forecasts-20261022-092122.sqlite3` (rev `0012`, 19,271,680 B); `.backups/before-weather-outlook-records-20261022.sqlite3` (rev `0013`, 19,271,680 B).
- `.backups/croppulse_phase1-before-crop-health-f2b1bc4d.sqlite3` (rev `0009`, 1,540,096 B); `.backups/croppulse_phase1-before-password-recovery-20261020.sqlite3` (rev `0003`, 155,648 B); `.backups/croppulse_phase1-before-weather-bulletins.sqlite3` (rev `0011`, 1,540,096 B).
- `.backups/croppulse_phase1_before_0008_20261021.sqlite3` (rev `0007`, 286,720 B); `.backups/croppulse_phase1_before_0009_crop_health_20261021.sqlite3` (rev `0008`, 307,200 B); `.backups/croppulse_phase1_pre_0006_20261020.sqlite3` (rev `0005`, 192,512 B); `.backups/croppulse_phase1_pre_0007_20261020.sqlite3` (rev `0006`, 241,664 B).
- `.backups/pre-react-migration-20261016/croppulse_phase1.sqlite3` (rev `0002`, 81,920 B); `.backups/pre-react-migration-20261016/croppulse_local.sqlite3` (no Alembic revision, 16,384 B).
- `data/backups/croppulse_phase1_before_weather_alerts_20261022_174642.sqlite3` and `...174716_292005.sqlite3` (both rev `0014`, 19,271,680 B).

The NISR `data/verified/MANIFEST.json` is for the statistics CSV, not farmer/application database lineage.

## Keep these identities separate

1. **Local development default:** `data/croppulse_phase1.sqlite3` when `CROP_PULSE_DATABASE_URL` is unset and the process working directory is the project root. This is confirmed by source and setup documentation.
2. **Live API database:** unknown. PID 21152's source tree, working directory, environment, and effective SQLAlchemy target remain unverified. Health and routes do not identify the database.
3. **Authoritative farmer-record store:** unknown. This is an organizational data-governance decision; code defaults, filenames, timestamps, revisions, and integrity checks cannot make it.

## Data-owner decision record

The accountable data owner/records custodian should complete this in the organization's controlled approval system. Do not guess missing values. If provenance cannot distinguish candidates, record that no database is currently designated and keep release blocked.

```text
CropPulse Rwanda — Authoritative database designation

Decision: [ ] Designate one database  [ ] No candidate can currently be designated
Data owner / records custodian (identity and role):
Organization:
Approver(s), approval date/time, and second approver if required:

Exact canonical identity:
  SQLite: absolute path and checksum/evidence reference
  Managed DB: approved provider/instance/database identifier
  (No credentials, passwords, tokens, or raw connection URL.)
Environment: [ ] development [ ] test [ ] staging [ ] production
Intended role and record scope:
May contain real farmer/application records? [ ] Yes [ ] No [ ] Unknown
Data custodian, retention policy, and intended service owner:

Basis for designation (trusted operational records, lineage, backup IDs):
How continuity was checked without exposing farmer records:
Why other candidates are historical, excluded, or retained:
Known gaps/restrictions:
Schema revision and compatibility status (not migration authorization):
Backup record ID and protected destination reference:
Isolated restore record ID/date/result:
Recovery owner, retention, and agreed recovery objectives:

Approval reference/signature:
Independent approver (if required):
Governance/change ticket and next review date:

This designation alone does not authorize restart, migration, restore, copy,
promotion, production traffic switch, or deployment. Separate approval is required.
```

## Service-owner runtime evidence checklist

The service owner/operator must provide sanitized evidence for the intended API. Do not record raw environment dumps, full credential-bearing URLs, signing secrets, tokens, or farmer records. If a field cannot be read safely, mark it unavailable rather than infer it.

- [ ] Timestamp, observer, listener address/port, and PID.
- [ ] Process owner/supervisor and parent relationship verified with approved Windows tooling.
- [ ] Executable and Python environment (`sys.executable`, `sys.prefix`).
- [ ] Working directory, launch target, and imported `backend.api.__file__` tied to the approved project tree.
- [ ] Effective configuration source identified; secret values omitted.
- [ ] Running SQLAlchemy engine dialect and effective database target resolved (not inferred from source fallback).
- [ ] SQLite: canonical absolute path / `PRAGMA database_list` matches owner decision. Managed DB: approved sanitized provider/instance/database identity matches.
- [ ] Auto-create setting and startup behavior recorded; no migration/schema creation performed for this evidence.
- [ ] Read-only revision/integrity evidence for that exact target, without personal-record queries.
- [ ] Health/OpenAPI recorded only as supporting checks, not database identity proof.
- [ ] Service owner and data owner reconcile discrepancies and approve the resulting evidence.

Until complete, the live API remains **unidentified**. A controlled restart may verify an explicitly approved target later; it must not be used to choose a target by trial and error.

## Backup and isolated-restore prerequisites

Before maintenance involving an owner-designated database:

1. Confirm exact target, write-freeze procedure, and one-writer plan with the data and service owners.
2. Create a consistent backup of that exact target using a database-supported method. For SQLite, quiesce writers or use SQLite's online backup mechanism and account for WAL/journal state; do not raw-copy an actively written main file.
3. Store it outside the project/web root in an owner-approved encrypted, access-controlled destination. Verify ACLs with authorized and unauthorized identities; record checksum, time, operator, retention, and backup ID.
4. Restore to a distinct isolated location that cannot serve production traffic. Never overwrite the source or another candidate during rehearsal.
5. Verify integrity, foreign-key constraints, schema revision, and owner-approved non-sensitive consistency checks. Record results without names, contacts, messages, or private rows.
6. Record restore procedure/operator/result, recovery contact, elapsed time, and agreed RPO/RTO. Claim recovery only for the exact identified database tested.
7. Obtain separate written maintenance approval after the rehearsal. These checks do not authorize migration, service replacement, promotion, or traffic switch.

The Phase 4 restore evidence used synthetic data and does not satisfy these real-data requirements.

## Blockers and next authorized action

- The local development default is documented; the live API's effective database is not.
- No data-owner designation identifies the authoritative farmer/application record store.
- No protected backup and isolated restore for that designated real-data store is documented.
- PID 21152's source/runtime/database identity remains unverified; prior gates document Windows process-inspection limits.
- Historical backups have no trusted database-lineage manifest or approved production-backup record.

**Next action:** ask the organization's data owner/records custodian to complete the designation record using trusted operational evidence, and the service owner to complete the runtime checklist. If candidates cannot be distinguished, record “no candidate can currently be designated” and pause maintenance/deployment. After designation, arrange a separately authorized protected backup and isolated restore rehearsal for that exact target. This is a governance decision that more code inspection alone cannot resolve.

No database was selected, copied, promoted, restored, migrated, or modified. No service was stopped or restarted. Gate 1 remains blocked.
