# Frontend readiness

## Implemented workflows

- Crop Decisions ranks candidates with visible reasons, limits, evidence strength, and links to a detailed plan or recommendation feedback.
- Seasonal Crop Plan builds a district/crop/season/planting-date activity sequence and approximate harvest window from provisional guidance. Its tracking action opens Farm Records with the plan's crop, district, and season selected.
- Farm Records supports farmer-reported planting, activities, crop health, harvest, cost, and feedback entries, edit/delete, CSV export, and same-unit harvest summaries. Farm activities use the configured API; other entries remain temporary and are cleared at account boundaries.
- Market & Economics captures dated, sourced user observations, filters and charts matching quotes, and calculates clearly labeled assumption-based scenarios.
- Weather & Climate accepts user-entered coordinates for an Open-Meteo seven-day model forecast and keeps sourced, user-entered rainfall/temperature readings separate. District/sector-to-coordinate verification is unavailable; forecast is not used in crop advice.
- Pest & Crop Health, Extension Visits, Cooperative Activities, Recommendation Feedback, and Agronomy Review Queue provide session-only forms, validation, exports, and explicit non-verification states.
- Analytics pages expose dataset filters, year selection, visual summaries, quality warnings, and export workflows. Demonstration statistics are labeled and do not change recommendation ranking.
- English and Kinyarwanda are available for navigation and primary farmer inputs, statuses, and actions. Detailed analytics and agronomy explanations remain primarily English.
- Responsive CSS includes mobile column wrapping, touch-size buttons, focus indicators, and reduced-motion handling.

## Data and trust boundaries

Most submitted entries remain in the active Streamlit session. Signed-in Farm Records and saved crop plans persist in the Phase 1 API and are owner-scoped. Users can export session and farm activity entries; session clearing never deletes account records. Do not use this prototype to collect sensitive or confidential farm data.

Crop guidance and calendars remain provisional until qualified local review. Weather is a point model forecast, not station data, and requires deployment licensing, request controls, and privacy review. Verified market feeds are not connected. Pest reports do not diagnose a condition or notify an officer. Review submissions do not approve guidance. Cooperative entries are aggregate planning notes, not shared organizational records.

## Backend Phase 1

The Streamlit frontend remains available, and a React + strict TypeScript + Vite client now runs alongside it. Both connect to the same FastAPI service. React provides role-specific farmer, reviewer, and administrator routes; cookie sessions; farmer farm/activity workflows; assigned-district review decisions; audited account access management; aggregate dashboard/report views; and current API/database connectivity states. Setup, migrations, owner boundaries, route roles, and remaining session-only collections are in [backend-phase-1.md](backend-phase-1.md) and [React app setup](react-app-setup.md). Weather and market provider integrations remain deferred.

The React client currently covers farmer farms and activities, not all of Streamlit's planning/analytics workflows. It is English-only. Reviewer decisions apply to saved farm activities; the separate Streamlit agronomy guidance queue remains session-only and is not the same review system. Backup status, historical error rates, account recovery/deletion, audit history of ordinary reads, and notifications are not implemented.

The React farmer overview summarizes persisted crop plans by farm, status, and planting dates. React also includes private crop-health report creation, farmer case history and district-scoped reviewer follow-up. Maize crop-health reports show experimental model-ranked candidates, not AI diagnoses or treatment recommendations. Growth-stage observations, alerts, structured harvest and season-outcome review remain unavailable; see the [crop-growth workflow audit](crop-growth-workflow-audit.md) and [crop-health workflow](crop-health-review.md).

## Review boundary

The source was checked for Python syntax, application routes were rendered with Streamlit AppTest, and key session workflows were exercised. Automated route and workflow checks do not replace a visual review on actual low-end Android devices, screen-reader/keyboard review by intended users, or agronomic review by qualified Rwanda specialists. Those real-world reviews should happen before calling the product production-ready or publishing agronomic guidance as approved.
