# CropPulse Rwanda — Phase 2C FarmsPage Readability Refactor

**Date:** 26 October 2026  
**Project root:** `C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda`

## Change summary

The inline **New farm profile** JSX was extracted from `FarmsPage` into `FarmProfileForm`, a controlled presentation component. The parent still owns all form state, `createFarm`, the API request, success/error notices, and post-save farm reload. The component receives values and callbacks through props; it has no API, auth, database, or recommendation dependencies.

The form retains its fields and constraints, district options and default, labels, optional-area placeholder, CSS classes, close-button accessibility label, save-disabled state, and busy label. `X` is imported by the new component rather than the page module.

## Files changed

- `frontend/src/pages.tsx` — imports and renders the extracted form; parent state and mutation handler remain in place.
- `frontend/src/FarmProfileForm.tsx` — new controlled form presentation component.
- `frontend/src/App.test.tsx` — strengthens the existing farm-creation test with submitted-payload and close-after-success assertions.
- `docs/code-readability-refactor-phase-2c-report.md` — this report.

No API contracts, auth behavior, database code, agricultural recommendation logic, Streamlit workflow, dependency, or configuration changed.

## Rollback and before-change evidence

Before editing, copies were made in the unique directory:

`C:\Users\Student\AppData\Local\Temp\croppulse-phase2c-rollback-f0c3a4800a8c4629a80ae8fac9c71fcb`

SHA-256 values recorded before editing:

- `frontend/src/pages.tsx`: `4AA3C1D63CD427D58D29CB4D14E6ADF276DA2A8F5EE76CA90CAF6C3086F3BB68`
- `frontend/src/App.test.tsx`: `90F366250AF140E8F659D7965D230BD2245485DD5C95D8CFC0D79722F9905FD0`

Both backup copies matched their originals at creation. They remain available. A unified comparison against those copies showed only the form import/replacement in `pages.tsx` and the targeted payload capture/assertions in `App.test.tsx`. To roll back, restore those two verified copies and remove `frontend/src/FarmProfileForm.tsx`.

Git was unavailable, so a repository-wide Git status or full working-tree diff could not be established. The comparison was limited to the files this task edited. `frontend/dist` existed before the change; its observed top-level timestamps remained unchanged, and the build was not run.

## Test isolation

The targeted existing test in `frontend/src/App.test.tsx` replaces global `fetch` with a synthetic in-memory handler. It does not connect to the API service or a database. No service was contacted or started. The prior pytest cache permission warning does not affect these frontend commands; no pytest command was run.

## Checks and results

- `npm run test -- src/App.test.tsx -t "creates a farm through the persistent API workflow"` — **did not reach the test**. Vite failed loading `vite.config.ts` with `Error: spawn EPERM`. The test is therefore **unverified**, not passing.
- `npm run typecheck` — **passed** after correcting a type in the new test assertion.
- `npm run lint` — **passed** (`eslint src` exited 0).
- `npm run build` — **not run**. The existing `frontend/dist` contains files and the normal build writes there; overwriting existing output was not necessary to complete this bounded refactor.

No database tests or migrations were run. No backend or Python checks were needed for this React-only change.

## Compatibility and unresolved limitations

The form state remains in `FarmsPage`, and the same callback still submits the existing `POST /v1/farms` payload. The existing test fixture uses mocked fetch and now asserts the district default (`Huye`), numeric area (`0.5`), farm name, successful message/list refresh, and form closure.

Because Vitest could not initialize under the current process-spawn permissions, runtime rendering behavior was not verified by the test. Typecheck and lint do not replace that test. The production build is also unverified. No browser verification was performed.

## Verdict

**REFACTOR COMPLETE — SOME CHECKS NOT RUN**

The view extraction and static frontend checks completed. The focused UI test did not start, and the production build was skipped; this report does not claim those checks passed or establish release readiness.

## Verification recovery addendum — 26 October 2026

### Vitest startup failure diagnosis

The configured command is `vitest run`, with `frontend/vite.config.ts` supplying the React plugin and the `jsdom` test environment/setup file. The previous focused command passed file and test-name filters, but the failure occurred while loading Vite's config, before the selected test ran.

The captured stack identifies Vite's Windows `optimizeSafeRealPathSync` path and Node's `child_process` spawn/exec APIs. Inspection of the installed Vite code shows that this path invokes `exec("net use", { windowsHide: true }, ...)` to discover Windows network drive mappings. The reported `spawn EPERM` therefore points to a subprocess launch restriction in the current execution environment while Vite performs its Windows path probe. It does not point to the form test, app code, or a project-specific `vite.config.ts` plugin error. The evidence does not identify whether the underlying restriction is the sandbox, endpoint policy, or another Windows process policy; no elevated retry or process-policy bypass was attempted.

Vitest's installed CLI exposes `--configLoader` options (`bundle`, experimental `runner`, and `native`). They are alternate configuration-loading modes, but source inspection alone does not prove that the full Vitest startup avoids the same Vite Windows real-path probe. No alternate loader was run because it would be an unverified workaround for the blocked subprocess. The focused UI test remains unverified.

### Reconfirmed checks and build assessment

- `npm run typecheck` — rerun during this recovery; **passed** (`tsc --noEmit`, exit code 0).
- `npm run lint` — rerun during this recovery; **passed** (`eslint src`, exit code 0).
- Vitest — not rerun. The previously captured command exited during Vite config loading with `spawn EPERM`, before test collection/execution.
- Production build — not run. `frontend/dist` existed before the work, and `npm run build` runs `tsc -b && vite build`. A Vite `--outDir` override alone would not isolate all build side effects: TypeScript build mode may update build metadata, while Vite still loads the config through the affected Windows path. An isolated full build was not demonstrated, so preserving existing artifacts takes priority.

### Read-only source comparison

The saved rollback copies were read and compared to the current source using Python's standard-library unified diff. Their hashes remain consistent with the values recorded above. The only differences in `pages.tsx` are removal of the inline form/imported icon and insertion of the `FarmProfileForm` import/call with explicit props. The only differences in `App.test.tsx` are the typed mock payload capture and assertions for district, area, and close-after-success. The new component was confirmed to be present; it did not exist before implementation according to the pre-change check. No Git status or full repository diff is available because Git is not installed.

The test's `fetch` is stubbed in the selected case, and neither the form component nor its test uses a database. No application service was contacted or started during this recovery.

### Recommended next action

Run the exact focused Vitest command in the project's ordinary Windows development terminal, without elevation, after confirming that environment permits Node to launch its normal child processes. If it still reports `spawn EPERM`, have the environment owner investigate the process-launch policy rather than changing application configuration. For a later production build, use a reviewed isolated output/build-info location only after the Vite config startup issue is resolved; do not target the existing `frontend/dist` until its contents are intentionally backed up or otherwise protected.

**Recovery conclusion:** `FarmProfileForm` remains statically typechecked and linted, but its UI regression test and production build are unverified. No application/test/configuration/database changes were made during this recovery; only this report was updated.
