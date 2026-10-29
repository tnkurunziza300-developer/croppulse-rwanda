# CropPulse Rwanda — Manual Browser Smoke Verification, Phase 16

**Date:** 2026-10-28  
**Verdict:** **DEVELOPMENT ONLY.** This phase does not authorize a pilot, staging deployment, or release.

## Summary

Frontend source checks and an isolated production build completed successfully. A fresh synthetic SQLite database was migrated and checked, and the API and Vite server were briefly started on verified, unused loopback ports. The installed browsers could not provide a usable page: Chrome failed to create its isolated profile/Crashpad files with access-denied errors, and the Edge fallback did not produce a usable capture or DOM. Consequently, none of the requested visual or interactive React and Streamlit checks is claimed as passed. Automated browser E2E remains unverified.

The normal application databases were not selected. The build output went to a separate temporary directory; `frontend/dist` was not the build target. No application source, agronomic rule, review decision, NISR source, or dependency manifest was changed. No package was installed and npm policy was not changed.

## Environment and isolation

- Windows PowerShell, repository `C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda`.
- Installed Google Chrome 156.0.8078.48 and Microsoft Edge 156.0.4314.42. No Playwright or computer-control/browser automation tool was available.
- Frontend: React/Vite, existing installed dependencies. API: FastAPI with Alembic.
- API database selection was confirmed to read `CROP_PULSE_DATABASE_URL`; the API and Alembic were both explicitly given `sqlite:///C:/Users/Student/AppData/Local/Temp/croppulse-phase16-synthetic.sqlite3`. The file did not exist before setup. Migrations reached `0015_weather_alert_foundation`; read-only SQLite checks returned `integrity_check=ok` and no foreign-key issues. No synthetic account or record was created.
- Test API and Vite ports were `49182` and `49183`, after checking that neither had a listener. Both listeners were confirmed to belong to the processes launched for this phase. API and Vite used loopback URLs; no external provider was contacted.
- Existing listeners on ports 8001 and 5173 belonged to processes whose identities could not be inspected. They were not stopped or used to run the app. Before their ownership was discovered, one unauthenticated `GET /health` request reached port 8001 and one unauthenticated `GET /` reached port 5173. No credentials or writes were sent. Those responses are excluded as verification evidence.

## Commands and automated checks

Commands ran from `frontend/` unless noted:

| Command | Result |
|---|---|
| `npm run typecheck` | **PASS** |
| `npm run lint` | **PASS** |
| `npm test -- --configLoader native --pool=threads --maxWorkers=1` | **PASS** — 48 tests across 6 files. Vitest printed a known jsdom navigation-not-implemented diagnostic; the command exited successfully. |
| `npm run build -- --outDir "C:/Users/Student/AppData/Local/Temp/croppulse-phase16-isolated-build" --emptyOutDir` | **BLOCKED** — Windows `spawn EPERM` loading the Vite config, before output. |
| `npm run build -- --configLoader native --outDir "C:/Users/Student/AppData/Local/Temp/croppulse-phase16-isolated-build" --emptyOutDir` | **PASS** — 2,517 modules transformed; output went only to the isolated temporary directory. |

No dependency install or package/lockfile/policy edit was performed. `frontend/dist` remained outside the build target.

## Manual smoke-check results

Since neither installed browser yielded a usable rendered page, blocked checks are not inferred from source tests or successful HTTP responses.

| Surface/check | Result | Observation |
|---|---|---|
| React: primary screen renders without fatal error | **BLOCKED** | Chrome exited before producing a usable page capture. Its fresh profile attempt logged access denied while creating the profile singleton/Crashpad files and a fatal platform-channel error. The HTML capture was empty. |
| React: provisional crop fit distinguished from validated advice | **NOT TESTED** | Requires rendered recommendation screen; no authenticated browser interaction was available. |
| React: historical NISR yield context not a suitability guarantee/forecast | **NOT TESTED** | Requires rendered recommendation context. |
| React: unknown conditions not presented as verified facts | **NOT TESTED** | Requires rendered recommendation details. |
| React: clipping, labels, status readability | **NOT TESTED** | No usable viewport screenshot. |
| Streamlit: Crop Guide provisional/unverified wording | **NOT TESTED** | Streamlit was not launched because there was no usable browser for visual inspection. |
| Streamlit: Season Calendar status wording | **NOT TESTED** | Same browser blocker. |
| Streamlit: Farm Planner estimates and wording | **NOT TESTED** | Same browser blocker. |
| Streamlit: District Map categories and status | **NOT TESTED** | Same browser blocker. |
| Streamlit: embedded Crop Guide caption and layout | **NOT TESTED** | Same browser blocker. |
| Synthetic UI operation failure/error messaging | **NOT TESTED** | No UI operation was exercised; no unavailable scenario was invented. |
| Authenticated farmer/reviewer/admin workflows, ownership, persistence, or lifecycle transitions | **NOT TESTED** | No synthetic users were created and no authentication/browser interaction was completed. |

An Edge fallback was attempted with a separate temporary profile but did not produce usable DOM or screenshot evidence. Therefore no visual PASS or FAIL is reported for either browser.

## Preservation and cleanup

SHA-256 values checked after the run:

| File | SHA-256 |
|---|---|
| `data/agronomy/rules.json` | `619F664181AF91448A0070C2DC4FEBE6E5C497183BBAB82FB09DA003B5116B1D` |
| `data/agronomy/review_decisions.json` | `5BC0F737622F40AC572FEC99EC54829AC0747FA444DC764A9DD490F120DA5FF4` |
| `data/verified/nisr_sas_2023_2026.csv` | `98DE5073D00F60231DF496DA3C19912834A3156A7F2F044BD6EAA5108F313927` |
| `data/verified/MANIFEST.json` | `400712C83177950EA9E86016CC41EF2EE8F428D6BBD15E7526CF62B082CAF562` |
| `data/agronomy/MANIFEST.json` | `CA73CB3F7A8E03373C1B5B453090421791FA5BF349EBACFD7BE6ACD5BB154F37` |
| `data/agronomy/validation_report.json` | `F0C025486D067EC8C7DC5289971B8B6A35DA020F8F001807D7B1A630DAA0941C` |
| `frontend/package.json` | `15EA2F8FD6AAD40FDBCB3AA64F621BCD7771CDB5AC2A86078A43E48F779F0545` |
| `frontend/package-lock.json` | `29CB252BD28AB66259AE5843DB83B4CD70E8995B234A5E9F555015D55F7BFB8F` |

The NISR CSV hash matches the existing verified-data manifest. The synthetic database still passes read-only integrity/FK/revision checks. The normal app databases were not opened by the test services. The pre-existing `frontend/dist` directory remained present; the build output was isolated elsewhere. No before-run content hash for `frontend/dist` was captured, so this report makes no byte-for-byte unchanged claim for that directory; it was not a build destination.

The phase-started API and Vite processes were stopped by their recorded process IDs after confirming they owned ports 49182/49183. Those ports were free afterward. Unknown processes on ports 8001/5173 were left untouched. The synthetic database and temporary isolated build were retained under `%TEMP%` for reproducibility; they contain no farmer data. No production service, external provider, SMTP, migration target, or live application configuration was used.

## Remaining boundary

This was not automated browser E2E testing and does not verify authentication, authorization, cross-farmer isolation, persistent workflow transitions, production settings, agricultural correctness, or specialist approval. The Playwright package-source blocker remains open. Product readiness remains **DEVELOPMENT ONLY**. A later visual smoke pass requires an approved browser execution path/profile access; authenticated workflow checks additionally require isolated synthetic accounts.
