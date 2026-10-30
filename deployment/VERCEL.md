# Vercel multi-service deployment draft

The repository-root `vercel.json` describes three services: a Vite frontend,
FastAPI API, and a Streamlit planning container. Public rewrites send `/health`
and `/v1/*` to FastAPI, `/planner` and `/planner/*` to Streamlit, and other
paths to React. The planner service binds to the API at runtime through
`CROP_PULSE_API_URL`; do not set that binding variable manually.

## Vercel project settings

Select the Services project framework and confirm that this feature is enabled
for the Vercel account. Configure these values in Vercel's server-side runtime
environment settings, never in the repository:

- API service: `CROP_PULSE_ENVIRONMENT=production`,
  `CROP_PULSE_DATABASE_URL`, `CROP_PULSE_SECRET_KEY`,
  `CROP_PULSE_CORS_ORIGINS`, `CROP_PULSE_COOKIE_SECURE=1`,
  `CROP_PULSE_REACT_URL`, and `CROP_PULSE_STREAMLIT_URL`.
- Frontend build environment: `VITE_API_BASE_URL=same-origin`.
- Planner runtime: `CROP_PULSE_ENVIRONMENT=production` is set in its image;
  `CROP_PULSE_API_URL` is injected by the service binding.

Set `CROP_PULSE_REACT_URL` to the approved HTTPS project origin and
`CROP_PULSE_STREAMLIT_URL` to that same origin plus `/planner`. The API uses
these configured public URLs to create the one-time browser handoff. They are
not service bindings because the API constructs redirects and does not make
server-to-server requests to those services.

The API's existing production runtime checks still apply. Configure its
database, secret, trusted proxy behavior, and CORS origins before deployment;
do not run migrations as part of a build. Apply migrations only to a reviewed,
disposable database first, using a separate controlled release step.

## Release blockers and limitations

- `data/verified/nisr_sas_2023_2026.csv` is excluded from Git by the existing
  `.gitignore`. A fresh Vercel checkout therefore will not contain this file,
  even though it exists in some local workspaces. Decide whether its source
  terms permit packaging it, then add it through the approved data-release
  process and verify it against `data/verified/MANIFEST.json`. Do not silently
  remove the file or fabricate a replacement.
- Confirm the bundled crop-health model's redistribution and derivative-work
  terms before distributing the API/container image.
- Streamlit requires its public `/planner` path for assets and WebSocket
  traffic. Vercel's Container runtime and Services must be available for this
  project, and long-running WebSocket sessions need deployment verification.
  Container local storage is ephemeral; durable records belong in the
  configured external database.
- The current dashboard routes Streamlit server-side calls through the private
  service binding. Calls made by the browser use the public same-origin
  `/v1/*` rewrite; browser code cannot access runtime bindings.

This is deployment configuration, not evidence of a successful Vercel build,
database connection, browser handoff, or hosted readiness.
