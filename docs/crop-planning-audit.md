# Crop planning audit — 2026-10-22

## What exists today

- **React entry and route:** `frontend/src/App.tsx` owns authenticated routing. Crop plans are part of the farmer-only **My farms** page in `frontend/src/pages.tsx`; there is no standalone React planning page.
- **Streamlit workflow:** `app.py` routes to Crop Decisions, Crop Plan, Season Calendar, and Farm Planner. `plan.py` calls the existing `utils.recommender.recommend()` engine and displays ranked candidates, exclusions, reasons, risks, historical NISR context, and evidence limitations. `product_pages.py::crop_plan_page` creates a provisional activity checklist and can save it through the existing account API or keep it in session state.
- **Recommendation logic (current after Phase 2):** `utils/recommender.py` validates district, season, and optional elevation; applies existing configured altitude/water checks with provisional-status labeling; and uses the CropPulse guidance pack for its provisional order. NISR history is descriptive only and never affects ranking or suitability. Unknown conditions are disclosed. Synthetic demo rows do not affect decisions.
- **Data provenance:** `utils/data_loader.py` is the shared Streamlit/backend loader. It reads `data/verified/*.csv`, checks `data/verified/MANIFEST.json` and SHA-256, structurally validates rows, and labels validated, pending, warning, demo, or unavailable states. The NISR SAS CSV and manifest are present. Structural validation does not independently validate NISR's estimates.
- **Persistence and security:** `backend/api.py` provides authenticated, farm-owner-scoped plan create/list/status endpoints. `CropPlan` and `CropPlanEvidence` already exist; migration `0007_fields_and_evidence` added field links and evidence records. React currently saves only farmer notes in `plan_json`; its plan evidence list is therefore empty. The existing API checks farm ownership and active field membership.
- **Weather:** Open-Meteo forecasts and imported historical weather bulletins are separate existing features. The recommendation engine explicitly does not rank crops from either source. There is no justified crop-specific weather rule in the current evidence, so forecast information must remain contextual and must not be presented as seasonal climate evidence.
- **Localization:** Streamlit has partial English/Kinyarwanda strings. The current React farmer workspace is English-only. A complete Kinyarwanda planning translation is not available to claim.

## Gaps and credibility risks

1. React cannot request or compare recommendations; it saves a manual crop/date/area record only.
2. Streamlit decisions and the detailed plan are separate flows. The detailed plan's approximate seeds, harvest dates, and calendar are based on explicitly unverified CropPulse guidance and must remain labelled provisional.
3. Streamlit's plan checklist contains a stale claim that farm records are temporary even though authenticated records can persist. The checklist also uses approximate date/seed quantities, which are not official planting prescriptions.
4. The recommender's historical fit classifications and planting windows derive from unverified CropPulse guidance, not a verified Rwanda agronomy source. (The heuristic confidence wording identified in this audit was subsequently removed.)
5. SAS district/season production data can describe historical observations but cannot establish individual-farm suitability, future yield, or planting dates. Coverage varies by crop and period; the system must not turn missing cells into zero.
6. No trusted soil requirements, plot-level weather-to-planting rules, variety/seed guidance, labor/budget model, market prices, or verified objective-specific rules are connected. No supported sector-level crop rules exist.
7. The API currently stores plans and farmer notes but does not snapshot recommendation context/provenance. Existing evidence schema is available; no new migration is required for a plan JSON snapshot.
8. No actual browser/device responsive verification has been performed during this audit.

## Reuse and implementation scope

- Keep `utils.recommender.recommend` as the single ranking engine and keep the existing NISR validation pipeline. Add an authenticated API endpoint that invokes those same modules for React; Streamlit will continue to call the same function directly with the loader's output.
- Make evidentiary status explicit in results; do not frame the current unverified fit order or heuristic level as scientific confidence. Keep observed NISR history separate from general guidance.
- Add recommendation discovery, comparison, and saveable rationale to React's existing farm plan workflow. Persist the selected inputs and generated explanation in the existing `plan_json` through the current owner-scoped plan endpoint. Do not add evidence rows for guidance that has no traceable approved source.
- Correct stale Streamlit plan copy and ensure generated checklists are represented as provisional planning prompts. Preserve existing plan lifecycle, fields, records, and session-only guest behavior.
- Add tests for the API recommendation endpoint, engine trust semantics, and React planning integration. Keep weather contextual and retain missing-data warnings.

## Files expected to change

- `docs/crop-planning-audit.md` — this repository-grounded baseline.
- `utils/recommender.py` — replace unsupported confidence terminology with evidence availability semantics while retaining existing documented ranking/exclusion rules.
- `backend/api.py`, `backend/schemas.py` — authenticated recommendation request/response boundary and server-side use of the established loader and engine.
- `frontend/src/api.ts`, `frontend/src/pages.tsx` — retrieve/compare results and persist selected recommendation context with a plan.
- `plan.py`, `product_pages.py` — make Streamlit explain the same uncertainty, correct persistence copy, retain the existing engine and provisional plan behavior.
- Relevant existing Python and React tests; planning documentation/setup only as needed.

## Not responsibly implementable with current evidence

- Verified crop/soil suitability, recommended seed varieties/rates, exact agronomic planting dates, fertilizer or pesticide prescriptions, profitability, forecast-based planting decisions, or yield predictions.
- Sector-level suitability or farm boundary validation.
- A genuine probability of success or scientifically meaningful recommendation confidence score.
- Full Kinyarwanda translation or farmer-validated usability claims.

No database migration is planned. Saved plans continue to use the current model and farm ownership authorization. This audit is based on source inspection; tests and runtime checks are reported separately after implementation.

## Implemented in this pass

- Added authenticated `POST /v1/crop-planning/recommendations`, which calls the existing `utils.data_loader.load_data()` and `utils.recommender.recommend()` modules. It rejects extra request fields, validates district/season/optional elevation and supported water/irrigation values, and returns explicit loader state, provenance and generation time. It does not require a farm ID or return farm data.
- React's **My farms → Explore crops for this farm** now uses the selected farm district and lets the farmer choose season and optionally provide elevation/water/irrigation context. It presents the existing engine's ranked options, reasons, risks, historical context when validated, source note, limitations, missing-window state, and ranking method. Farmers can compare up to three options side by side on guide fit, indicative window, relative water need, unverified altitude range, available historical context, and known risks. A farmer must explicitly review a candidate before using it in a saved plan.
- The selected candidate's inputs, rationale, limitations, statistics state/provenance, and timestamp are saved as `plan.recommendation_snapshot` inside the existing `plan_json`. The backend remains the persistence boundary; no database migration was needed. Existing plan ownership and field checks are unchanged.
- Streamlit's Crop Decisions continues to call the same engine and now reports the evidence basis instead of a heuristic confidence grade. The detailed plan now says farmer activity records may be account-persisted or session-only depending on sign-in/service state, and planting dates remain proposed rather than scientifically recommended.
- Added tests for authenticated API behavior, strict request validation, evidence/provenance response, engine threshold language, and React recommendation-to-save flow.

The recommendation ordering uses provisional CropPulse guide categories with alphabetical tie-breaking; NISR observations are historical context only. This ordering is not an agronomic probability. Recommendations and seasonal activities remain provisional because the repository has no locally verified agronomy package connected. Weather is not used to rank or time crops. Plan creation, viewing, lifecycle updates, and editing unstarted saved plans are supported. Full Kinyarwanda UI localization remains incomplete.

Run locally from the repository root in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.api:app --host 127.0.0.1 --port 8001
```

In a second terminal:

```powershell
Set-Location frontend
npm run dev
```

To launch the existing Streamlit interface with its current API and sign-in handoff, run this from the repository root instead of manually starting another API process:

```powershell
.\run_streamlit.ps1
```

No schema change or migration command is required for this feature.

## Follow-up implementation and verification — 2026-10-22

- Added `PUT /v1/farms/{farm_id}/plans/{plan_id}` to edit saved plans only while their status is `draft` or `planned`. It enforces authenticated farm ownership, validates supported crops/district/season/area through the existing schema, and accepts only an active field belonging to that farm. Started or completed plans cannot be rewritten. No migration was added.
- React Farm Records now offers **Edit plan** for draft/planned records, pre-fills saved values, preserves the recommendation snapshot only if crop and season still match, and shows save errors without removing the entered values. Saved plans now show a progress timeline using the proposed date, farmer-recorded actual date, and saved lifecycle status; the interface does not invent crop-stage dates.
- Streamlit's private farmer dashboard now exposes editing for draft/planned saved plans through the same owner-scoped endpoint. Rebuilding a plan refreshes its provisional checklist from the existing shared `build_plan` helper. The Streamlit API client has an explicit farm/plan update call.
- Added API coverage for successful edit, invalid area, another user's access, and rejecting edits after planting. Added React save/edit coverage and a Streamlit client route/serialization test.
- Verified commands/results from the project root: `.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests\test_backend_api.py -q` (20 passed) and `.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests -q` (118 passed). From `frontend`: `npm run test` (33 passed), `npm run typecheck` (passed), `npm run lint` (passed), and `npm run build` (passed). Browser/manual device checks were not run.
- Remaining scope: no locally verified RAB/extension agronomy package is available, so the planning checklist, planting windows, and crop suitability pack remain provisional. There is no scientifically justified weather-to-planting rule, sector-level evidence, full React Kinyarwanda translation, or browser/farmer usability verification. These limitations prevent claiming the master prompt's definition of done.

## Phase 2 agronomic evidence review — 2026-10-22

- Audited the crop guide assumptions, recommendation ordering, historical NISR context, and source provenance. See [agronomic-evidence-review.md](agronomic-evidence-review.md) for source-by-source findings and remaining evidence requirements.
- Retained the rules engine but made its crop fit, calendar months, and elevation/water thresholds explicitly provisional. Unknown farm elevation or water information remains disclosed and does not exclude a crop.
- Removed NISR historical variability from recommendation ranking and agronomic risk. NISR survey measurements remain descriptive historical context only.
- Kept weather and NISR statistics separate from crop suitability. No unsupported agronomic dataset or fabricated source values were imported; no database migration was required.
- Tests for the final state are listed in the final report. Browser verification and qualified agronomist review remain outstanding.
