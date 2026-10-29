# CropPulse Rwanda — Phase 5: Controlled Browser QA and Operational Readiness

**Verification date:** 2026-10-26  
**Repository:** `C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda`  
**Readiness verdict:** **Development Only.**

## 1. Executive summary

The current source and automated checks were reviewed against the Phase 2, Phase 3A, Phase 3, and Phase 4 records. The full Windows-safe Python suite now passes with **169 tests** (the Phase 4 run had 159); the focused API/security/workflow set passes with 61 tests; and the frontend suite, typecheck, lint, and production build pass. These are local automated results, not browser or hosted-service evidence.

No API, Streamlit, or Vite listener was found on ports 8001, 8501, 5173, 18001, or 15173 when checked. No server was started and no credentials or persistent accounts were used. Existing API tests create synthetic accounts against per-test SQLite databases under `.test-runtime`; React tests run in Vitest/jsdom. That provides no cross-browser or end-to-end evidence.

Edge and Chrome are installed, but Playwright, Selenium, and browser-control tools are not available. Installing an automation stack would add dependencies and potentially alter lockfiles or fetch binaries; it was not needed to complete the safe local checks, so no packages were installed. A manual browser checklist is provided below.

The current Streamlit source does not render a password sign-in form: without a valid API session it offers a **Sign in to CropPulse** link to React. Existing Streamlit tests verify that flow and verify that an admin session remains an admin session. If a user still sees a Streamlit password form, this source audit cannot identify the running process because no app listener was present; an older process or another project copy remains possible.

The most important newly confirmed operational gap is backup-file access. The project is on NTFS, and the existing synthetic backup inherits `NT AUTHORITY\Authenticated Users: Modify`, `BUILTIN\Users: ReadAndExecute`, plus two unidentified local SIDs with Modify rights. `Modify` includes changing and deleting files. Restricting a newly created empty test directory was denied by Windows. No existing directory or database ACL was changed. The prior Phase 4 synthetic recovery artifacts still pass integrity, schema, foreign-key, and synthetic-row checks, but they are not access-restricted backups.

No reproducible application defect was established in the work that could safely be verified here. No application code or database schema was changed. The verdict remains Development Only because browser workflows, protected backup permissions, hosted controls, privacy operations, external terms, and approved agricultural evidence remain incomplete.

## 2. Repository state and baseline

### Repository and source comparison

- The requested project copy exists and contains React/Vite under `frontend/`, FastAPI under `backend/`, Streamlit at `app.py`, Alembic migrations, Python tests, and prior audit documentation.
- There is no `.git` directory and `git` is unavailable on `PATH`; a Git diff/status baseline could not be obtained. Pre-existing source and untracked files were left intact.
- Source still uses `CROP_PULSE_DATABASE_URL`, falling back to `sqlite:///./data/croppulse_phase1.sqlite3` relative to the process working directory. Alembic uses the same environment variable. Python source does not load the root `.env` file automatically. The Windows launcher sets a default local database only in the process it starts when no URL is present.
- The root has `.env.example` but no `.env` file, matching the Phase 4 inventory. `frontend/.env` and `.env.local` each define `VITE_API_BASE_URL`; their endpoint target is localhost port 8001. Values were not recorded in this report. The verification shell had no `CROP_PULSE_DATABASE_URL` or `CROP_PULSE_API_URL` set.
- The API test fixture sets a unique database URL for each test and uses FastAPI `TestClient`; it does not need to connect to the local working database. No listening process was returned for API, Streamlit, React, or the documented isolated test ports.
- The installed React/Streamlit handoff code and current tests match the documented intended design: React is the password sign-in/registration interface; Streamlit redirects unauthenticated users to React and can restore the same cookie session and role. This confirms source behavior only.

### Existing database and evidence checks

Read-only checks of the local candidate databases:

| File | Integrity | Foreign-key violations | Revision / tables |
|---|---:|---:|---|
| `data/croppulse_phase1.sqlite3` | `ok` | 0 | `0015_weather_alert_foundation`, 24 tables |
| `data/croppulse_local.sqlite3` | `ok` | 0 | no Alembic revision, 0 application tables |

The local application database was opened read-only for these checks. No records were displayed or changed. This does not identify the database used by any other process or deployment.

The agronomic registry validator reported `valid=true`, current manifest, 5 source records, 4 source statements, **0 rules and 0 approved rules**, 6 open quality issues, and 2,020 NISR rows. The NISR CSV hash remains `98de5073d00f60231df496da3c19912834a3156a7f2f044bd6eaa5108f313927`, matching its manifest. Statistics remain historical context; no recommendation was activated.

## 3. Environment, ports, accounts, and database isolation

- **Ports checked:** 8001, 8501, 5173, 18001, and 15173. No listener was returned at the time of inspection. No server was launched or contacted.
- **Test-account strategy:** the API test suite uses throwaway synthetic accounts and records in unique test SQLite databases under `.test-runtime/api-test-databases`. Streamlit `AppTest` checks are synthetic and in-process. Frontend tests use Vitest/jsdom. No dedicated farmer, reviewer, or administrator account was created for this report.
- **Database isolation:** full Python API tests were run through `tests/windows_safe_pytest.py`, which provides a project-local temporary path. Existing local candidates were only read with SQLite read-only mode. No migration was applied to either existing database. Phase 4's already isolated synthetic database, backup, and restored copy were rechecked read-only.
- **Startup commands documented by the project:** API: `.\.venv\Scripts\python.exe -m uvicorn backend.api:app --host 127.0.0.1 --port 8001`; React: from `frontend`, `npm run dev -- --host 127.0.0.1`; Streamlit: from project root, `.\run_streamlit.ps1`. These commands were not run in Phase 5: the launcher defaults to the existing `data/croppulse_phase1.sqlite3` if no database URL is supplied, and no separate isolated runtime was configured.
- **Health checks:** none were sent to a running server. TestClient health/auth route assertions are in-process automated API tests, not live-service checks.

## 4. Browser automation and workflow evidence

| Capability | Result |
|---|---|
| Microsoft Edge | Installed at `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe` |
| Google Chrome | Installed at `C:\Program Files\Google\Chrome\Application\chrome.exe` |
| Python Playwright / Selenium | Not installed in `.venv` |
| Frontend Playwright / Puppeteer / Selenium packages | No direct project dependency found |
| Browser-control tool | Not available in this environment |

Browser automation was not installed. Doing so would require adding or downloading a new test dependency/browser binary and could alter the lockfile or environment; this was not necessary for the automated baseline and there was no configured isolated live-service runtime to test. No browser E2E scenario is claimed as passed.

### Automated workflow coverage (not browser evidence)

The focused API/security command passed 61 tests. The full suite passed 169 tests. Existing test coverage exercises registration/login/logout, cookie/CSRF/session behavior, role assignment restrictions, account-scoped farm and plan access, reviewer district scope, administrator-only actions, messaging participants/unread state, crop-health upload and reviewer flow, weather validation/staleness/provider failures, and the relevant audit and account actions.

The full suite also includes Streamlit `AppTest` checks that:

- unauthenticated Streamlit users see a React sign-in link and no password/registration form;
- a restored farmer browser session opens the signed-in workspace;
- an administrator retains the administrator role; and
- Streamlit reloads missing handoff helpers when a cached module is stale.

These are component/in-process tests; they do not prove cookie behavior across actual browser origins, proxy paths, or browsers. Since no authenticated browser workflows ran, farmer/reviewer/admin end-to-end results remain **unverified**.

### Responsive, accessibility, and localization

No browser viewport, keyboard-only, screen-reader, mobile-device, slow-network, or field-user check was performed. Vitest/jsdom checks are not a substitute for those checks. Kinyarwanda coverage and agricultural terminology remain unverified by fluent local reviewers.

### Manual browser checklist for a future isolated run

1. Provision a new disposable SQLite database under `.test-runtime`; explicitly set its URL and use the same value for Alembic and the API. Confirm the exact resolved path before starting any process. Do not use either `data/*.sqlite3` candidate.
2. Apply the current migration head only to that new database, then start API, React, and Streamlit on the documented isolated ports. Confirm `/health`, CORS/CSRF, and OpenAPI from the isolated API only.
3. Create synthetic farmer, reviewer, and administrator accounts; assign a test district only through the admin UI/API. Record browser and version without recording credentials.
4. Exercise registration validation, successful/failed sign-in, sign-out, refresh persistence, expiry, password recovery/email change with a local mail sink only, and protected-route behavior after sign-out.
5. As farmer A, create a farm, field, plan, activity, weather forecast, synthetic crop-health report, and authorized conversation; reload and confirm the expected persistence and empty/error/loading/stale states. Attempt farmer B's record IDs and expect denial.
6. As reviewer, view/update only a test case in an assigned district, then try unassigned/cross-district IDs and confirm server denial. Change reviewer status/assignment as admin and verify access is reevaluated.
7. As administrator, test role/status/assignment/messaging-setting boundaries and audit events; attempt those operations as farmer and reviewer and confirm denial.
8. At desktop and mobile widths, inspect overflow, forms, dialogs, menus, focus visibility, labels, error announcements, English/Kinyarwanda switching, and slow/offline behavior. Do not claim translation or accessibility certification based only on visual inspection.

This checklist is a next action, not evidence of completed browser tests.

## 5. Security and authorization review

The existing tests and source cover server-side role and owner checks, reviewer district scope, session invalidation, CSRF, request body limits, crop-health upload constraints, account-action throttles, safe errors, and messaging authorization. The focused suite passed. No destructive penetration testing or load testing was attempted.

The source and deployment docs still require production validation of proxy/TLS trust, secure cookie configuration, CORS, secret management, rate/concurrency limits at the edge, monitoring, incident handling, safe logs, and privacy controls. No hosted environment was available, so these are not confirmed by this local run.

## 6. Backup permissions and recovery

### Filesystem and effective ACL evidence

- The project is on the Windows **NTFS** `C:` volume.
- Read-only ACL inspection of `.backups`, `.test-runtime`, and the existing Phase 4 synthetic backup showed inherited grants for `NT AUTHORITY\Authenticated Users: Modify`, `BUILTIN\Users: ReadAndExecute`, `BUILTIN\Administrators: FullControl`, and `NT AUTHORITY\SYSTEM: FullControl`. Two additional local SID principals have inherited Modify access; their account names could not be resolved. The current interactive user also has inherited FullControl on the Phase 4 backup.
- The intended test-backup boundary is the current test operator, SYSTEM, and administrators only. Current inherited grants do not meet that boundary: any authenticated user can read, modify, or delete the synthetic backup; group membership provides additional access.
- A new empty directory was created under `.test-runtime` and an `icacls /inheritance:r` hardening attempt was made only on that directory. Windows returned **Access is denied**; ACL inheritance remained enabled. No existing backup, working database, project root, or unrelated directory permission was changed. No backup file was written into that directory.
- The current process could inspect ACL entries but could not verify an alternate identity by an actual access check. No second Windows identity was available. Therefore no test backup is claimed access-restricted.

### Isolated restore evidence

The three Phase 4 synthetic artifacts were rechecked in SQLite read-only mode:

| Artifact | Integrity | FK violations | Alembic revision | Tables | Synthetic farmer/farm rows |
|---|---:|---:|---|---:|---:|
| `isolated-test.sqlite3` | `ok` | 0 | `0015_weather_alert_foundation` | 24 | 1 / 1 |
| `isolated-test.backup.sqlite3` | `ok` | 0 | `0015_weather_alert_foundation` | 24 | 1 / 1 |
| `isolated-test.restored.sqlite3` | `ok` | 0 | `0015_weather_alert_foundation` | 24 | 1 / 1 |

These artifacts contain only synthetic Phase 4 records. The check confirms consistency of the retained local test artifacts; no fresh restore was made in Phase 5. It does not establish ACL protection, encryption, off-site retention, backup scheduling, real-data recovery, or production RPO/RTO.

**Safe next action:** a Windows administrator or authorized machine owner must create a dedicated backup destination with explicit restrictive ACLs and verify access as both an authorized and unauthorized test identity. Do this outside the user's working data directories; then repeat the isolated restore test there. Do not relax the ACL after verification or copy a real database before this control is proven.

## 7. Provider, deployment, privacy, and agricultural readiness

| Finding | Severity / status | Responsible party and next action |
|---|---|---|
| Backup destination is broadly accessible and cannot be hardened by this process | **High / confirmed** | Windows administrator/data owner: provision a restricted, encrypted backup destination; verify effective access with a second identity; define retention and test restore there. |
| Authenticated farmer/reviewer/admin browser flows and responsive/accessibility behavior have not been exercised | **High / blocked** | Project operator: provide an isolated test environment and browser automation or schedule the documented manual run; use only synthetic users. |
| Hosted proxy, HTTPS, cookies, CORS, rate/concurrency controls, secrets, monitoring, and incident response are unverified | **High / blocked** | Deployment owner: configure and test these at the actual staging gateway before public exposure. |
| No approved scoped agronomic rules exist | **High / confirmed** | Agricultural evidence owner: obtain traceable local sources and independent qualified review through the existing registry workflow. Keep the approved set empty until evidence and approval exist. |
| Open-Meteo free API is non-commercial and rate-limited; terms require CC BY 4.0 attribution. Its terms disclaim forecast accuracy/availability warranties. Current terms checked 2026-10-26: [Terms](https://open-meteo.com/en/terms), [Pricing](https://open-meteo.com/en/pricing). | **High if commercial/promotional deployment is intended** | Product/legal owner: classify intended use and obtain approval before any paid subscription. No paid service was introduced or purchased. |
| NISR's current terms page states its disseminated data/analysis are CC BY 4.0, with source attribution and integrity requirements; individual content can carry different terms: [NISR terms of use](https://statistics.gov.rw/terms-use). | **Partially resolved** | Data owner: retain attribution and verify the specific SAS publication/CSV provenance and any embedded conditions. The file checksum confirms integrity, not source authenticity or legal review. |
| No written METEO RWANDA permission for reuse of supplied bulletins/transcriptions was located in project documentation. | **Open** | Data owner: retain source-specific licence/permission before redistributing bulletins or derived content; public access alone is not treated as permission. |
| The PlantVillage mirror declares CC BY-SA 3.0: [dataset card](https://huggingface.co/datasets/mohanty/PlantVillage). The exact pinned dataset revision and model-weight/derivative obligations remain unresolved. | **High / open** | Model/data owner and legal reviewer: pin exact dataset/model provenance and assess obligations before distribution or commercial use. Experimental labels remain non-diagnostic. |
| Personal farmer identity/contact information, farm coordinates, messages, crop-health photos, and account records persist; a complete organization-approved retention/export/deletion, incident, support, and residency process is not established. | **High / open** | Data controller/privacy counsel: approve and implement the policy and operational workflow before a farmer pilot. |
| No live mail sink, provider, external weather request, or production service was used. | **Medium / unverified** | Operator: test delivery only with a non-production mail sink; review provider terms and failures separately. |

Open-Meteo and NISR terms are web-published, changeable terms, not a legal opinion. The NISR general reuse licence does not itself establish the provenance or licence of every embedded third-party item. No organization was contacted.

## 8. Findings, fixes, and files changed

### Confirmed findings

1. **High — test backup permissions are inadequate.** Existing Phase 4 backup artifacts inherit broad authenticated-user modification rights and cannot be made private by the current Windows process. Reproduction: `icacls`/`Get-Acl` on `.test-runtime` and the synthetic backup; the scoped hardening attempt on a newly created empty directory returned Access Denied. Impact: other authenticated local users may read, alter, or delete test artifacts. No real backup was exposed or changed by this phase.
2. **High — real-browser workflows remain unverified.** Browser automation packages/tools are absent and no isolated live services were started. Existing tests are API-level, component-level, or in-process.
3. **High — deployment/privacy/agronomic blockers persist.** No hosted controls or approved agronomic rules were verified; privacy operations and source/model/provider review remain incomplete as detailed above.
4. **No confirmed source defect fixed.** The reported possibility of a Streamlit login screen was checked against source and test coverage: current source uses React as the only password sign-in UI, and an AppTest asserts no Streamlit password form. Because no server was running, a stale process or different project copy cannot be ruled in or out.

### Fixes

No application or test code was changed. There was no reproducible defect within the available safe test scope that justified a code change. The ACL failure is an environment permission boundary, not safely repairable here; it remains explicitly open.

### Files changed

- `docs/phase-5-controlled-browser-qa-operational-readiness.md` — this evidence record, limitations, reproduction, and next steps.
- `README.md` — link to the Phase 5 report.

The frontend production build generated ignored files under `frontend/dist/`. Test execution wrote disposable artifacts under the existing ignored `.test-runtime/`. No existing user file was overwritten. A newly created empty ACL-test directory remains under `.test-runtime`; it contains no backup or database.

## 9. Exact verification commands and results

Commands ran from the project root unless noted:

| Command | Result |
|---|---|
| `.\.venv\Scripts\python.exe tests\windows_safe_pytest.py` (sequential rerun) | **169 passed, 1 warning** in 120.65 seconds. Existing `PytestAssertRewriteWarning`: AnyIO had already been imported. |
| `.\.venv\Scripts\python.exe tests\windows_safe_pytest.py tests\test_backend_api.py tests\test_react_security_api.py tests\test_crop_health_api.py tests\test_weather.py tests\test_weather_alert_rules.py tests\test_plan_lifecycle_migration.py` (sequential rerun) | **61 passed, 1 warning** in 76.76 seconds; same AnyIO warning. |
| From `frontend`: `npm test -- --configLoader native --pool=threads --maxWorkers=1` | **37 passed across 4 files.** Vitest logged `Not implemented: navigation to another Document`; suite still passed. |
| From `frontend`: plain `npm test` | Not rerun in Phase 5. Phase 4 recorded it failing before test collection with Windows `spawn EPERM`; the Windows-compatible native-config invocation above passed. |
| From `frontend`: `npm run typecheck` | **Passed.** |
| From `frontend`: `npm run lint` | **Passed.** |
| From `frontend`: `npm run build -- --configLoader native` | **Passed.** Vite built the production bundle. |
| `.\.venv\Scripts\python.exe -m utils.agronomy_knowledge` | **Passed validation**; manifest current, zero active/approved rules, 2,020 NISR rows; no validator findings. |
| Read-only SQLite checks on both local candidate databases | Both integrity checks `ok`, zero FK violations; Phase 1 database revision remains `0015_weather_alert_foundation`. |
| Read-only SQLite checks on the three retained Phase 4 synthetic recovery artifacts | All returned integrity `ok`, zero FK violations, revision `0015_weather_alert_foundation`, 24 tables, 1 synthetic farmer and 1 synthetic farm. |
| `git status --short --branch` | Not available: no `.git` directory and Git command unavailable. |
| Browser E2E | Not run: no Playwright/Selenium/browser-control tooling and no isolated live app services. |
| ACL hardening of newly created empty test directory | **Failed safely:** Windows returned `Access is denied`; inheritance remained enabled. Existing permissions were not changed. |

The first focused Python run overlapped the first full run; both passed. To remove that overlap as a source of uncertainty, both the complete Python suite and focused API/security group were rerun sequentially; both passed again.

## 10. Scope, limitations, and next phase

### Not performed

- No browser-based E2E or real visual/responsive/accessibility check.
- No live API health or OpenAPI request, no active service identification, and no Streamlit process diagnosis.
- No migration, server launch/restart, production deployment, real account, real email, or external provider request.
- No change to existing database contents, database ACLs, production secrets, NISR CSV/manifest, weather source files, or agronomic registry.
- No restore into an access-restricted directory; Windows denied ACL changes before any backup file was written.

### Prioritized next actions

1. Have the machine owner provision and verify a private NTFS backup destination; repeat the synthetic restore there with a second identity check.
2. Run authenticated desktop/mobile browser workflows against a fresh disposable database. First confirm the launched API process, working directory, and exact database path; never infer them from port or default filename.
3. If Streamlit still displays a password form, capture the URL and sanitized process identity (executable, working directory, project entry point) and compare its file path to this repository. Current source has no separate password form.
4. Run a staging deployment review for HTTPS/proxy trust, cookie and CSRF scope, CORS, secret storage, edge request limits/rate controls, logging, monitoring, backup schedule, recovery objectives, and incident response.
5. Finalize organization-approved privacy/retention/support operations and obtain source-specific METEO RWANDA, dataset/model, and other third-party reuse determinations.
6. Keep the approved agronomic registry empty until real traceable evidence is correctly scoped, independently reviewed, and formally activated. Validate Kinyarwanda, accessibility, low-bandwidth, and field usability with local users.

## 11. Evidence boundary and verdict

- **Automated evidence:** 169 Python tests, 61 focused API/security/workflow tests, 37 React tests, typecheck, lint, build, registry validation, and read-only integrity checks passed as recorded above.
- **Browser evidence:** none in Phase 5.
- **External validation:** current public Open-Meteo, NISR terms, and PlantVillage dataset-card information was reviewed; no provider was contacted and no hosted behavior was checked.
- **Production assumptions:** TLS/proxy, real secrets, hosted database, SMTP, rate limits, backup protection/scheduling, privacy operations, and monitoring remain unverified.

**Readiness verdict remains Development Only.** Passing automated tests does not qualify CropPulse for farmer pilot or public production.
