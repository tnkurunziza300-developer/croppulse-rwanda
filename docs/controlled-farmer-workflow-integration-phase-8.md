# CropPulse Rwanda — Controlled Farmer Workflow Integration, Phase 8

**Implementation date:** 2026-10-28  
**Repository:** `C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda`  
**Readiness:** **DEVELOPMENT ONLY**

## 1. Executive summary

Phase 8 selected the existing farm and crop-plan journey: a signed-in farmer selects an owned farm, reviews its saved plan and activity history, and records the actual planting date to move an eligible plan to `planted`.

The API already enforced ownership and lifecycle rules, persisted the transition, and created a farmer-reported `Planting` activity. The React page reloaded the plan after a successful transition but did not reload the separate activity-history panel. As a result, the plan showed as planted while the corresponding saved activity stayed invisible until a later navigation or page reload. The page now reloads that farm's activity history after the API confirms the planting transition. A frontend regression test verifies the activity appears; existing backend integration coverage verifies that the activity and plan persist and remain owner-scoped.

Automated Python and frontend suites, typecheck, lint, and an isolated Vite production build passed. No browser workflow was run because no verified local API or frontend listener was available. This is source and isolated-test evidence, not a live end-to-end or production verification.

## 2. Workflow selected and source paths

### Farmer journey

1. React authenticates the farmer through its existing browser session and API client.
2. The farm workspace loads the signed-in farmer's farms and selects one.
3. The page loads that farm's crop plans and activity history.
4. The farmer creates a plan or uses an existing editable `draft`/`planned` plan.
5. To record planting, the farmer enters the actual planting date and selects **Mark planted**.
6. FastAPI validates the transition and date, updates the plan, and inserts one farmer-reported `Planting` activity in the same transaction.
7. After the successful status response, React reloads both the activity history and crop plans for the still-selected farm. A read failure is shown in the relevant panel; it is not represented as a successfully refreshed activity list.
8. Revisiting the workspace loads the saved plan and activity from the API again.

### Existing routes and responsibilities

| Operation | Route | Enforcement/purpose |
|---|---|---|
| List farmer's farms | `GET /v1/farms` | Authenticated farmer; returns only farms owned by that account. |
| List a farm's plans | `GET /v1/farms/{farm_id}/plans` | Authenticated farmer; `_owned_farm` rejects access to another account's farm. |
| Create plan | `POST /v1/farms/{farm_id}/plans` | Validated request; owner-scoped; plan and initial farmer-reported “Seasonal plan” activity are committed together. |
| Transition plan | `PATCH /v1/farms/{farm_id}/plans/{plan_id}/status` | Owner-scoped; server checks allowed transition and future-date constraint. A planting event is added with an idempotency key in the same transaction. |
| Read activity history | `GET /v1/farms/{farm_id}/activities` | Authenticated and owner-scoped; returns saved activities. |

Relevant implementation is in `frontend/src/pages.tsx` (`FarmsPage`), `frontend/src/api.ts` (authenticated API client), and `backend/api.py` (farm, plan, activity routes and lifecycle rules). No API route, schema, model, migration, or response contract changed in this phase.

## 3. Current behavior and change

Before Phase 8, `changePlanStatus()` awaited the status PATCH response and reloaded plans, but left the separate `activities` state unchanged. The API's transaction already inserted the planting activity; only the activity-history refresh was missing.

After the change, a successful `planted` transition reloads the selected farm's activities, then reloads its plans. Other lifecycle transitions preserve their existing refresh behavior. The activity loader retains its request identity and selected-farm checks, so a delayed response cannot show a previous farm's history after the farmer switches farms.

The updated mocked-fetch test simulates the backend's planting record and confirms that its text and date appear in the history after the transition. It also checks the PATCH body and the existing plan/status rendering. The frontend test is a UI behavior test; it does not establish database persistence by itself.

## 4. Security, lifecycle, and persistence evidence

- FastAPI authenticates each endpoint and checks that the requested farm belongs to the current farmer. Existing `test_owner_scope_blocks_other_farmer_and_unauthorized_access` covers unauthenticated and cross-farmer read/write denial for farm, plan, and activity routes.
- `test_plan_lifecycle_transitions_record_actual_planting_once_and_persist` verifies that a missing actual date, a future date, and an invalid transition are rejected, then rereads the plan and activity list to confirm failed attempts left them unchanged. It also verifies a valid planting transition, idempotent retry without duplicate activity, retrieval of the actual date and `user_reported` verification, and retrieval of the completed plan after disposing and clearing the engine.
- The UI accepts the server's successful PATCH response before showing the transition success notice. It does not claim that a failed write was saved.
- API tests use generated synthetic SQLite databases under `.test-runtime`, set `CROP_PULSE_DATABASE_URL` before schema setup, and do not target the owner-designated development database.
- Plan status and planting activity remain farmer-reported records. This change does not verify that planting occurred, infer crop stages, or convert provisional agronomic guidance into approved guidance.

## 5. Regression and quality checks

Baseline before editing was the immediately preceding Phase 7 run on the same application source: 181 Python tests and 48 frontend tests passed, with typecheck, lint, and isolated Vite build passing. Git was unavailable and the project has no `.git`, so repository-wide pre-existing edits could not be inventoried. Verified copies of the files to be edited were made before changes; hashes are recorded below.

| Command | Result |
|---|---|
| `\.venv\Scripts\python.exe tests\windows_safe_pytest.py tests\test_backend_api.py::test_plan_lifecycle_transitions_record_actual_planting_once_and_persist tests\test_backend_api.py::test_owner_scope_blocks_other_farmer_and_unauthorized_access` | **2 passed, 1 AnyIO pytest assert-rewrite warning.** Isolated backend fixtures. |
| `npm.cmd test -- --configLoader native --pool=threads --maxWorkers=1 src/App.test.tsx -t "loads and creates saved crop plans"` | **1 passed, 31 skipped.** Focused React regression. |
| `\.venv\Scripts\python.exe tests\windows_safe_pytest.py` | **181 passed, 1 warning, exit 0, 116.93s.** Warning: `PytestAssertRewriteWarning` because AnyIO was already imported. |
| `npm.cmd test -- --configLoader native --pool=threads --maxWorkers=1` | **48 passed across 6 files.** Vitest/jsdom printed `Not implemented: navigation to another Document`; no test failed. |
| `npm.cmd run typecheck` | Passed, exit 0. |
| `npm.cmd run lint` | Passed, exit 0. |
| `.\node_modules\.bin\vite.cmd build --configLoader native --outDir ..\.test-runtime\phase8-build-20261028 --emptyOutDir false` | Passed, exit 0; output was written to the new isolated directory. `frontend/dist` was not the build destination. |

The complete Python suite includes migration regression tests; those test cases create and migrate only temporary synthetic SQLite databases under the test runner's `.test-runtime` area. No migration was applied to the designated development database or any existing application database. No migration source was changed.

During the first focused frontend rerun, an existing assertion expecting the planting date twice failed because the newly visible activity adds a third occurrence. The assertion was updated to expect the plan and activity views together; the test then passed with the new activity-content assertions retained. An initial backend command used an invalid relative Python executable path and ran no tests; the corrected command above passed.

## 6. Browser verification and remaining limits

The current read-only listener check found no listeners on ports 8000, 8001, 8501, 5173, 18001, 15173, or 5000. No network request was sent to a live service and no browser login/session was exercised. Therefore the following remain **unverified in a browser**:

- Sign-in/session behavior against a running isolated API.
- Farm selection and plan/activity persistence across a real browser refresh.
- Cross-user attempts against a live service (ownership is covered by isolated API tests).
- Mobile layout, keyboard/accessibility behavior, and actual network failure rendering.

The frontend regression uses mocked fetch. Backend persistence and authorization are covered separately through in-process FastAPI `TestClient` tests against synthetic SQLite fixtures; these tests instantiate the app in-process but do not launch a listening Uvicorn service, and they are not a live HTTP service or browser end-to-end test.

## 7. Files and rollback evidence

Application/test/documentation files changed:

- `frontend/src/pages.tsx` — reload selected-farm activities after the API confirms transition to `planted`.
- `frontend/src/App.test.tsx` — model a rejected transition followed by a successful planting response, assert no false success/activity on failure, then assert the saved activity appears and update the expected date occurrence count.
- `tests/test_backend_api.py` — extend lifecycle integration coverage to reread plan and activities after rejected transitions and prove persistent state is unchanged.
- `docs/controlled-farmer-workflow-integration-phase-8.md` — this implementation and verification report.
- `README.md` — link to this report.

Before-change copies of `pages.tsx`, `App.test.tsx`, and `README.md` are stored at:

`.backups/phase8-farmer-workflow-20261028-093228-2adafd2f/`

The copies matched their originals by SHA-256 before editing:

| Original | SHA-256 before change |
|---|---|
| `frontend/src/pages.tsx` | `05FFBEEB1A8CD9DA7EEB32D88701F6B5D6AD3A253D3918447E7684E7DFCCB8BC` |
| `frontend/src/App.test.tsx` | `E5EEB5FDFBB229920F1117EBAB60F1E33ADB05E1DC9FA08F37D44CEDBE1C77B3` |
| `tests/test_backend_api.py` | `5774CC77E50ACF0B3DA0AF5CD2F498C06C58314910761FA40C1B1E83DAB69BFF` |
| `README.md` | `82A4992D2E56B39DA0091A84015C891651773C153A9A5633D6EBE2CD2AA3BB6D` |

The final comparison against these copies showed only the described activity-refresh implementation, its regression fixture/assertions, and the README report link. Git was unavailable, so no complete repository diff or clean-working-tree claim is made.

## 8. Data preservation and readiness

- No application source beyond the focused React change, API code, config, dependencies, schema, migration history, or production settings were modified.
- No designated development/application database or backup was written. The regression suite created synthetic test databases only under `.test-runtime`; migration tests operated only on disposable test paths.
- No NISR file or manifest, agronomic rule, or review-decision file was changed. The NISR CSV SHA-256 still matches its manifest; `rules.json` and `review_decisions.json` retain their previously recorded hashes and zero-approved-rule state.
- No real account, farmer data, message, weather alert, or agricultural recommendation was created.
- The production bundle was written to `.test-runtime/phase8-build-20261028`; `frontend/dist` was not used as an output target.
- No listening application service was started, stopped, restarted, or contacted. Backend test cases ran FastAPI in-process with `TestClient` against temporary databases.

The product remains **DEVELOPMENT ONLY**. The completed tests establish a connected plan-to-planting activity path in source and isolated automated tests. They do not establish a live browser journey, hosted runtime/database identity, real-world planting verification, agricultural validation, or production readiness.

## 9. Remaining gaps and next phase

The next step is a separately authorized browser integration run against a verified disposable API/database and dedicated synthetic accounts. It should verify refresh and navigation, farmer ownership boundaries, failed status writes, activity-history reload failures, and desktop/mobile behavior. Continue to keep live and designated development data outside test workflows. Resolve the separate runtime identity and deployment blockers before any pilot or public deployment.
