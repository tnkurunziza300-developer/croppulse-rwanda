# CropPulse Rwanda — Field Decision-Support Summary, Phase 21

**Date:** 2026-10-28  
**Database migration:** none; repository head remains `0019_soil_records`.  
**Readiness:** CropPulse remains **development only**.

## Implementation

The React **My farms** workspace now includes an accessible, closed-by-default **Field decision-support summary**. The farmer opens it and selects the whole farm or one of its existing fields. It reads existing authenticated endpoints for crop plans, irrigation records, soil observations, soil-test records, harvests, the farm timeline, and saved weather forecasts. It performs no writes and creates no duplicate activity records. The detail requests are deferred until the summary is opened.

For a field view, records are included only when their stored `field_id` matches that field; farm-level records are not assigned to a field. For the whole-farm view, farm-level and field-linked records are both shown. The API endpoints remain responsible for account ownership; the forecast list is the current farmer's own saved forecasts and the summary only attaches entries whose field ID matches a field in the selected farm.

The summary labels plans as provisional; distinguishes proposed planting targets from stored actual planting dates; shows irrigation as farmer reported and preserves each recorded quantity/unit without combining measurements; separates visible soil observations from farmer-entered test transcriptions; and labels harvest/activity information as farmer reported. Weather entries show provider/source and retrieval time when present and preserve the provider's stale status. Coordinates are described as farmer supplied and not independently verified. Forecasts are external model forecasts, not observations or agronomic advice.

Missing values remain explicitly unrecorded. Missing records are not evidence that an event did not happen. The summary provides evidence-gap messages and record-keeping or qualified local extension next steps only. It does not rank crops, assess suitability, diagnose soil or disease, predict yield, or prescribe fertilizer or irrigation. Empty, loading, partial API failure/retry, and no-record states are included. Field filtering is client-side over the authenticated selected-farm responses; no other farmer's data is requested or displayed.

## Files changed

- `frontend/src/FieldDecisionSummary.tsx` — summary disclosure, record aggregation and evidence-boundary labels.
- `frontend/src/FieldDecisionSummary.test.tsx` — display, field filtering, unknown/null values, stale weather, partial errors/retry, loading/empty states, and read-only request tests.
- `frontend/src/pages.tsx` — integration in the React farm workspace.
- `frontend/src/styles.css` — responsive layout and summary styles.
- `docs/field-decision-support-summary-phase-21.md` — this implementation record.
- `README.md` — link to this report.

No backend route, model, schema, database, or migration changed. Existing owner-scoped APIs provide the data, and no migration test or real database write was needed.

## Verification

| Check | Result |
|---|---|
| Focused component tests: `npm test -- --configLoader native --pool=threads --maxWorkers=1 src/FieldDecisionSummary.test.tsx` | **4 passed** |
| Full Python suite: `\.venv\Scripts\python.exe tests\windows_safe_pytest.py` | **205 passed**, 1 existing AnyIO pytest assert-rewrite warning |
| Full frontend suite: `npm test -- --configLoader native --pool=threads --maxWorkers=1` | **73 passed across 11 files** |
| `npm run typecheck` | Passed |
| `npm run lint` | Passed |
| Isolated production build: `npm run build -- --configLoader native --outDir .phase21-final-build-20261028-202600` | Passed; temporary output removed; normal `frontend/dist` was not targeted |
| Alembic head: `\.venv\Scripts\python.exe -m alembic heads` | `0019_soil_records (head)` |

No authenticated browser workflow was performed. Automated UI tests do not verify real deployment/API connectivity, browser rendering on a farmer device, or accessibility with assistive technology. No PostgreSQL compatibility or production readiness is claimed. No migration was added or applied, and no real database was migrated, reset, seeded, or otherwise modified.

## Remaining limits

The source APIs return existing records, and the weather API's saved forecast listing is bounded to the latest 50 entries for the signed-in user. No forecast match means none was found in that returned list; it does not establish that no older forecast exists or that weather conditions are absent. The timeline remains bounded by its existing API. No stale-time threshold is invented for soil results, and no external soil dataset, verified laboratory integration, or approved agronomic rules are assumed. CropPulse remains **development only** pending technical, security, evidence, privacy, operational, and field validation.
