# CropPulse Rwanda — Farmer-Facing Evidence Transparency, Phase 15

**Audit date:** 2026-10-28  
**Scope:** crop-planning evidence and uncertainty language in React and Streamlit, plus the directly related weather and crop-health boundaries.  
**Verdict:** **DEVELOPMENT ONLY.** No agronomic rules were added or activated; this phase authorizes no pilot, staging deployment, or public release.

## Summary

The React recommendation comparison already marks guide fit and planting windows provisional, describes NISR statistics as historical context rather than a ranking input, surfaces risks and unknowns, and states what it cannot assess. Its weather page distinguishes model forecasts from observations and explicitly says no automatic agricultural alerts are generated. Its crop-health reporting page and model component call the screening experimental and not a diagnosis, and say reviewer qualifications are not verified.

The main wording gap was in the older Streamlit reference pages. The Crop Guide called internal guide content “Facts” and displayed “Typical yield,” “How well suited is each zone?”, and planting months without a nearby clear statement that the values were CropPulse-generated and unverified. The Season Calendar and District Map described crop categories as fitting a zone, and the Farm Planner presented seed/harvest estimates without making their unverified source prominent. These labels could imply locally established suitability or expected yields. They now identify the content as provisional CropPulse guide categories or unverified estimates. Calculations, ordering, filters, data, and thresholds were not changed.

## Paths audited and findings

| Interface path | Existing behavior and evidence boundary | Phase 15 outcome |
|---|---|---|
| React **My farms → Crop plans → Compare crop options**, option details, comparison, and plan review (`frontend/src/pages.tsx`) | Cards say “Provisional guide fit”; reasons are emitted by `utils/recommender.py` and identify the broad grouping and unverified guide. “Risks and unknowns” disclose missing elevation/water; soil and weather limitations appear in evidence details. No approved source-backed rule is loaded at present; the no-rule branch says the comparison is not verified. Historical district yields are labeled as calculated historical area/production, not forecasts; comparison says statistics do not affect rank or suitability. | Wording is sufficiently bounded for the current implementation; no React crop-planning copy change. Regression coverage already checks provisional labels in `frontend/src/App.test.tsx`; Python recommender tests cover unknown inputs and historical-statistics non-ranking. |
| React saved plans / evidence snapshot (`frontend/src/pages.tsx`, `utils/recommender.py`) | Saved recommendation context is described as provisional and not an independently verified evidence record. `utils/seasonal_plan.py` calls its outputs prompts and discloses unverified timing, missing plot data, no fertilizer rates, and no diagnosis. | No behavior or copy change. Existing wording remains. |
| Streamlit **Crop Decisions** (`plan.py`, `utils/recommender.py`) | Ranking method, provisional status, no-window semantics, “cannot assess” list, NISR descriptive-only use, and unknown elevation/water are disclosed. A no-window or excluded crop is not presented as proof of unsuitability. | Existing decision wording is retained. |
| Streamlit **Crop Guide** (`plan.py`, `knowledge.py`) | It displayed internally compiled fit, altitude, water, seed, duration, yield, months, and tips. `knowledge.py` identifies its guidance as general and approximate; the records have no claim-level approved source. | Replaced “Facts” framing with an explicit unverified-guide caption. Fit chart now says unverified guide categories, uses “broad CropPulse grouping,” and labels the existing 1–3 values “limited/possible/favorable (provisional).” Duration, altitude, water, planting material, planting months, and yield are explicitly labeled unverified or indicative. Yield is expressly distinguished from NISR observations and a yield forecast. |
| Streamlit **Season Calendar** (`plan.py`) | Approximate timing was stated, but source was not prominent and the filter called crops ones that “fit my zone.” | Caption says dates are unverified guide entries, not locally approved dates or a weather forecast. Filter says “possible or favorable provisional guide category”; notice says omissions do not show local impossibility. Filtering behavior is unchanged. |
| Streamlit **Farm Planner** (`plan.py`, `knowledge.py`) | Existing calculator scales internal guide seed/harvest assumptions and user-entered prices/costs. Its former intro said “nothing is invented,” which did not identify the unverified inputs. | Intro calls outputs indicative calculations from the unverified guide, not a local yield forecast. Cards identify planting material and harvest range as guide estimates; gross income is described as indicative and calculated from the user price and unverified harvest range. Downloaded plan adds an estimate-limits note. Arithmetic and user inputs are unchanged. |
| Streamlit **District Map** (`plan.py`) | Map/table called categories “High / Medium / Low” and “crop fit” by district despite the underlying broad CropPulse grouping. | Map, selector, legend, and table now call them provisional guide categories and state that they are not verified district suitability. District centers and coloring logic are unchanged. |
| Streamlit **Seasonal Crop Plan** (`product_pages.py`, `utils/seasonal_plan.py`) | The planning page calls guidance provisional and not locally verified; evidence status, missing farm measurements, estimated quantities, unverified calendar, and no-diagnosis/no-treatment warnings appear with activities. | No wording or behavior change. |
| React and Streamlit **Weather** (`frontend/src/WeatherPage.tsx`, `product_pages.py`) | Model forecasts are distinguished from observations; React says forecast-based prompts are automated and not RAB-verified, not crop-specific limits or official warnings; alert section says generation is inactive and preferences do not start monitoring. Streamlit states forecasts are not used in crop recommendations and local readings are farmer observations, not forecasts or official climate records. | No wording or behavior change. No agricultural alerts were enabled. |
| React and Streamlit **Crop Health** (`frontend/src/CropHealthPage.tsx`, `frontend/src/CropHealthAIScreening.tsx`, `product_pages.py`) | React describes maize model output as experimental candidate screening, not diagnosis, says non-maize lacks model screening, and warns reviewer credentials are not verified. Streamlit observations and seasonal plan prompts say they are not diagnosis/treatment. | No wording or behavior change. No treatment guidance was added. |

## Exact changes

- `plan.py`: made the Crop Guide, season calendar, farm-planner estimates, map categories, and generated plan limits explicitly provisional/unverified. Replaced “marginally suited; consider a better-fit crop” with a description of the existing limited provisional category and no local suitability finding.
- `tests/test_app.py`: added an AppTest regression that checks the Streamlit Crop Guide, calendar, planner, and map retain clear provisional wording.
- `README.md`: linked this audit.
- `docs/farmer-facing-evidence-transparency-phase-15.md`: recorded the audited paths, claim support, exact scope, and verification boundaries.

No change was made to React UI code because its audited recommendation wording already communicated the supported boundaries. No recommendation output, rank, exclusion, threshold, source, input, plan calculation, or farmer data behavior was changed.

## Verification

| Check | Result |
|---|---|
| `python -m py_compile plan.py` | Passed after the Streamlit copy edits. |
| `tests/windows_safe_pytest.py tests/test_app.py tests/test_seasonal_plan.py tests/test_recommender.py` | **31 passed, 1 AnyIO assert-rewrite warning.** Covers all Streamlit page rendering tests, the updated copy including its embedded Crop Guide tab, seasonal-plan boundaries, recommender unknown inputs and NISR non-ranking, and related decision output. |
| Focused React tests: `App.test.tsx`, `WeatherPage.test.tsx`, `CropHealthPage.test.tsx` | **41 passed across 3 files.** Vitest printed “Not implemented: navigation to another Document” from a test environment; suite exit status was successful. |
| `npm run typecheck` | Passed. |
| `npm run lint` | Passed. |
| Frontend build | Not run to preserve the existing `frontend/dist` output. |
| Browser E2E | Not performed. Phase 13 records the unresolved Playwright package-source blocker; these checks are component/synthetic tests, not real browser verification. |
| Agronomy registry and data preservation | `rules.json`, `review_decisions.json`, NISR CSV/manifest, source manifests, database, and migrations were not edited. No frontend build output or dependency/npm security configuration was changed. |

Git status could not be inspected because `git` is unavailable in the current shell. The report therefore makes no claim that the working tree was clean or that these are the only pre-existing changes.

## Remaining limits

The internal crop knowledge pack remains unverified; the approved-rule and review-decision registries remain empty. NISR historical aggregates do not establish crop suitability, cause of yield, or future results. District-level guide groupings are not field-level soil or climate assessments. No qualified specialist reviewed or endorsed this wording or the underlying claims. Forecasts remain forecasts, weather alert generation remains inactive, and crop-health model output remains experimental and non-diagnostic. Specialist evidence acquisition, identity/qualification verification, rights review, and scope-specific decisions remain open under the [Phase 14 evidence inventory](agronomic-evidence-inventory-phase-14.md) and [specialist review register](specialist-review-register-phase-14.md).
