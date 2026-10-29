# Private staging preparation — Phase 25

**Status:** deployment package prepared; no staging host, database, gateway, or secret store has been provisioned or tested. CropPulse remains development-only.

## Verified repository baseline

- Source Alembic head: `0020_agronomy_review_workflow`.
- `0020` is additive and has a disposable SQLite upgrade/downgrade regression test. Never use the downgrade procedure on a shared or real target.
- Production/staging startup requires explicit environment, strong signing secret, HTTPS CORS origins, secure cookies, and disabled automatic schema creation. Migrations are a separate release operation.
- `/health` makes a database readiness query and returns only a generic health response. It does not report migration readiness or uptime history.
- React builds to `frontend/dist`; `/v1/*` must reach FastAPI without static caching. Streamlit remains a separate service and needs WebSocket proxying; use one private HTTPS host with route separation so the host-only session cookie is shared only by trusted CropPulse services.
- The React frontend requires the public `VITE_API_BASE_URL`. A production build now rejects sensitive `VITE_*` environment names.
- The current local `.env`/`.env.local` files are ignored working-copy configuration. Do not copy them to staging. The prior login UI read and rendered a demo password from a `VITE_*` variable; Phase 25 removes that behavior. If any such demo credential was used publicly, rotate it at its account authority.
- General API rate/concurrency limits, TLS termination, proxy header trust, monitoring, and backups are not provided by the application. They must be configured at the private gateway/hosting layer.

## Deployment topology to implement in a private environment

```text
Browser --HTTPS--> private reverse proxy
                     / and static assets -> React dist (SPA fallback)
                     /v1/* and /health   -> FastAPI (no-store for API)
                     /streamlit/*        -> Streamlit (WebSocket upgrade)
                         FastAPI and Streamlit -> same private API/database
```

Use a single private hostname and TLS certificate. Do not expose database or Streamlit ports publicly. Add gateway request-size limits no larger than the application's 8 MiB cap, route-specific rate limits, connection/concurrency ceilings, timeouts, and WebSocket limits. Set security headers at the proxy where appropriate. Do not enable proxy trust headers until the trusted proxy chain is explicitly configured. Cache only fingerprinted static assets; never cache authenticated `/v1/*` responses.

No hosting vendor or paid service is selected by this runbook.

## Configuration and secret injection

1. Provision private staging infrastructure and an isolated PostgreSQL database through the organization's approved provider. Do not use a developer's SQLite file for shared multi-user staging.
2. Copy [`deploy/staging.env.example`](../deploy/staging.env.example) into the approved staging secret/configuration system. Replace placeholders there; do not commit the filled file. Configure the exact HTTPS React origin, database URL, and public app/API origin. Give the database account only the access needed by the application and reviewed migrations.
3. Generate a unique signing secret in a trusted terminal with `python -c "import secrets; print(secrets.token_urlsafe(48))"`, then place it directly in the secret store. Do not paste it into tickets, chat, command history, the frontend environment, or this repository. Inject secrets into each API and Streamlit process at startup. Use a separate secret per environment and a planned rotation/session-invalidation procedure.
4. Create a protected build environment directory outside the repository containing only a `.env.production` file copied from [`deploy/frontend.env.production.example`](../deploy/frontend.env.production.example). It may contain only `VITE_API_BASE_URL`; do not place any credentials there. Point Vite at that directory with `CROP_PULSE_FRONTEND_ENV_DIR`. This avoids loading ignored local developer `.env.local` values during release builds.
5. Set `CROP_PULSE_ENVIRONMENT=staging`, `CROP_PULSE_COOKIE_SECURE=1`, and `CROP_PULSE_AUTO_CREATE_SCHEMA=0` for both services. Set `CROP_PULSE_CORS_ORIGINS` to the exact HTTPS browser origin. Inject `CROP_PULSE_SECRET_KEY` and `CROP_PULSE_DATABASE_URL` from the secret store. Keep SMTP credentials absent unless account recovery delivery has been deliberately configured and tested.

## Build and migration release procedure

Run from the repository root in an approved deployment shell. These commands are a template; use the private staging environment's own secret injection and target. Do not run against a developer or production database.

```powershell
# Install only from the reviewed lock/requirements files in the isolated release environment.
python -m pip install -r requirements.txt
Push-Location frontend
npm ci
$env:CROP_PULSE_FRONTEND_ENV_DIR = '<private-build-config-directory>'
npm run build
Pop-Location

# Verify the configured target is exactly at the reviewed pre-migration revision.
# For a database being upgraded to 0020 from Phase 24, that prior revision is 0019.
python scripts/staging_preflight.py --expected-prior-revision 0019_soil_records

# Only after a protected verified backup and a passing preflight:
python -m alembic upgrade head
python -m alembic current
Invoke-RestMethod -Method Get -Uri 'https://<private-staging-host>/health'
```

If the planned release expects a different prior revision, stop and update the reviewed change plan rather than guessing. `scripts/staging_preflight.py` validates the staging runtime configuration and performs a read-only target inspection; it never applies migrations. For SQLite, it refuses to create a missing target. Its PostgreSQL diagnostic runs in a read-only transaction. Do not paste diagnostic output containing a local path into public logs.

### Backup and restore gate

- PostgreSQL staging: use the provider's protected backup facility or `pg_dump --format=custom` through its approved service profile/credential file. Write a unique, access-restricted artifact; verify the dump with `pg_restore --list`; record a checksum in the protected change record. Never put the full database URL or password on a command line.
- SQLite-only isolated development: follow the online-backup API procedure in [Phase 3A security, privacy, and recovery notes](security-privacy-recovery-phase-3a.md), use a unique new destination, then check `PRAGMA integrity_check`, Alembic revision, expected schema, and SHA-256. Do not use file copy alone when WAL may be active.
- Restore drills always target a separately named isolated database. Verify integrity, current revision, foreign keys, representative synthetic records, and application read-only health. Never test restore by overwriting the source. Agree recovery objectives and retention before onboarding real farmers.

## Start, smoke test, monitor, and stop

Start FastAPI and Streamlit as separate managed processes using the approved service manager, explicit working directory, injected environment, and pinned release. Serve the completed React `dist` directory through the proxy. Do not use Vite's development server or `--reload` in staging. Add restart policy and readiness-based routing; do not start traffic until `/health` succeeds and the migration revision is verified.

Use synthetic accounts only. Check sign-in/sign-out, CSRF rejection, farmer A/B ownership boundaries, farm/field/crop-plan lifecycle, harvest/post-harvest/irrigation/soil records, weather consent/coordinate labeling, crop-health submission wording, reviewer district access and decision history, admin reviewer grants, and agronomic proposal approval remaining inactive as guidance. Check stale/failed provider states, 390 px layout, keyboard focus, and session expiry. Confirm logs exclude credentials, request bodies, farmer notes, tokens, and private messages. Monitor readiness failures, latency, 4xx/5xx rates, throttling, database pool saturation, disk/storage, backup outcomes, and provider quotas; alert without including personal data.

Apply organization-approved cleanup schedules for sessions, one-time tokens, auth-attempt buckets, messages, crop-health photos, farm histories, and audit events only after retention and deletion policy is approved. Current code does not provide a complete scheduled retention service.

To stop staging, remove traffic at the private gateway, stop managed Streamlit/API processes through that service manager, preserve logs/backups under their approved retention policy, and revoke/rotate credentials according to the change plan. Do not kill unknown local processes.

## Rollback

If smoke checks fail, keep the environment private, stop routing new traffic, and restore the prior frontend/API release together. Do not downgrade schema in place unless an explicit migration review proves downgrade safety and the operation is exercised on a disposable clone. Prefer a forward corrective migration. If data integrity is in question, restore a verified backup to a new isolated database and validate it before any cutover. Record the incident and preserve the failed staging database read-only for investigation.

## Readiness boundaries

- **Verified locally:** source configuration guards; disposable migration upgrade/downgrade tests; read-only migration preflight tests; API/frontend automated suites; production frontend build with a clean private env directory; agronomy validator.
- **Must verify in private staging before a pilot:** target database identity/revision, TLS/proxy/CORS/cookie behavior, gateway limits, managed secret injection/rotation, SMTP if enabled, backup/restore, logs/monitoring, synthetic authenticated browser flows, accessibility/mobile, and service restart/rollback.
- **Must resolve before a real-farmer pilot:** privacy/retention/legal approval, provider licensing, qualified local agronomic evidence and approvals, crop-health model licensing and field validation, support/incident process, recovery objectives, and consented user testing.
- **Must resolve before public production:** all pilot blockers plus independent security review, load/abuse testing, data residency and organizational ownership, sustained recovery monitoring, approved provider terms, and evidence-backed agronomic scope. The registry currently has zero approved rules.

## Exact next safe step

An operator should first choose and provision a private staging host, gateway, and isolated database through the organization's approved process. No host or database is currently configured, so do not run the migration command above yet. After secrets are injected, identify the target's expected prior revision, create and verify a protected backup, then run the read-only preflight against that exact revision before a reviewed migration window.
