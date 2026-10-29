# CropPulse Rwanda — Phase 7: Runtime Identity, Environment Verification, and Safe Local Workflow Testing

**Verification date:** 2026-10-28  
**Repository:** `C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda`  
**Verdict:** **DEVELOPMENT ONLY**  
**Scope:** Read-only runtime/configuration inspection, documented read-only database diagnostics, safe automated checks, isolated frontend build, and agricultural evidence validation. No application service was started or contacted.

## 1. Executive summary

The current project virtual environment and source tree were exercised by the local automated suites. The Windows-safe Python suite passed 181 tests with one pytest warning. Frontend tests passed 48 tests, typecheck and lint passed, and a production Vite build completed in a fresh `.test-runtime` output directory.

No listener was found on the checked development ports (8000, 8001, 8501, 5173, 18001, 15173, or 5000). Therefore no live CropPulse process could be positively identified, no live OpenAPI document could be read, and no live process database can be claimed. The project's read-only diagnostic inspected the database selected by that command invocation: the project-root default SQLite file. That result does not establish a running API's database identity.

The agronomic pack validates as current, with zero rules, zero approved rules, zero review decisions, and six open quality issues. The NISR CSV checksum matches its manifest. Provisional and forecast limitation labels are present in the inspected source. No agricultural evidence was activated or changed.

The repository remains **DEVELOPMENT ONLY**. Automated tests do not substitute for authenticated browser workflows, runtime identity, external-service, operational recovery, or production evidence.

## 2. Repository baseline and configuration

- Working directory and project root were confirmed as `C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda`.
- `.git` was absent and Git was unavailable in this environment. A clean Git status or complete baseline diff could not be established; the report does not claim otherwise.
- The requested Phase 3, Phase 4, Phase 5, and Phase 6 reports and the README were read. Their results are historical evidence unless separately rerun below.
- The API database selector in `backend/db.py` reads `CROP_PULSE_DATABASE_URL`, defaulting to `sqlite:///./data/croppulse_phase1.sqlite3`. Relative SQLite paths resolve from the process working directory.
- The backend source does not load `.env` files. The project launcher supplies environment values to the process it starts. The current shell's `CROP_PULSE_DATABASE_URL`, `CROP_PULSE_ENVIRONMENT`, `CROP_PULSE_AUTO_CREATE_SCHEMA`, and `VITE_API_BASE_URL` were unset.
- The launcher uses the project `.venv` and configures the development API on `127.0.0.1:8001`, with automatic schema creation disabled. Its reuse checks do not identify an arbitrary listener's source tree or database.
- The API lifespan invokes `Base.metadata.create_all()` only when `CROP_PULSE_AUTO_CREATE_SCHEMA` equals `1`. Staging/production runtime validation rejects that setting. Alembic migrations are an explicit separate command; none were run.
- `frontend/src/api.ts` reads `VITE_API_BASE_URL` and includes credentials on browser requests. The frontend `.env`, `.env.local`, and `.env.example` each configure loopback host `127.0.0.1`, port `8001`. Their other contents were not printed. Vite uses these build-time environment files; no remote/production API address was assumed.
- The frontend tests use Vitest/jsdom and mocked API behavior. The Python API fixtures set a unique `.test-runtime/api-test-databases` SQLite URL before schema creation; migration tests use temporary paths. The safe pytest runner disables the cache provider and places `tmp_path` beneath `.test-runtime`.

## 3. Listener and process identity

The read-only PowerShell check queried TCP listeners on ports 8000, 8001, 8501, 5173, 18001, 15173, and 5000. It returned **NO_MATCHING_LISTENERS**.

| Service/port | Listener and PID | Executable, command line, working directory | Repository association |
|---|---|---|---|
| API 8000/8001 | None observed | Not applicable | No live API identity established |
| Streamlit 8501 | None observed | Not applicable | No live Streamlit identity established |
| Vite 5173 | None observed | Not applicable | No live frontend identity established |
| Prior isolated ports 18001/15173 | None observed | Not applicable | No isolated test service running |
| Other checked port 5000 | None observed | Not applicable | None |

Because no listeners were observed, no HTTP request was sent. Live health, OpenAPI route set, PID, executable, command line, parent process, working directory, loaded module path, runtime environment, and live database are **UNVERIFIED**. A candidate database's health or the source tree's route list cannot prove runtime identity.

## 4. Database identity and preservation

`CROP_PULSE_DATABASE_URL` was unset for the diagnostic command, whose working directory was the project root and whose executable was the project's `.venv` Python. The documented default therefore resolved for that command to:

`C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda\data\croppulse_phase1.sqlite3`

`backend.diagnostics` was inspected before execution. For SQLite it refuses a missing file, checks for WAL/SHM sidecars and declines to connect if they exist, opens an existing database using SQLite `mode=ro`, sets `query_only`, runs only read checks, and never imports the FastAPI application or applies migrations. Its result was:

| Diagnostic | Result |
|---|---|
| Backend/path | SQLite; project-root default path above |
| File exists / connection | Yes / `ok` |
| Alembic revision | `0015_weather_alert_foundation` |
| Source migration head match | Yes |
| SQLite integrity | `ok` |
| Foreign-key violations | 0 |

This confirms the local diagnostic target only. **The database used by a live API remains unverified** because no API listener existed and no process runtime was available to inspect.

No SQL writes, schema creation, migration, backup, restore, account operation, or private-record query was performed. API integration tests used generated synthetic database files beneath `.test-runtime`; their fixtures set the URL before creating tables and clean their uniquely named API test databases. Migration tests operate on test temporary paths. The tests did not target the designated development database.

## 5. Test and integrity results

Commands were run from the indicated project directories. Exit status is recorded where available.

| Command | Result |
|---|---|
| `\.venv\Scripts\python.exe tests\windows_safe_pytest.py` (repository root) | **181 passed, 1 warning, exit 0, 120.53s.** Warning: pytest `PytestAssertRewriteWarning` because AnyIO was already imported. |
| `npm.cmd test -- --configLoader native --pool=threads --maxWorkers=1` (`frontend`) | **48 passed across 6 files, exit 0.** Vitest printed a jsdom `Not implemented: navigation to another Document` notice; no test failed. |
| `npm.cmd run typecheck` (`frontend`) | Passed, exit 0. |
| `npm.cmd run lint` (`frontend`) | Passed, exit 0. |
| `\.\node_modules\.bin\vite.cmd build --configLoader native --outDir ..\.test-runtime\phase7-build-20261028 --emptyOutDir false` (`frontend`) | Passed, exit 0. Fresh isolated destination; `frontend/dist` was not the output target. |
| `\.venv\Scripts\python.exe -m backend.diagnostics` (repository root) | Passed read-only candidate check; exit 0. It reports the current command invocation, not a running API. |
| `\.venv\Scripts\python.exe -m utils.agronomy_knowledge` (repository root; no write flags) | Passed, `valid: true`, manifest current. 5 sources, 4 statements, 0 rules, 0 approved rules, 0 review decisions, 6 open quality issues, 12 legacy provisional guide entries. |

NISR verification:

- `data/verified/nisr_sas_2023_2026.csv`: 609,936 bytes; SHA-256 `98de5073d00f60231df496da3c19912834a3156a7f2f044bd6eaa5108f313927`.
- `data/verified/MANIFEST.json` declares the same filename and SHA-256.
- The NISR CSV and manifest were not modified. The validator was run without manifest/report write flags.
- Post-test hashes of the verified-data manifest, agronomy manifest, `rules.json`, and `review_decisions.json` were recorded. No code path in the test runner targets these registry files for writing; all test-created evidence records use temporary fixtures.

Test-created temporary files and isolated build output are confined to `.test-runtime`. The test runner uses a unique pytest run directory; its existing Streamlit scratch folder was not cleared. No existing frontend build output was cleaned or overwritten.

## 6. Browser workflow matrix

No browser workflow was executed. The required identity prerequisites were absent: there was no running frontend/API, no verified backend process/database pair, and no isolated browser-ready account service. No test account was registered. Prior reports' browser observations are historical and do not establish current end-to-end behavior.

| Workflow | Status | Reason |
|---|---|---|
| Registration, sign-in, sign-out, session expiry, settings | **BLOCKED** | No verified isolated API and test account environment |
| Farm/field list and ownership boundaries | **BLOCKED** | Would require a verified isolated authenticated backend |
| Crop plans and lifecycle transitions | **BLOCKED** | Would write persistent records; no isolated app runtime was established |
| Activity recording and persistence | **BLOCKED** | Would write persistent records |
| Weather page, forecast provider, alert settings/history | **NOT TESTED** | No frontend/API runtime contacted; unit tests cover source behavior only |
| Crop-health report/photo and reviewer updates | **BLOCKED** | Would create private application records/files and require isolated roles/accounts |
| Private messaging and authorization | **BLOCKED** | Would create messages; no isolated roles/accounts |
| Unauthorized/cross-farm access | **BLOCKED** | Requires dedicated isolated accounts and backend |
| Empty/loading/validation/error states | **NOT TESTED end-to-end** | Component tests are not a current browser journey |

The next safe browser stage requires an explicitly approved disposable runtime/database, isolated test accounts and roles, confirmed API/frontend identity, and review of every route to be exercised for external calls or persistent writes.

## 7. Agricultural safety labels and approval boundary

- The recommender source labels its broad categories as provisional, says local thresholds are unverified, and states that NISR statistics do not determine crop rank.
- React crop-plan/recommendation copy describes source status and limits; missing entries are not presented as proof of local unsuitability.
- The Weather page describes precipitation/temperature as model estimates, says they do not measure soil moisture or confirm plot rainfall, and states its prompts are not official warnings, diagnoses, or pesticide recommendations. Weather preference UI states that no alerts are currently generated.
- The Phase 5 evidence-governance report documents a fail-closed approval trust boundary: locally declared approvals do not serve as verified agricultural approval. The current validator confirms zero effective/declared approved rules and zero review decisions.
- Existing source/reports characterize image screening as experimental and non-diagnostic. Reviewer application roles do not establish professional qualifications.

No rule was activated and no agricultural content or evidence was changed.

## 8. Unresolved risks and prioritized next steps

1. **Runtime identity:** start only through an owner-approved controlled local procedure that proves executable, source module, working directory, effective configuration, and database before any writes. This phase observed no process and did not start one.
2. **Browser integration:** prepare a separately approved disposable database and test accounts, then verify API route behavior and role boundaries in a browser at desktop/mobile widths. No production or designated development data should be used.
3. **Database recovery:** identify the authoritative environment and establish protected backup access plus a successful isolated restore rehearsal before migration or maintenance.
4. **Agricultural evidence:** acquire traceable, reusable, current local evidence and qualified review for scoped rules. Do not infer RAB/NISR endorsement; keep approved-rule coverage at zero until the trust boundary and review evidence are real.
5. **Deployment blockers:** resolve production API URL, TLS/CORS/cookie/secret configuration, rate/concurrency controls, monitoring, privacy/retention/legal basis, dataset/provider permissions, email delivery, and operational incident/rollback procedures.

## 9. Explicit gates before higher-risk activity

- **Browser integration testing:** verified disposable database and runtime, dedicated synthetic farmer/reviewer/admin accounts, route-level write/external-call review, and recorded cleanup plan.
- **Database migration:** identify and approve the target by its owner, verify a protected pre-migration backup, rehearse restore to an isolated destination, stop all writers in an approved window, and review migration compatibility/rollback limits. No migration is authorized by this report.
- **Farmer pilot:** resolve agronomic evidence and specialist governance, data rights, privacy/retention, authenticated workflow testing, support/escalation, monitoring, backups/recovery, and operational ownership.
- **Public deployment:** additionally verify hosting/runtime identity, HTTPS, CORS/cookies, managed secrets, abuse controls, provider licenses, deployment rollback, and production-grade recovery. Passing local suites is insufficient.

## 10. Data and application changes

No application source, configuration, dependency, migration, protected database, NISR dataset/manifest, agronomic rule, or approval decision was changed. The only intended tracked changes for Phase 7 are this report and its README link. Automated checks created isolated temporary test artifacts and the isolated Vite build under `.test-runtime`; existing `frontend/dist` was not used as a build destination. No service was launched, stopped, restarted, or contacted.
