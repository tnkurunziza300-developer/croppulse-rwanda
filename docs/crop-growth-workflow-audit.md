# Crop growth workflow: current audit and phased plan

**Reviewed:** 20 October 2026  
**Scope:** Existing React, FastAPI, Streamlit, and persistence workflows. This is an implementation inventory, not a claim that the platform is production-ready or that agronomic advice is validated.

## Verified project inventory

| Layer | Existing implementation | Persistence and boundary |
|---|---|---|
| React | Vite/TypeScript farmer, reviewer, and admin workspaces; account pages; farm records; crop plans; activity history | Calls FastAPI; farmer resources are owner-scoped. Browser auth uses an HttpOnly session cookie and CSRF token. |
| FastAPI | Registration, login, session control, account actions, farm and field CRUD/archive, activity CRUD, field-linked or farm-level crop plans, review, admin, and private farmer-to-reviewer messaging routes | SQLAlchemy and SQLite/Alembic. The local database is at migration 0007; messaging is disabled until an administrator enables it. |
| Streamlit | Crop decisions, provisional seasonal checklist, farm records, weather, market/economics, crop-health reports, feedback, extension and cooperative forms | Some farm records/plans use the API when configured. Many planning and reporting forms remain Streamlit-session data. |
| Existing data entities | Farmer, Farm, FarmField, CropPlan, CropPlanEvidence, FarmActivity, sessions, account tokens, reviews, audit events | Fields are farmer-owned via their farm. Crop plans may reference a field; legacy plans remain farm-level. Evidence snapshots have structured provenance fields but are not yet generated in the current manual React plan flow. |
| Agronomic and environmental evidence | Crop guidance is marked provisional; React and Streamlit use an authenticated API route backed by the same attributed Open-Meteo forecast adapter | Crop guidance is not nationally validated. Forecasts are not attached to persisted crop plans or used as advice. Weather remains a point forecast; no field soil source or boundary verification exists. |

## Current versus target workflow

| Target step | Current state | Remaining gap |
|---|---|---|
| Register, consent, authenticate | Implemented in FastAPI and React | Registration email verification and MFA are absent. |
| Farmer profile/preferences | Basic name/email/account role and required privacy-notice acceptance | No language/unit/notification preferences or richer profile workflow. |
| Farm and field setup | Farm profile and optional named fields persist; field area and paired farmer-supplied coordinates are optional; fields can be archived | Coordinates are numeric-range checked but not matched to district polygons. No sourced soil attributes or surveyed boundaries. |
| Crop selection and plan | Crop, season, intended date, area, provisional notes, status, and optional field link persist | React plan still does not invoke the Streamlit recommender or carry a generated recommendation's source/evidence version. Variety is absent. |
| Baseline and crop calendar | Streamlit can build a provisional seasonal activity checklist | Not crop-plan-linked durable baseline; no locally approved crop-specific calendar. |
| Growth monitoring | Plan lifecycle can move through planned, planted, monitoring, harvesting, completed, or cancelled | No dated crop-stage observation model; status does not prove growth was observed. |
| Weather and soil | React now provides the point forecast; Streamlit retains its separate farmer-entered session observations | No persisted environmental observation linked to a field/plan; no verified soil measurement feed. |
| Crop health | Streamlit can capture session-only farmer reports | No persisted case workflow, expert referral queue, diagnosis, or notification. Reports are not confirmed diagnoses. |
| Alerts/recommendations | No durable farmer alert system | No sourced, expiring, deduplicated, acknowledge/dismiss lifecycle. |
| Farm activities and inputs | React API stores farmer-reported activities; Streamlit includes wider session-only records | No planned-task versus completed-activity relationship, structured inputs, or correction history. |
| Harvest and outcome | React/FastAPI store owner-scoped harvest records with optional field/crop-plan links, dates, area and quantity units, optional losses/observations, validated corrections, timestamps, and converted kg/ha calculations | Records are farmer-reported and do not change crop-plan status. No complete cost/revenue ledger, causation analysis, or season outcome summary exists. |
| Season review and next season | Plans and activities can be revisited separately | No consolidated season report or copy-forward with preserved history. |
| External referral | No Hekitari connection or data-sharing integration is configured | Current UI adds an outbound referral only. A real API integration requires an agreed API, authorization, privacy review, and partner approval. |

## First workflow slice implemented

The React farmer overview now loads the farmer's saved farms and crop plans from the existing API, summarizes actual plan counts/statuses, shows intended and actual planting dates, and gives a status-aware next step. Empty states guide the farmer to create a farm or crop plan. The panel explicitly says when crop-stage observations or structured yield/cost review are not available.

The page also links to Hekitari's Smart Farm Manager as a separate external service. Its public site describes satellite vegetation monitoring, weather tools, and photo-based crop-health features, directs users to request account access, and says pricing varies by operation ([Hekitari product description](https://www.hekitari.com/apps/smart-farm-manager), [Hekitari FAQ](https://www.hekitari.com/)). CropPulse sends no farmer records through this link and does not claim a partnership, shared login, or verified performance. Users should review Hekitari's own access and privacy terms before using it.

## React migration slice: weather forecast

The existing Open-Meteo point-forecast adapter is now available to signed-in React users through **Weather & climate**. The authenticated API receives coordinates in a request body, calls the existing adapter, and does not persist the location. Farmers can use saved coordinates from their own active farm fields or enter coordinates manually. Provider attribution, retrieval time, model-forecast labeling, stale-data age, and unavailable states remain visible. The Streamlit page remains available during migration; its local-observation form still uses temporary session data and has not moved to React.

## Harvest outcome slice

The React farm workspace and owner-scoped FastAPI API now provide dedicated harvest records rather than relying on free-form activity entries. Records require a farmer-entered harvest date, positive harvested area, and positive quantity with explicit supported units; optional losses, notes, and post-harvest observations remain optional. A linked plan must belong to the same farm and match the recorded crop and season. Field links are checked against the farm. Updates are validated and retain creation/update timestamps.

Yield is calculated only after converting recorded area and quantity to hectares and kilograms, then shown as kg/ha with the conversion formula. This is a calculation of the farmer-entered record only; it is not NISR data, a farm-yield forecast, or evidence that a plan caused the result. Creating or correcting a harvest does not advance the crop-plan lifecycle. The additive Alembic migration is `0016_farm_harvests`.

The next migration should be selected after this slice is reviewed. Existing Streamlit crop decisions and planning estimates depend on provisional evidence and session state; they should not be copied into React as authoritative advice or durable records without a separate provenance and persistence design.

## Prioritized implementation backlog

1. **Stabilize and join the existing records (current slice):** keep account/farm/plan ownership intact; show persisted plans and honest next steps in one farmer overview. Continue integration/security regression coverage.
2. **Plan evidence integration:** connect a server-side recommendation flow to the new provenance snapshot schema, preserve source/version/verification metadata, and capture variety only where known. Do not promote provisional knowledge to approved advice.
3. **Observed growth stages:** introduce dated, farmer-reported stage observations with optional notes and provenance; distinguish these from estimates and plan status.
4. **Environmental provenance:** link coordinates/forecasts and farmer or verified soil/weather measurements to the relevant field/season, with source, units, timestamps, and stale/unavailable states. Retain Open-Meteo licensing and privacy controls.
5. **Crop-health cases and alerts:** persist farmer symptom reports and a review/escalation lifecycle. Add only source-backed, deduplicated alerts with clear uncertainty; no automated diagnosis or unsafe treatment advice without local validation.
6. **Activities, harvest, and economics:** separate planned tasks from completed events; create harvest records with explicit units and multiple harvest support; calculate yield only when area and quantity are compatible; label farmer-reported and estimated costs/revenue.
7. **Season review and next-season planning:** summarize persisted plans, observations, activities, harvests, and known gaps; allow copy-forward while preserving prior season history.
8. **Channel and partner integration:** assess Kinyarwanda/low-bandwidth needs and any Hekitari/extension integrations only with user consent, documented data sharing, technical API terms, and partner authorization.
9. **Integrated validation:** security/ownership, migration/persistence, UI/device/accessibility, language, and qualified Rwanda agronomy review. Automated tests alone do not establish production readiness.

## Design boundaries

- Use existing entities and endpoints until an actual workflow gap justifies a migration.
- Never treat a plan status as a field observation or a farmer report as verified evidence.
- Do not infer farm-level conditions from a regional forecast, fabricate soil/weather data, or let current forecasts silently alter crop advice.
- Keep external referrals explicit; do not transfer personal or farm data to a third party without a separately designed consent and integration flow.
- Test each coherent phase and document actual results before expanding the claims made by the interface.
