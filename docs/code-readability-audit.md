# CropPulse Rwanda — Code Readability and Maintainability Audit

**Date:** 26 October 2026  
**Scope:** Phase 1 read-only review requested by the master refactoring prompt. This is a static maintainability review, not a security certification, correctness audit, or production-readiness decision.

## Executive summary

The repository has recognizable boundaries for the React client, FastAPI service, Streamlit application, and shared utilities. The main maintainability pressure comes from a few large modules that mix multiple workflows, not from a need to replace the architecture. The safest next step is incremental extraction behind existing contracts, with regression coverage and one domain at a time.

No application source, configuration, data, or database was changed. No tests, builds, migrations, application startup, or database inspection were performed. The `git` executable was unavailable in this environment, so repository status could not be collected.

## Areas reviewed

- Application entry points and page composition: `app.py`, `plan.py`, `views.py`, `product_pages.py`.
- API and persistence boundaries: `backend/api.py`, `backend/client.py`, `backend/db.py`, `backend/models.py`, `backend/schemas.py`, `utils/frontend_services.py`.
- React composition and API client: `frontend/src/App.tsx`, `frontend/src/pages.tsx`, `frontend/src/api.ts`, `frontend/src/auth.tsx`.
- Project guidance and current architecture claims: `README.md`, `docs/backend-phase-1.md`, `docs/react-migration-audit.md`, and the recent application audit/readiness documents.
- Existing test names and package scripts were inspected statically to assess where future extractions need regression protection. No checks were run.

## Prioritized findings

### High — FastAPI route module combines many application domains

**Evidence:** `backend/api.py` is approximately 2,012 lines. Its module-level helpers and route handlers cover runtime configuration and middleware, browser authentication and account recovery, handoffs, weather and alerts, messaging, administration and review, crop-health reports, farms, fields, activities, and crop plans. Representative route groups begin around lines 442, 560, 833, 1077, 1205, 1416, 1587, 1762, and 1880.

**Why this is hard to maintain:** A change in one domain is made in a file that also owns unrelated authorization and persistence flows. Reviewers must navigate a large module to understand route registration and shared dependencies. The file size itself is not a defect, but the demonstrated domain concentration increases change-review and merge-conflict costs.

**Recommended change:** In a later, separately authorized implementation phase, extract routers by domain (for example, auth, weather, messaging/admin, crop-health, and farm/planning) while keeping a single application factory/entry point and preserving URL paths, dependency functions, middleware order, and response contracts. Move one router at a time and add route-registration and authorization regression checks before each move.

**Risk:** High if done broadly. Import cycles, missing router inclusion, changed dependency overrides, altered middleware behavior, and route-order changes can break callers or security controls. Do not perform a bulk rewrite.

### High — React `FarmsPage` owns several workflows in one component

**Evidence:** `frontend/src/pages.tsx` is about 596 lines; `FarmsPage` starts near line 143 and maintains state for farm selection, fields, activities, crop plans, plan lifecycle, recommendations, comparison, and multiple forms and notices. Loading and mutation functions are declared inside the component, alongside the rendered views.

**Why this is hard to maintain:** State for distinct user tasks shares one component lifecycle. A future edit to forms or selection logic can interact with unrelated async loading and plan state, making behavior harder to reason about and review.

**Recommended change:** Extract cohesive view components and narrowly scoped hooks for farm/field selection, activity records, and plan/recommendation workflows. Keep API operations and existing endpoint contracts unchanged. Preserve request cancellation/stale-response guards and the current farmer ownership model.

**Risk:** High if state is moved without preserving effect ordering, selected-farm resets, loading/error semantics, form persistence, and in-flight request guards. Prefer small extractions with existing UI tests expanded around the affected user journey.

### Medium — Streamlit farmer workflows are concentrated in `product_pages.py`

**Evidence:** `product_pages.py` is about 535 lines and defines crop planning, farm records, market/economics, review queue, extension notes, pest reporting, feedback, weather, and cooperative workflows. The `crop_plan_page`, `farm_records_page`, and other page functions are all in this module.

**Why this is hard to maintain:** A shared page file has grown into a collection of distinct workflows with different persistence, evidence, and session-state behavior. Finding a page-specific change requires navigating unrelated forms and helpers.

**Recommended change:** Move cohesive page families into modules incrementally, leaving common presentation and shared data helpers in a small common module. Maintain the current Streamlit navigation registration and `session_state` keys during the first pass; do not combine restructuring with product behavior changes.

**Risk:** Medium to high because Streamlit reruns pages and relies on stable widget keys and session-state behavior. Kinyarwanda/English labels and existing evidence caveats must remain intact.

### Medium — API schema contracts are grouped in one broad module

**Evidence:** `backend/schemas.py` is about 505 lines and contains account/admin, messaging, review, farm/field, weather, crop planning, activity, and crop-health models.

**Why this is hard to maintain:** Related contracts are not discoverable by domain, and the growing module makes it easier to overlook which API workflows share a schema. This is a maintainability concern, not evidence of incorrect validation.

**Recommended change:** If API routers are later split, split schema definitions along the same domain boundaries and retain compatibility re-exports from `backend.schemas` during transition where existing imports depend on them.

**Risk:** Medium. Pydantic model names, OpenAPI schema identifiers, import paths, and generated client expectations may change. Compare OpenAPI output and validation behavior before and after any move.

### Medium — Streamlit backend client combines transport fallback and response policy

**Evidence:** `backend/client.py::request` handles token lookup, request construction, optional `httpx` transport and `urllib` fallback, timeout/network errors, JSON decoding, expired-session cleanup, API error detail formatting, and response validation in one function. `requirements.txt` includes `httpx`, while the fallback is explicitly retained for environments where it is missing.

**Why this is hard to maintain:** Transport-specific behavior and application-level error/session policy are interleaved, so fixing one path requires checking parity in the other.

**Recommended change:** Extract small transport adapters and a shared status/payload normalization step, retaining the fallback until the supported launch environments and dependency policy explicitly make it unnecessary. Keep the user-facing error mapping and session clearing behavior stable.

**Risk:** Medium. Divergent handling of HTTP errors, timeouts, JSON bodies, 204 responses, and 401 cleanup could cause regressions. Tests should exercise both transport paths.

### Low — Streamlit entry-point composition is dynamic and carries compatibility reload logic

**Evidence:** `app.py` builds pages through a local `page()` factory, wraps analytical pages with `guarded()`, and conditionally reloads imported modules when expected helper functions are missing. The comments explain that this addresses Streamlit reruns and stale imported modules.

**Why this is hard to maintain:** The page registry and runtime compatibility behavior are implemented in the entry module, while reload conditions depend on helper-name lists. This makes the startup path less straightforward to trace.

**Recommended change:** Document the page-registration/reload rationale and add a focused composition test before considering any simplification. Only remove reload handling if the supported launch/reload behavior is demonstrated without it.

**Risk:** Medium. Removing or changing reload behavior can reintroduce stale-module errors in long-running Streamlit sessions. The current unusual pattern is not, by itself, a confirmed defect.

### Low — Some Streamlit rendering and state logic is compressed into dense statements

**Evidence:** `app.py` and `product_pages.py` contain compact one-line conditionals and multiple UI/data actions in single blocks. For example, `app.py::guarded` combines demo warnings, unavailable-data handling, filter-empty handling, and page dispatch.

**Why this is hard to maintain:** Dense statements make control flow and early exits less visible, particularly in page code that also handles persistent account data and temporary session data.

**Recommended change:** Expand only the most behavior-sensitive blocks into named helpers with explicit inputs and returns. Treat this as a readability change, not an invitation to change defaults, wording, or error behavior.

**Risk:** Low to medium. Even formatting-oriented edits in Streamlit can alter indentation-sensitive control flow; validate page behavior after changes.

## Confirmed problems versus preferences

### Confirmed maintainability concerns

- Several high-traffic files contain multiple distinct workflow domains, with the examples and locations documented above.
- Important responsibilities are combined in `backend/client.py::request` and in the React `FarmsPage` stateful component.
- The Streamlit entry point uses conditional module reloads that require special care during changes; their comments document the reason, so they should not be removed casually.

### Subjective or not established as defects

- File length alone does not establish poor design or incorrect behavior.
- The code's naming, framework choices, dynamic Streamlit page factory, and single-file React API client are not defects solely because another style is possible.
- This static review did not establish runtime bugs, security vulnerabilities, performance problems, or a need to replace Streamlit or the current backend.
- No recommendation is made to introduce a new framework, state-management library, dependency, service, or database.

## Existing test protection to preserve

Static inspection found existing test coverage by area, including backend API/security tests (`tests/test_backend_api.py`, `tests/test_react_security_api.py`), farm/planning lifecycle and migration tests, Streamlit app tests (`tests/test_app.py` and related UI tests), and React tests under `frontend/src` (including app, weather, crop-health, and statistics pages). The frontend package defines test, typecheck, lint, and build scripts. These files and scripts were not executed; their presence is not a claim that the checks currently pass.

Before any Phase 2 extraction, add or confirm focused tests for route registration, authentication/authorization boundaries, farmer ownership, error/loading states, and Streamlit/React workflow semantics. Run relevant tests before and after each small move; compare API/OpenAPI contracts wherever backend imports or schemas move.

## Suggested order for a future refactor

1. Extract one low-coupling React view from `FarmsPage` behind existing props and tests.
2. Extract one FastAPI router at a time, beginning with a well-bounded domain, without changing paths or dependencies.
3. Split Streamlit workflow modules while preserving navigation keys, widget keys, session-state names, and bilingual content.
4. Separate the Streamlit client's transport handling only after tests cover both `httpx` and fallback behavior.
5. Reorganize schema modules alongside router extraction, with compatibility imports until consumers migrate.

This order is a proposal, not authorization to begin Phase 2. Security-sensitive authentication, access-control, migration, agronomic evidence, and dataset behavior should remain unchanged during readability-only work unless a separately reviewed defect is found.

## Audit limitations

- This review was static; no Python tests, frontend tests, typecheck, lint, or production build ran.
- No browser workflow or service was contacted.
- No database was opened or inspected; no dataset, manifest, migration, registry, or application state was changed.
- `git status` could not be checked because `git` was not available in the shell environment.
- Findings identify maintainability risks and proposed refactor boundaries. They do not establish production readiness or certify behavior.

**Phase 1 status:** Audit document completed. Stop here and wait for explicit authorization before implementing any refactor.
