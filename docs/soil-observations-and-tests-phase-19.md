# CropPulse Rwanda — Soil Observations and Soil-Test Records, Phase 19

**Date:** 2026-10-28  
**Scope:** persistent farmer-reported soil observations and farmer-entered soil-test report values in the React farm workspace and FastAPI service.  
**Readiness:** CropPulse remains **development only**. This feature records information and does not provide agronomic recommendations.

## Implementation

Added two distinct farm-linked record types:

- **Soil observations:** observation date; optional farmer-described soil type, drainage, visible erosion, management/conservation practices, and notes.
- **Soil-test records:** test date; optional unitless pH on a 0–14 scale; optional reported N/P/K values with explicit units; optional organic matter with explicit units; and optional provider/laboratory name, report reference, provenance, and notes.

Measurements remain nullable. Nutrient and organic-matter values require units when supplied, numeric values must be finite and nonnegative, and pH is range-checked. No missing value becomes zero. The UI labels all entries as farmer reported and not independently verified. Provider names and report references are entered by the farmer and do not establish laboratory provenance. No thresholds, conversions, diagnosis, fertilizer quantities, or product advice were added.

Every API list, create, detail, and update operation derives the farmer from the authenticated session and verifies ownership of the farm. Optional field references must belong to that same farm. Unknown request fields are rejected, so a client-supplied farmer ID cannot select the owner. Updates preserve the same ownership/link checks.

## Migration and preservation

Added additive Alembic migration `0019_soil_records`, descending from `0018_irrigation_records`. It creates `soil_observations` and `soil_test_records`, including nullable field links, indexes, unit/value pairing constraints, nonnegative-value checks, and the pH range check. Downgrade removes only the two new tables.

Upgrade, preservation assertions, and downgrade were exercised against UUID-named disposable SQLite databases under `.test-runtime`; existing synthetic harvest, post-harvest, irrigation, crop-plan, and farm records remained unchanged. The real application database was not migrated, seeded, reset, or altered.

## Files changed

- `backend/models.py`, `backend/schemas.py`, `backend/api.py`
- `backend/migrations/versions/0019_soil_records.py`
- `frontend/src/api.ts`, `frontend/src/pages.tsx`, `frontend/src/SoilRecords.tsx`, `frontend/src/SoilRecords.test.tsx`, `frontend/src/styles.css`
- `tests/test_backend_api.py`, `tests/test_harvest_migration.py`, `tests/test_runtime_diagnostics.py`
- `docs/field-evidence-phase.md`, `README.md`
- This report

The diagnostics regression expectation now follows the migration head (`0019_soil_records`) when the test upgrades its disposable database to `head`.

## Verification

| Check | Result |
|---|---|
| Focused Python API and migration checks: `\.venv\Scripts\python.exe tests\windows_safe_pytest.py tests\test_backend_api.py tests\test_harvest_migration.py` | **32 passed**, 1 existing AnyIO assert-rewrite warning |
| Focused frontend component check: `npm test -- --configLoader native --pool=threads --maxWorkers=1 src/SoilRecords.test.tsx` | **3 passed** |
| Full Python suite: `\.venv\Scripts\python.exe tests\windows_safe_pytest.py` | **204 passed**, 1 existing AnyIO assert-rewrite warning |
| Full frontend suite: `npm test -- --configLoader native --pool=threads --maxWorkers=1` | **66 passed across 9 files** |
| `npm run typecheck` | Passed |
| `npm run lint` | Passed |
| Alembic heads | `0019_soil_records (head)` |
| Production build to a unique temporary output directory | Passed with `npm run build -- --configLoader native --outDir <temporary-path>`; `frontend/dist` was not used as the output target |

The first full Python run found a stale test assertion expecting migration `0018_irrigation_records`; it was corrected to the actual new head, and the rerun passed. The initial isolated build invocation without the native config loader hit Windows `spawn EPERM` during Vite config resolution; the native-loader invocation succeeded. No source test was weakened to mask a feature failure.

## Remaining verification

No browser workflow was run. Manual browser checks remain outstanding for create/list/detail/correction, field selection, validation messages, and error/retry behavior. PostgreSQL migration compatibility is not established here. CropPulse stays **development only** pending its existing independent release, evidence, privacy, deployment, licensing, and operational prerequisites.
