# CropPulse Rwanda — Phase 4 Readiness Verification

**Verification date:** 2026-10-26  
**Repository path:** `C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda`  
**Baseline:** [Full System Audit and Remediation, Phase 3](full-system-audit-remediation-phase-3.md), dated 2026-10-23.  
**Readiness verdict:** **Development only.**

## 1. Executive summary

The Phase 3 baseline remains broadly accurate. This pass reran the full Python and frontend checks, reviewed API-level security and farmer/reviewer/admin workflow tests, checked the local SQLite candidates read-only, verified the agronomic registry and NISR checksum, and performed a backup/restore exercise against a new, isolated database containing only synthetic test records.

Automated verification is strong for local route logic and database-backed API behavior, but it does not establish browser usability, hosted deployment security, live SMTP behavior, external-provider availability, or a production recovery objective. No browser automation tool or browser driver is available in this environment. No application service was started and no real farmer or administrator credentials were used.

No application code defect was confirmed in this pass, so no application code or existing database schema was changed. The recovery drill created a synthetic SQLite database, backup, and restored copy beneath `.test-runtime/phase4-recovery-3f5e0732384149d7b6201b3677958bc4/`. Attempts to apply a restrictive ACL made the artifacts unreadable to the normal workspace process; inherited ACLs were restored. The final test backup is therefore **not claimed to have a verified restrictive ACL**. It contains synthetic data only and is not encrypted or off-site.

The project remains unsuitable for a farmer pilot or public production: the approved agronomic-rule registry has zero rules; agricultural source reuse and model licensing remain unresolved; authenticated browser workflows and live email delivery remain unverified; and hosted rate/concurrency controls, monitoring, privacy operations, and production recovery are not established.

## 2. Baseline and repository-state findings

### Repository and local configuration

- The requested project directory exists and contains the React app under `frontend/`, FastAPI under `backend/`, Streamlit entry point `app.py`, Alembic migrations, tests, and the Phase 2/3A/3 audit records.
- Git status could not be obtained: the `git` command is unavailable and the project root has no `.git` directory. Existing source changes therefore cannot be classified as committed, modified, or untracked. No source files were overwritten in this phase.
- The root has `.env.example` but no root `.env` file. `frontend/.env` and `frontend/.env.local` exist; only variable names were inspected, not values. Both define `VITE_API_BASE_URL`. They were left unchanged.
- `CROP_PULSE_DATABASE_URL` is unset in the verification process. `backend/db.py` defaults to `sqlite:///./data/croppulse_phase1.sqlite3`, relative to the API process working directory; an environment override selects another database. This does not establish a separate live service's database target.
- The local candidate `data/croppulse_phase1.sqlite3` passed read-only `PRAGMA integrity_check` (`ok`) and `PRAGMA foreign_key_check` (zero violations), at revision `0015_weather_alert_foundation`, with 24 tables. `data/croppulse_local.sqlite3` also passed integrity checks but has no application tables or Alembic revision. Neither file was modified.
- Startup only calls `Base.metadata.create_all()` when `CROP_PULSE_AUTO_CREATE_SCHEMA=1`. The production/staging startup checks and migration policy are covered by existing tests. No service was launched, no migration was applied to either existing database, and no server environment was inspected.

### Browser capability and service availability

- No browser tool is available in the agent environment. `playwright`, `selenium`, and `pytest-playwright` are not installed, and no Edge/Chrome/Chromium or driver executable was found on `PATH`.
- The FastAPI and Vite services were not started. Frontend React tests run in the project's jsdom/Vitest test environment; API integration tests use FastAPI `TestClient` and per-test SQLite databases. These are not browser end-to-end evidence.
- The Windows test runner creates project-local temporary directories under `.test-runtime`; its API fixtures use unique SQLite filenames and remove their per-test database files after completion.

## 3. Work performed and files changed

No application code, model, migration, environment file, verified dataset, or existing database changed.

- `docs/phase-4-readiness-verification.md` — this Phase 4 verification report, findings, evidence, and repeatable browser checklist.
- `README.md` — link to this report.
- `.test-runtime/phase4-recovery-3f5e0732384149d7b6201b3677958bc4/isolated-test.sqlite3` — fresh disposable database upgraded through the existing migration head and populated with one synthetic farmer and one synthetic farm.
- `.test-runtime/phase4-recovery-3f5e0732384149d7b6201b3677958bc4/isolated-test.backup.sqlite3` — SQLite backup of that synthetic database.
- `.test-runtime/phase4-recovery-3f5e0732384149d7b6201b3677958bc4/isolated-test.restored.sqlite3` — separate restore target copied from the isolated backup.

The test directory and database files contain only synthetic test data and are retained. Inherited ACLs were restored after ACL hardening blocked normal workspace access; the artifacts are not treated as a protected backup of real data.

## 4. Findings

Severity describes readiness impact in the inspected local environment; it is not a penetration-test rating.

| ID / severity | Finding and evidence | Status and next action |
|---|---|---|
| P4-01 — **High** | Authenticated browser workflows for farmer, reviewer, and administrator have not been executed. No browser or browser-driver capability is installed here. Existing React tests use jsdom, and API tests use in-process `TestClient`. | **Blocked.** Run the browser checklist below on an isolated development database using disposable accounts and a supported browser. Do not onboard farmers based on unit/API tests alone. |
| P4-02 — **High** | No approved, current, scoped agronomic rules exist. The registry validator reports zero rules and zero approved rules. Provisional crop rankings/calendar entries remain unverified. | **Open / external review required.** Obtain traceable local evidence and qualified independent review, then use the existing approval workflow. Do not transform NISR descriptive statistics into advice. |
| P4-03 — **High** | Hosted HTTPS/proxy trust, general API rate/concurrency controls, monitoring, incident response, hosted secrets, and production logs were not inspected or load-tested. Only sensitive account-action throttles and request body limits are covered by local source/tests. | **Blocked on deployment owner.** Configure and verify gateway limits, TLS/proxy settings, monitoring, safe logging, secrets, and recovery controls in staging. |
| P4-04 — **High** | The effective database for any live service is unknown. The verification shell had no database URL override; the local default candidate is healthy at revision 0015, but this does not identify another process's target. | **Open.** The operator must confirm the service's process, working directory, and database URL through a sanitized runtime diagnostic before any production backup or migration. |
| P4-05 — **High** | Open-Meteo free service terms limit use to non-commercial purposes and publish call caps and CC BY 4.0 attribution; CropPulse's intended deployment/commercial status is undecided. METEO RWANDA/NISR reuse terms are not confirmed. | **Open / legal and provider decision.** Select a suitable service/license and obtain source-specific permissions before redistribution or commercial deployment. |
| P4-06 — **High** | The PlantVillage mirror currently labels the dataset CC BY-SA 3.0. The local snapshot does not document a pinned immutable source revision; model-weight obligations and use in a public/commercial service have no legal determination. | **Open.** Preserve attribution, pin provenance, and obtain qualified licensing review before redistributing or relying on the model as a farmer diagnosis. |
| P4-07 — **High** | Farmer identifiers, farm coordinates, messages, crop-health photos, and account records persist. A complete retention/deletion/access-request, breach, support, and residency policy is not approved. | **Open / organizational and legal owner.** Establish and implement privacy, retention, deletion/export, and incident procedures before a pilot. |
| P4-08 — **Medium** | Password recovery/email-change behavior has local regression tests, but real SMTP delivery and provider failure behavior were not exercised. | **Partially verified.** Test with a non-production mail sink and disposable accounts after SMTP is configured. Do not send real email as part of this audit. |
| P4-09 — **Medium** | Git baseline cannot be inspected because this copy has neither an available Git executable nor a `.git` directory. | **Blocked by repository metadata/tooling.** Provide a version-controlled checkout or Git tooling for future change attribution. No source edits were made in this pass. |
| P4-10 — **Medium** | The plain `npm test` command fails before collecting tests because Vite's config bundler receives Windows `spawn EPERM`. The repository-native config-loader invocation succeeds. | **Workaround verified.** Continue using the native config loader in this managed Windows environment or fix the local execution policy/tooling separately; do not disable tests. |
| P4-11 — **Partially verified / blocked** | An isolated database migrated to `0015`, was backed up, restored to a separate file, and passed schema/revision, SQLite integrity, FK, and synthetic-row checks. ACL restriction attempts made the files unreadable; inherited ACLs were restored. | **Restore mechanics passed for synthetic data.** The backup is not verified access-restricted, encrypted, or off-site. Before any real-data drill, use an operator-controlled protected destination. No RPO/RTO was measured. |
| P4-12 — **Verified locally** | Existing Phase 3.1 intake publication and Phase 3 NISR checksum regression remain covered. Registry validation is current and the NISR file hash matches its existing manifest. | **No new defect found.** Zero approved rules remains the correct registry state. |

## 5. Workflow verification and evidence

### Automated/API verification

The full Python suite and focused API integration group passed. Their real route-handler and persistence assertions include:

- Registration, hashed passwords, browser sign-in/out, CSRF, cookie attributes, session expiry/revocation, and rejection of role self-assignment.
- Farmer ownership checks for farms, fields, activities, crop plans, private weather data, crop-health reports/photos, and messaging conversations.
- Crop-plan persistence and lifecycle validation.
- Reviewer district assignment boundaries, reviewer-only access, and immutable review decisions.
- Administrator-only role/status/permission controls, audit events, reviewer assignments, messaging settings, and protection against last-admin self-deletion.
- Private message access, unread/read state, and re-evaluation of reviewer/farm district scope.
- Crop-health report upload validation, private photo access, unsupported crop/model behavior, and reviewer follow-up.
- Weather coordinate validation, saved forecast ownership/stale status, forecast provider failure fallback, malformed provider responses, and alert preference/history behavior.
- Password reset/email change token single-use, expiry/revocation behavior, and safe account deletion paths in isolated test databases.

These checks do not prove a React browser rendered each state correctly, a live external weather call succeeded, or a hosted SMTP relay delivered mail. Tests that mock providers remain provider-adapter tests, not external service verification.

### Reproducible browser checklist prepared; not executed

To avoid touching the current local database, run the future manual/browser pass against a fresh, disposable database and browser test accounts:

1. From the repository root, choose a new database path under `.test-runtime`, set `CROP_PULSE_DATABASE_URL` to that SQLite URL, set a newly generated local-only `CROP_PULSE_SECRET_KEY`, set `CROP_PULSE_ENVIRONMENT=development`, `CROP_PULSE_COOKIE_SECURE=0`, and set `CROP_PULSE_CORS_ORIGINS=http://127.0.0.1:15173`. Keep `CROP_PULSE_AUTO_CREATE_SCHEMA` unset or `0`.
2. Run `alembic upgrade head` with that exact temporary database URL, then run FastAPI on `127.0.0.1:18001`. Do not point the command at `data/croppulse_phase1.sqlite3`.
3. In `frontend/`, set the process-only `VITE_API_BASE_URL=http://127.0.0.1:18001` and run Vite on `127.0.0.1:15173`. Confirm the API CORS allowlist matches that origin.
4. In a browser, register two disposable farmers. Verify sign-in, reload/session persistence, sign-out, invalid credentials, expiry, and that farmer A cannot retrieve or mutate farmer B's farm, plan, activity, photo, weather record, or conversation by changing a URL/ID or request payload.
5. Create farmer A's farm/field, activity, and crop plan. Save, reload, edit an allowed planned record, test invalid lifecycle changes, and confirm persisted state. Confirm recommendations remain labeled provisional and disclose missing approved evidence.
6. Use the explicit first-admin operator command only against this isolated database. From the UI, grant a separate disposable account reviewer role and a test district. Verify the reviewer sees and updates only assigned-district eligible crop-health reports/conversations; try a second unassigned district and a farmer account to confirm denial.
7. As admin, test account status/session revocation, reviewer assignment, admin audit events, and messaging enable/disable. As farmer, test eligible reviewer discovery, conversation creation, message send, unread count, explicit mark-read, and denial after district assignment/status changes.
8. Submit a synthetic non-sensitive image to crop health; confirm the result is presented as experimental screening, with uncertain/non-diagnostic language and reviewer follow-up. Verify an unsupported crop does not receive a fabricated model diagnosis.
9. Test weather with coordinates inside/outside the supported Rwanda extent, confirm units/source/retrieval time/staleness labels, and use the existing automated adapter tests for malformed-provider and forced-failure cases. A live provider request is a separate external network check and should not be described as deterministic browser coverage.
10. Test account recovery/email change only with a local mail sink or other approved non-production SMTP. Do not use real farmer addresses. If SMTP is absent, record the UI/API unavailable path instead of claiming delivery.

This is a reproducible manual plan, not a completed browser test suite. No account from this plan was registered in this phase; all automated API-created accounts use test fixtures and isolated databases.

## 6. Exact verification record

Commands below ran from the project root unless the command explicitly says `frontend`.

| Command/check | Result |
|---|---|
| `git status --short --branch` | **Unavailable:** `git` is not recognized in this environment. `.git` is absent in the project root. |
| `\.venv\Scripts\python.exe tests\windows_safe_pytest.py` | **159 passed, 1 warning** in 137.03 seconds. Warning: AnyIO was already imported before pytest assertion rewriting. |
| `\.venv\Scripts\python.exe tests\windows_safe_pytest.py tests\test_backend_api.py tests\test_react_security_api.py tests\test_crop_health_api.py tests\test_weather.py tests\test_weather_alert_rules.py tests\test_plan_lifecycle_migration.py` | **59 passed, 1 warning** in 48.99 seconds; same AnyIO rewrite warning. |
| From `frontend`: `npm test` | **Failed before tests started** while loading Vite config: Windows `spawn EPERM` in `externalize-deps`. No tests were disabled. |
| From `frontend`: `npm test -- --configLoader native --pool=threads --maxWorkers=1` | **35 passed across 4 files.** |
| From `frontend`: `npm run typecheck` | **Passed.** |
| From `frontend`: `npm run lint` | **Passed.** |
| From `frontend`: `npm run build -- --configLoader native` | **Passed**; production bundle built successfully. |
| `utils.agronomy_knowledge.validate_pack()` | **valid=true**, current manifest, zero findings, zero agronomic rules, zero approved rules; NISR integrity valid, 2,020 rows. |
| NISR SHA-256 vs `data/verified/MANIFEST.json` | **Match:** `98de5073d00f60231df496da3c19912834a3156a7f2f044bd6eaa5108f313927`. |
| Read-only existing SQLite checks | `data/croppulse_phase1.sqlite3`: integrity `ok`, 0 FK violations, revision `0015_weather_alert_foundation`. `data/croppulse_local.sqlite3`: integrity `ok`, 0 FK violations, no app revision/tables. |
| Isolated recovery exercise | Fresh synthetic DB migrated from base to `0015_weather_alert_foundation`; source, backup, and restored DB each returned integrity `ok`, 0 FK violations, same revision, and exactly one synthetic farmer and farm. Backup and restore used SQLite's backup API; measured combined migration/write/copy/check procedure was 0.96 seconds. This is not an RPO/RTO measurement. |
| Recovery test-directory ACL | Initial `Set-Acl` was denied. A scoped elevated `icacls` ACL change then made the artifacts unreadable to the normal workspace process. Inherited ACLs were restored on that test directory only; afterward the normal process reopened all three databases and repeated `integrity_check` successfully. Final directory `AreAccessRulesProtected=False`. ACL protection is **not verified**. |

## 7. Data, database, and migration preservation

- The existing local Phase 1 database and legacy empty database were queried read-only only. Their records were not printed or modified.
- No migration was applied to either existing database. Alembic upgrades ran only against the new synthetic recovery database under `.test-runtime`.
- The NISR CSV and `data/verified/MANIFEST.json` were not changed. The CSV SHA-256 still matches the manifest.
- Agronomic source/rule/review files and derived Phase 3 registry artifacts were not changed in Phase 4. The registry remains valid with zero approved rules.
- No real farmer or administrator account was created or used. Test suite accounts use throwaway SQLite fixtures; the recovery database contains only `TEST_ONLY` synthetic rows.
- The synthetic test backup is not verified as ACL-restricted, encrypted, off-site, or part of a scheduled backup system. No real-data restore was performed. The failed ACL-hardening attempt and inherited-ACL restoration affected only this disposable test directory.

## 8. External, agricultural, privacy, and operational blockers

- **Open-Meteo:** the current terms state the free API is for non-commercial use, with limits below 10,000 calls/day, 5,000/hour, and 600/minute and CC BY 4.0 attribution; the service disclaims data accuracy/availability warranties. Paid subscriptions provide a commercial-use licence. CropPulse's deployment classification, plan, and cost approval remain open. Terms checked 2026-10-26: [Open-Meteo terms](https://open-meteo.com/en/terms), [pricing](https://open-meteo.com/en/pricing).
- **PlantVillage:** the Hugging Face dataset page labels the dataset CC BY-SA 3.0. The local model's exact immutable dataset snapshot is not documented, and no legal determination has been made for model weights/derivatives or commercial redistribution. See [dataset card](https://huggingface.co/datasets/mohanty/PlantVillage) and [original project](https://github.com/spMohanty/PlantVillage-Dataset).
- **METEO RWANDA and NISR:** source provenance exists, but institution-specific permission to redistribute source PDFs, transcriptions, and statistics in the intended service has not been confirmed. Public availability and attribution do not alone establish reuse rights.
- **Agricultural decisions:** RAB/NISR approval, reviewer account roles, and passing software tests do not establish specialist qualifications. Source-backed rules need current local review by qualified specialists, clear crop/variety/geography/season/context scopes, expiry, and independent evaluation. The classifier is experimental maize screening, not a diagnosis or treatment recommendation.
- **Privacy and organization:** lawful basis, user access/export/deletion process, retention periods, data residency, breach response, operator access policy, and farmer support remain decisions for the responsible organization and legal advisers.
- **Operations:** hosted configuration, general traffic controls, TLS/proxy trust, monitoring, incident response, scheduled protected backups, off-site restore, SMTP delivery, accessibility, low-bandwidth use, and mobile-device behavior have not been independently verified.

## 9. Prioritized next-phase roadmap

1. **Run authenticated browser workflows:** use the isolated database and checklist above with a real browser, disposable farmer/reviewer/admin accounts, and verified denial tests. Record browser/version, service configuration (without secrets), steps, results, and screenshots without personal data.
2. **Resolve source and model rights:** obtain written terms for NISR/METEO RWANDA reuse and determine Open-Meteo commercial status/plan and PlantVillage/model obligations before public or commercial distribution.
3. **Establish responsible agricultural evidence:** collect authentic source material, confirm permission, review it with qualified Rwandan specialists, apply narrow scope and expiry, and independently validate the farmer-facing wording. Keep the approved registry empty until this is complete.
4. **Prepare a controlled staging environment:** identify the actual runtime DB, use managed secrets, TLS, a trusted proxy configuration, gateway rate/concurrency controls, monitoring, redacted logs, and configured mail delivery.
5. **Set recovery objectives and prove them operationally:** define RPO/RTO with the data owner, schedule access-controlled encrypted backups, keep off-site copies, and restore a protected staging copy to an isolated destination on a recurring schedule.
6. **Approve privacy operations:** agree farmer notices, retention/deletion/export handling, access and support controls, data residency, and incident-response procedures before collecting real pilot data.
7. **Expand field validation:** evaluate crop-health screening on consented Rwanda field images with specialist labels and farm/time-separated test sets; calibrate/abstain and keep results non-diagnostic until evidence supports any stronger claim.
8. **Improve access and usability:** complete Kinyarwanda review, accessibility, mobile, low-bandwidth, and field-user testing; define any offline/SMS/USSD work as separate future scope.

## 10. Readiness verdict

**Development only.** Local Python/API/frontend automated checks pass with the documented Windows Vitest invocation, and the isolated synthetic recovery exercise passed integrity/schema/data checks. The lack of authenticated browser evidence, live service/database identification, production security and recovery proof, cleared provider/data rights, approved agricultural rules, and organizational privacy operations prevents a controlled farmer pilot or public production claim.
