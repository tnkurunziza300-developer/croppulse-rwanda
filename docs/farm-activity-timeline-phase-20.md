# CropPulse Rwanda — Unified Farm Activity Timeline, Phase 20

**Date:** 2026-10-28  
**Scope:** read-only aggregation of existing authenticated farmer records.  
**Database migration:** none; Alembic head remains `0019_soil_records`.  
**Readiness:** CropPulse remains **development only**.

## Implementation

The React **My farms** workspace now shows a unified timeline for its selected farm. The new `GET /v1/farms/{farm_id}/timeline` endpoint reuses the existing plan, activity, irrigation, soil observation, soil-test, harvest, and post-harvest tables. It creates no timeline rows and changes no source record. The endpoint checks authenticated farm ownership before querying and scopes field-name resolution to that farm. It returns no farmer ID or private notes. Results default to the latest 300 entries, accept a validated limit up to 500, and set `has_more` when additional entries exist.

Entries cover crop-plan creation, a separately stored actual planting date, regular dated farm activities, irrigation events, soil observations and soil-test transcriptions, harvest records, and post-harvest observations. A plan's creation entry uses `created_at`; planting uses only `actual_planting_date`. The existing status workflow does not store dates for monitoring/harvesting/completion transitions, so the timeline does not invent those events. The application's generated Planting activity duplicates the plan's actual planting event; the timeline recognizes its idempotency key and represents that event once. Other farmer-entered activities remain distinct records.

Dates are sorted newest first; an entry lacking a source date is sorted last and labeled **Date not recorded**. The UI does not infer missing dates, measurements, or field links. Descriptions show a single record's values and explicit units without combining quantities. Farmer-entered data is labeled **Farmer reported** (soil-test report transcriptions also state the source is not independently verified); crop-plan creation is labeled provisional. Links jump to the existing record section in the workspace. Empty, loading, retry/error, and bounded-results states are included. An empty timeline explicitly does not mean no activity occurred.

## Data and authorization boundaries

- Farm records are limited to the authenticated farmer's requested farm; a different owner's farm returns the existing not-found response.
- Field names are attached only through field IDs belonging to the requested farm. Sources without a stored field association remain farm-level.
- Activity notes and personal notes are not copied into the timeline description.
- Existing APIs and schema remain the source of truth. There is no timeline write or migration.
- No live browser flow, production service, or real application database was used.

## Changed files

- `backend/api.py`, `backend/schemas.py`
- `frontend/src/api.ts`, `frontend/src/pages.tsx`, `frontend/src/FarmTimeline.tsx`, `frontend/src/FarmTimeline.test.tsx`, `frontend/src/styles.css`, `frontend/src/App.test.tsx`
- `tests/test_backend_api.py`
- `docs/field-evidence-phase.md`, `README.md`
- This report

## Verification

| Check | Result |
|---|---|
| Focused timeline API test: `\.venv\Scripts\python.exe tests\windows_safe_pytest.py tests\test_backend_api.py -k farm_timeline` | **1 passed**, 31 deselected, 1 existing AnyIO assert-rewrite warning |
| Focused timeline component: `npm test -- --configLoader native --pool=threads --maxWorkers=1 src/FarmTimeline.test.tsx` | **3 passed** |
| Full Python suite: `\.venv\Scripts\python.exe tests\windows_safe_pytest.py` | **205 passed**, 1 existing AnyIO assert-rewrite warning |
| Full frontend suite: `npm test -- --configLoader native --pool=threads --maxWorkers=1` | **69 passed across 10 files** |
| `npm run typecheck` | Passed |
| `npm run lint` | Passed |
| Isolated production build | Passed using `npm run build -- --configLoader native --outDir <unique temporary directory>`; `frontend/dist` was not the output target |
| Alembic heads | `0019_soil_records (head)` |

The final backend full-suite run includes a regression that asserts a plan's actual planting date and its generated idempotent activity appear only once in the timeline. All Python API test databases are disposable; no migration was applied and no real application database was modified. No browser verification was performed, and no PostgreSQL compatibility claim is made.

## Remaining work

Manual authenticated browser checks remain outstanding for farm switching, source links, empty/loading/error states, and timeline readability at narrow widths. The current event model does not preserve dated history for crop-plan progress transitions beyond actual planting. CropPulse remains **development only**.
