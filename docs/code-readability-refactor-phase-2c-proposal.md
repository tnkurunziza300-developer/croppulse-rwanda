# CropPulse Rwanda — Phase 2C Readability Refactor Proposal

**Date:** 26 October 2026  
**Status:** Planning only. No application changes or tests were performed.

## Decision

Select a narrow React extraction from `FarmsPage`: move the **New farm profile** controlled form into a dedicated presentational component. This is smaller and lower risk than extracting plan/recommendation state, restructuring Streamlit pages, or splitting FastAPI routers.

## Evidence and current problem

The Phase 1 audit identifies `frontend/src/pages.tsx::FarmsPage` as combining several workflows and recommends extracting a low-coupling React view first. The current form markup is a single long JSX expression around line 333. It contains three fields (farm name, district, optional area), a close button, and a save button. The form is visually difficult to scan and sits in a component already managing many farm, field, activity, plan, and recommendation states.

The existing `createFarm` handler around lines 216–219 owns submission, calls `POST /v1/farms`, updates notices, closes the form, and reloads the farm list. Those responsibilities should stay in `FarmsPage`. The extraction should move presentation only.

The existing `frontend/src/App.test.tsx` test **“creates a farm through the persistent API workflow”** covers opening the form, entering a name and area, submitting, displaying success, and showing the resulting farm. Its `fetch` is stubbed; it does not require a running API or database.

## Proposed change

Add `frontend/src/FarmProfileForm.tsx`, a controlled presentation component that receives the current values, change callbacks, district options, busy state, submit callback, and close callback as props. Replace the inline form in `FarmsPage` with that component. Keep state ownership and all mutations in `FarmsPage`.

Example shape:

```tsx
<FarmProfileForm
  name={farmName}
  district={district}
  area={area}
  districts={DISTRICTS}
  busy={busy}
  onNameChange={setFarmName}
  onDistrictChange={setDistrict}
  onAreaChange={setArea}
  onSubmit={(event) => void createFarm(event)}
  onClose={() => setFormOpen(false)}
/>
```

The component would preserve the existing field labels, required/optional status, numeric bounds, maximum lengths, default district behavior, CSS classes, accessible close-button label, disabled/busy label, and form submit semantics. It would not import or call `api`, access auth/session state, or contain agricultural rules.

## Expected behavior and dependencies

- **Expected behavior impact:** None intended. This is a view extraction; same values and callbacks remain owned by the parent.
- **Dependencies:** Existing React and TypeScript only; no package changes.
- **API/database/auth:** No changes to endpoints, request payloads, authentication, authorization, ownership, or persistence. `createFarm` remains the only submit handler.
- **Recommendation logic:** Not touched.

## Risks and regression coverage

The main risks are accidentally changing a form constraint, submitting twice or not at all, changing the default district, losing the close behavior, or changing the loading state while saving. Keeping the parent state and handler intact limits those risks.

Recommended test: extend the existing farm-creation test to assert that the submitted mocked request contains the same district and area values, and that the form closes after success. The current test already verifies successful submission and refreshed farm display. If the component is independently exported, an isolated rendering test is optional; avoid adding a second test that duplicates the page workflow without a distinct assertion.

Safe checks for a future authorized implementation:

1. `npm run test -- src/App.test.tsx -t "creates a farm through the persistent API workflow"` — the selected test mocks `fetch`; it does not contact a service or database.
2. `npm run typecheck` — TypeScript static check; no application startup or database access.
3. `npm run lint` — frontend static lint; no application startup or database access.
4. `npm run build` — frontend production compilation; no application API or database access. It writes generated frontend build output, so confirm that output directory is expected and preserve any pre-existing build artifacts before running.

`frontend/node_modules`, `npm`, and `node` are present in the current environment. No commands above were run for this proposal. The prior pytest cache permission warning does not apply to these Vitest/npm checks; no pytest command is proposed.

## Exact expected file list

- `frontend/src/pages.tsx` — replace the inline farm-profile JSX with a component call; keep state and `createFarm` unchanged.
- `frontend/src/FarmProfileForm.tsx` — new controlled presentational form.
- `frontend/src/App.test.tsx` — strengthen the existing farm-creation regression assertion if needed to establish parity.
- `docs/code-readability-refactor-phase-2c-proposal.md` — this proposal.

No Streamlit, FastAPI, schema, database, migration, dependency, or configuration files are in scope.

## Rollback and baseline comparison

Before implementation, create a unique, non-existing temporary rollback directory and copy each existing file that may change (`frontend/src/pages.tsx` and `frontend/src/App.test.tsx`) into it. Record SHA-256 hashes for each original and copy and stop if they differ. Confirm `frontend/src/FarmProfileForm.tsx` does not already exist; if it does, inspect and stop rather than overwrite it.

After implementation, compare current `pages.tsx` and `App.test.tsx` against the saved copies using a unified diff generated from the copies (for example, Python's standard-library `difflib`). Review that diff and confirm only the intended extraction and test assertion changed. Roll back by restoring the verified copies and removing only the newly created component file. Preserve the proposal and any pre-existing generated output. Git is unavailable per the Phase 2B report, so this plan does not rely on Git for the baseline.

## Runtime and data safety

The focused React test uses a mocked `fetch` implementation and synthetic fixture values. It does not use the designated development database or contact a running service. Typecheck and lint are static. Build is local compilation only but may write `frontend/dist`; preserve existing output as noted. No migrations or Python tests are required for this view-only change.

## Stop conditions

- A rollback copy/hash check fails or cannot be created without overwriting an existing backup.
- The proposed component file already exists or has user work that makes a simple extraction unsafe.
- The farm-creation handler, API contract, or form requirements have changed from the inspected version.
- The focused UI test reveals a regression; do not change persistence or product behavior to force it to pass.
- Running the build would overwrite output that cannot be preserved safely.

**Authorization boundary:** This document is a proposal only. Wait for explicit approval before modifying application or test files.
