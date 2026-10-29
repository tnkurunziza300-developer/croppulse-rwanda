# CropPulse Rwanda — Final Development Day Release Report

**Review date:** 2026-10-26 (Africa/Johannesburg)  
**Target deployment date:** 2026-10-27  
**Project:** `C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda`  
**Verdict:** **BLOCKED** for the planned deployment. The repository remains suitable for development and isolated local verification only; the evidence does not support a farmer pilot or public production release.

## Executive summary

The current local source passed the full Windows-safe Python suite, the frontend suite, typechecking, lint, production build, agronomic-pack validation, NISR file checksum comparison, and read-only integrity checks of the local candidate SQLite database. No confirmed application defect requiring a code change was found in this release review. No application code, database schema, NISR source file or manifest, or active agronomic rule was changed.

The release gate is blocked by unresolved operational facts: the running API's source directory, working directory, process environment, and effective database target cannot be established; no production host or database target was supplied; the available backup evidence is synthetic and does not prove protected access or production recovery; the local Streamlit listener is bound to all IPv4 interfaces; and production security, privacy, provider permissions, and authenticated browser workflows have not been verified.

The 2026-10-26 live API check differs from the earlier Phase 6 observation: the current API responds successfully and its OpenAPI document includes the weather alert routes that Phase 6 previously found absent. That observation does not establish the API's code copy or database. The reason for the discrepancy remains unknown.

## 1. Baseline and repository state

Reviewed the Phase 3 full-system audit, Phase 4 readiness verification, Phase 5 browser QA and operational readiness report, Phase 6 live database report, README, deployment checklist, React setup guide, weather documentation, and relevant source configuration.

- Git status is unavailable: Git is not available on `PATH` and this project copy has no `.git` directory. Existing source changes therefore cannot be classified as committed, modified, or untracked.
- Root `.env` is absent; `.env.example` is present. Frontend `.env`, `.env.local`, and `.env.example` exist. Their contents were not read or recorded. No secrets or tokens were inspected.
- Current source selects `CROP_PULSE_DATABASE_URL` from the API process environment, otherwise defaults to the relative SQLite URL `sqlite:///./data/croppulse_phase1.sqlite3`. A relative path depends on the process working directory. The API calls `Base.metadata.create_all()` only when `CROP_PULSE_AUTO_CREATE_SCHEMA=1`; production/staging configuration rejects auto-creation and uses Alembic migrations.
- No production host, production environment, intended production database, or migration target was identified in the repository or supplied with this request.

## 2. Runtime and database findings

Read-only listener and process checks were performed at approximately 11:30 local time on 2026-10-26. No service was started, stopped, or restarted.

| Service | Observed listener | Process evidence | Limit |
|---|---|---|---|
| FastAPI API | `127.0.0.1:8001`, PID 21152 | Global Python executable `C:\Users\Student\AppData\Local\Programs\Python\Python312\python.exe` | Parent process, command line, entry point, working directory, and process environment were unavailable through the supported process query. Effective database URL is unknown. |
| Streamlit | `0.0.0.0:8501`, PID 24140 | Global Python executable at the same path | Listener is bound to all IPv4 interfaces. Whether another device can reach it depends on firewall and network controls, which were not verified. No process restart or rebind was attempted. |
| Vite development server | `127.0.0.1:5173`, PID 11512 | Node executable under the user's local Node installation | This is a development listener, not a production deployment. |

The supported `Get-CimInstance Win32_Process` query returned no process metadata for these PIDs. Raw command lines and process environment values were not requested or printed. The running API executable is outside this repository's `.venv`, but that alone does not identify which source copy it imported.

Current unauthenticated, read-only API checks:

- `GET http://127.0.0.1:8001/health`: HTTP 200.
- `GET http://127.0.0.1:8001/openapi.json`: HTTP 200; title `CropPulse Rwanda Farmer Records API`, version `1.0.0`, 62 paths.
- The live OpenAPI document currently includes `GET /v1/weather/alert-preferences`, `PUT /v1/weather/alert-preferences/{field_id}`, `GET /v1/weather/alerts`, and `PATCH /v1/weather/alerts/{alert_id}/status`.
- Phase 6 recorded those routes absent from the OpenAPI document. The current observation is different; the process metadata available here does not explain why. No cause is asserted.

The candidate file `data/croppulse_phase1.sqlite3` was opened read-only. It reports `PRAGMA integrity_check=ok`, zero foreign-key violations, Alembic revision `0015_weather_alert_foundation`, and 24 application tables. `alembic heads` reports `0015_weather_alert_foundation` as the source head. These checks establish the state of this candidate file only; they do **not** prove the running API uses it or establish production migration compatibility. No production backup, migration, or database write was performed.

## 3. Release findings

Severity describes the release impact, not a claim that an exploit or data loss occurred.

| Severity / status | Finding | Evidence and required action |
|---|---|---|
| **High — Blocked** | Live API source and database identity are unconfirmed. | Port 8001 responds, but its working directory, source entry point, process environment, and effective database URL are unavailable. Deployment owner must confirm a sanitized target and verify the exact database before migration or release. |
| **High — Blocked** | No production database, migration target, or target-specific rollback plan is identified. | Local SQLite at revision 0015 is healthy; it is not evidence about production. Identify the deployment host/database and migration path. Review each pending migration against an isolated copy before any production change. |
| **High — Blocked** | Production backup protection and recovery are not proven. | Phase 4/5 restore artifacts contain synthetic data and pass integrity checks, but inherited ACLs were broad; Windows denied hardening an isolated directory. There is no verified encrypted/off-site production backup, schedule, retention, RPO/RTO, or authorized second-identity access test. Machine/data owner must provide a restricted backup destination and complete a restore rehearsal before handling live data. |
| **High — Current local exposure unknown** | Streamlit is listening on `0.0.0.0:8501`. | Confirmed by `netstat`; this binds all IPv4 interfaces. Firewall reachability was not checked. Keep this local service on a trusted network or have the authorized operator verify firewall/network isolation. Do not expose it publicly as a development server. No service setting was changed. |
| **High — Blocked** | Hosted security and operations are unverified. | Actual HTTPS/TLS termination, reverse-proxy trust, secure cookies, exact CORS origins, secret storage, host restrictions, edge rate/concurrency controls, monitoring, incident response, and safe logging have not been verified in a staging/production environment. Deployment owner must configure and test them at the real gateway. |
| **High — Blocked** | Authenticated browser workflows have not been exercised. | API and component tests cover meaningful authorization paths, but there is no supported browser automation setup or isolated browser test environment. Registration, login/logout, refresh/handoff, CSRF, farm ownership, crop-plan lifecycle, weather, messaging, reviewer, and administrator journeys remain unverified in a real browser. |
| **High — Blocked** | Privacy and retention operations are incomplete. | Identity/contact details, farm and field coordinates, messages, crop-health photos, and account records can persist. Approved retention, export/deletion operations, data residency, support, incident communication, and legal review are not established. Data controller/privacy owner must approve these before collecting pilot data. |
| **High — Blocked for advice/diagnosis claims** | No active agronomic rules are approved. | Registry validates and remains empty: zero rules and zero review decisions. Crop ranking/calendar content remains provisional; the maize image model is experimental screening, not diagnosis. Do not present treatment, medicine, dose, or disease-cause advice. Keep alert generation inactive until scoped rules are evidence-backed and formally reviewed. |
| **High if commercial or promotional use is planned** | Provider and model reuse rights need deployment-specific approval. | The documented Open-Meteo free endpoint is non-commercial, rate-limited, requires attribution, and disclaims accuracy/availability guarantees. NISR general terms describe CC BY 4.0 reuse but do not establish every embedded item's provenance or conditions. Permission for METEO RWANDA bulletins/transcriptions is undocumented. The PlantVillage mirror declares CC BY-SA 3.0; exact model/data revision and derivative obligations remain unresolved. Obtain source-specific legal/data-owner review before distribution or commercial use. |
| **Medium — Unverified** | Email delivery and user recovery flows are not externally tested. | SMTP is operator-configured; no real provider or mail sink was used. Test with a non-production mail sink before enabling real email workflows. |
| **Medium — Unverified** | Low-bandwidth, mobile, accessibility, and Kinyarwanda quality are not verified. | No field-user, screen-reader, mobile, or fluent local terminology review was performed. |

## 4. Agricultural and dataset safety

- The current read-only registry validation returned `valid=true`, current manifest, and zero findings. `rules.json` and `review_decisions.json` each contain zero records; there are no active or approved rules.
- The NISR SAS CSV has 2,020 records in the current loader and is structurally validated against its manifest. Its SHA-256 matches the existing manifest. This verifies file integrity and structure, not NISR authenticity, publication rights, or the correctness of estimates.
- Historical NISR observations remain descriptive context; they do not validate CropPulse planting recommendations or disease advice.
- Weather alert preference/history routes are present, but the documented rule registry has no approved rules or active alert-generation workflow. Preferences must not be presented as active warnings.
- Keep provisional guidance, the experimental maize-only image screening, and forecast uncertainty clearly labelled. No diagnosis/treatment claim or unsupported alert should be enabled for the release.

## 5. Confirmed defects fixed and files changed

No confirmed application-code defect that blocks release was found and fixed in this phase. The current route discrepancy was documented as unresolved rather than “fixed”; no service was restarted. No application source, configuration, migration, permissions, or database was changed.

Files changed for this report:

- `docs/final-development-day-release-report.md` — this release-gate evidence and go/no-go record.
- `README.md` — link to this report.

The requested test/build commands produced ignored disposable outputs under `.test-runtime/` and `frontend/dist/`. No existing NISR file, NISR manifest, agronomic registry, application database, or source file was intentionally modified.

## 6. Verification performed

Commands below ran from the project root unless the working directory is shown. Exit codes are included. A passing test suite is automated evidence only.

| Command/check | Result |
|---|---|
| `Get-Process -Id 21152,24140,11512` and filtered `netstat -ano -p tcp` | Exit 0. Confirmed listener PIDs, executable paths, and binds shown above. |
| `Get-CimInstance Win32_Process -Filter 'ProcessId = 21152 OR ProcessId = 24140 OR ProcessId = 11512'` | Exit 0, no process metadata returned; parent, command line, CWD, and process environment remain unknown. |
| `Invoke-WebRequest http://127.0.0.1:8001/health` | HTTP 200; read-only request. |
| `Invoke-RestMethod http://127.0.0.1:8001/openapi.json` | HTTP 200; read-only request; current routes listed above. |
| `\.venv\Scripts\python.exe tests\windows_safe_pytest.py` | Exit 0; **169 passed**, one `PytestAssertRewriteWarning` because AnyIO was already imported; 186.40 seconds. |
| From `frontend`: `npm.cmd test -- --configLoader native --pool=threads --maxWorkers=1` | Exit 1; **35 passed, 2 failed**. A device-location test hit Vitest's default 5-second timeout; the following saved-field test then failed because no forecast request had been captured. |
| From `frontend`: `npm.cmd test -- --configLoader native --pool=threads --maxWorkers=1 --testTimeout=30000 src/WeatherPage.test.tsx` | Exit 0; **5 passed**. No assertions were removed or changed. |
| From `frontend`: `npm.cmd test -- --configLoader native --pool=threads --maxWorkers=1 --testTimeout=30000` | Exit 0; **37 passed across 4 files**. Vitest logged `Not implemented: navigation to another Document`; the suite passed. The timeout was raised only for this invocation because the default run timed out; project configuration was not changed. |
| From `frontend`: `npm.cmd run typecheck` | Exit 0; passed. |
| From `frontend`: `npm.cmd run lint` | Exit 0; passed. |
| From `frontend`: `npm.cmd run build -- --configLoader native` | Exit 0; passed; Vite produced a local production bundle in ignored `frontend/dist/`. |
| `\.venv\Scripts\python.exe -m utils.agronomy_knowledge` | Exit 0; pack valid/current, zero findings, 5 sources, 4 source statements, zero rules/approvals/review decisions, 6 open quality issues, 2,020 NISR rows. This command validates only; no write flags were used. |
| Read-only inline Python check using `validate_pack()`, `load_data()`, SHA-256 comparison, and SQLite `mode=ro` PRAGMAs | Exit 0; NISR loader state `validated`, 2,020 rows, checksum match; candidate SQLite integrity and revision shown above. |
| SHA-256 comparison of `data/verified/nisr_sas_2023_2026.csv` to `data/verified/MANIFEST.json` | Match; no dataset or manifest write. |
| `\.venv\Scripts\python.exe -m alembic heads` | Exit 0; `0015_weather_alert_foundation` is source head. |
| Read-only SQLite connection to `data/croppulse_phase1.sqlite3`; `PRAGMA integrity_check`, `PRAGMA foreign_key_check`, revision/table count | Exit 0; `ok`, zero FK violations, revision `0015_weather_alert_foundation`, 24 application tables. No farmer rows were queried or printed. |
| Browser E2E workflows | **Not performed.** No isolated test deployment/browser-control tooling or synthetic role accounts were available. Current active local services were not used for state-changing browser tests. |
| Production backup/restore | **Not performed.** Only previous synthetic recovery evidence was reviewed; no backup copy, migration, restore, or ACL change was attempted in this phase. |

The first frontend test run failure is retained in this record even though the targeted and full suites passed with a longer per-test timeout. The default timeout sensitivity remains a test-environment limitation; no project test settings or assertions were weakened.

## 7. Deployment prerequisites for 2026-10-27

These are release gates, not actions performed in this review:

1. **Identify the target:** name the hosting owner, exact source artifact/commit, domain, proxy topology, API and Streamlit deployment model, database engine, sanitized database target, and operations contact. Do not infer these from the local process or default SQLite path.
2. **Prove database identity and migration plan:** from the authorized service configuration, establish the effective runtime DB target without disclosing credentials. Verify the intended schema revision and pending migration path on an isolated production-like copy. Do not migrate until a verified backup and change approval exist.
3. **Prove backup recovery:** provision encrypted backup storage with restrictive ACLs and off-site retention; verify access with an authorized and unauthorized identity; restore a copy into an isolated target; check integrity, schema, and required counts; set owners, retention, RPO/RTO, and alerting. Do not use a local broadly accessible directory for real farmer data.
4. **Harden the hosted boundary:** HTTPS-only public access, trusted proxy configuration, secure cookies, exact CORS allowlist, managed secrets, production environment mode, no auto-schema creation, request size controls, edge rate/concurrency limits, non-sensitive logs, monitoring, incident response, and firewall rules. Ensure the local Streamlit development listener is not exposed to public networks.
5. **Complete isolated browser journeys:** with synthetic farmer, reviewer, and administrator accounts on a disposable database, test registration/login/logout, CSRF, refresh and React/Streamlit handoff, cross-user denial, farm/activity and crop-plan lifecycle, weather retrieval/staleness, alert preferences/history, reviewer cases and messaging, and admin-only actions. Record browser/version and exact results.
6. **Close evidence and rights decisions:** obtain privacy/retention approval, local-language/accessibility review, and source-specific NISR/METEO RWANDA/Open-Meteo/model terms review for the intended non-commercial or commercial deployment. Keep unsupported agronomic advice and alert generation inactive.
7. **Stage then decide:** deploy only to a protected staging target after gates 1–6. Run non-destructive smoke tests, monitor, and document approval from the responsible deployment/data owners before any public or farmer-facing release.

### Rollback plan

The target host and database are unknown, so executable deployment/rollback commands cannot be specified safely. Before staging or production, retain the last known-good application artifact and sanitized configuration, and create a verified database backup in the protected destination. Prefer a compatible application rollback while retaining an additive schema. Do not downgrade migrations or overwrite the live database as a routine rollback. If data restoration is necessary, stop writes only under an approved incident/change plan, restore to a separate target first, verify integrity and ownership boundaries, then have the database owner approve any traffic switch. Define data-loss window and communications before release.

## 8. Final go/no-go checklist

| Gate | Status for 2026-10-27 |
|---|---|
| Exact production host, source artifact, and runtime identity known | **NO — not supplied/verified** |
| Effective production database identity confirmed | **NO — unknown** |
| Migration compatibility reviewed against intended database | **NO — intended database unknown** |
| Protected production backup and isolated restore proven | **NO — only synthetic local artifacts; ACL blocker remains** |
| HTTPS/proxy/CORS/secrets/rate limits/monitoring verified on target | **NO — no target environment** |
| Authenticated farmer/reviewer/admin browser workflows passed | **NO — unverified** |
| Privacy, retention, data residency, and support process approved | **NO — open** |
| Provider and model/data reuse permissions resolved for deployment purpose | **NO — open** |
| Unsupported treatment advice and unapproved alert generation kept inactive | **YES — source/report evidence; no deployment validation** |
| Local automated regression suite and production build passed | **YES — with the initial default-timeout test failure disclosed above** |

**Decision:** **NO-GO for the planned 2026-10-27 farmer-facing/public deployment.** Reassess only after the blocked gates are closed with evidence. Until then, limit use to development or a protected synthetic-data staging environment; do not treat passing local tests as production readiness.

## 9. Evidence boundary

This report records local repository, local runtime, automated-test, source, and read-only database evidence collected on 2026-10-26. It is not evidence of deployment, live production database identity, legal compliance, institutional endorsement, agricultural efficacy, provider availability, browser usability, or restoration of real farmer data. No external service, production account, real email, production database, migration, or deployment was accessed or changed.
