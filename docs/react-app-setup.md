# React + FastAPI workspace setup (Windows)

This guide runs the new React/TypeScript frontend beside the existing Streamlit app. Both use the same Phase 1 FastAPI service and SQLite database. Neither React nor Streamlit opens SQLite directly.

## What is implemented

- `frontend/` is a React, strict TypeScript, Vite single-page app with responsive role-specific workspaces.
- Browser authentication uses an HttpOnly, host-only session cookie with `Path=/`, a 30-minute expiry, and server-side revocation. A React page refresh rechecks that cookie at `/v1/me`; Streamlit can revalidate the same cookie after a browser reload, without saving the token in browser storage. State-changing cookie requests carry a signed double-submit CSRF token. Streamlit uses the revalidated token server-side for its existing bearer-token API contract.
- Farmer pages read/create owned farms and farmer-reported activities. Reviewer pages list stored farm activities in assigned districts and append immutable decisions. Admin pages show current aggregate metrics, manage account status/roles/reviewer districts, revoke sessions, inspect audit events, and export aggregate counts.
- Role checks and record ownership are enforced by FastAPI. Registration always creates an active farmer. It rejects extra role fields. The first administrator is provisioned by an interactive local operator command; authenticated admins can grant reviewer or admin access afterward.
- Account settings support confirmed email changes, password reset through expiring single-use email links, and self-service account deletion with password reauthentication and typed confirmation. Email-based actions require an operator-configured SMTP relay; no provider is included or assumed.
- React is the only password sign-in and account-registration interface. Streamlit directs unauthenticated visitors to React and resumes the Streamlit workspace after successful login. The Streamlit profile shows the authenticated account and role; farmer farm management remains available only to farmer accounts. Account farm/plan/activity data remains owner-scoped by FastAPI; temporary Streamlit entries are cleared at sign-out so they do not carry across accounts.
- React opens Streamlit with a five-minute, single-use server-issued handoff. Streamlit's **Return to CropPulse React** link uses a separate five-minute, single-use code to establish the React HttpOnly cookie session. Neither direction puts a password or bearer token in a URL. Both handoffs resolve the account and current role on the API, so an administrator or reviewer remains that role in both interfaces. Streamlit displays an administrator/reviewer workspace label instead of presenting those accounts as farmers; React remains the interface for account and system administration. If a return code was already used, use **Refresh React sign-in link** in Streamlit before returning again. On reload, Streamlit can revalidate the React session cookie with the API. React, API, and Streamlit must use the same hostname for cookie-based restoration; different ports are supported. Both applications continue using the same account service. Hekitari remains a separate external service.
- The admin dashboard reports only current database counts. It does not invent trends, backup health, historical error rates, email verification, or production health guarantees. “Approved as reviewed” is not an independent agricultural verification.

## One-time Windows setup

Open PowerShell in the repository root. The backend environment is isolated in `.venv`; the frontend dependency versions are pinned in `frontend/package-lock.json`.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
New-Item -ItemType Directory -Force data | Out-Null
```

Before upgrading an existing database, stop API writers and create a separate backup. The implementation audit backup is at `.backups/pre-react-migration-20261016/`; its integrity check and baseline row counts are documented in `react-migration-audit.md`. For a new pre-upgrade backup, use a dated destination and verify it can be opened before continuing:

```powershell
New-Item -ItemType Directory -Force .backups | Out-Null
Copy-Item -LiteralPath data\croppulse_phase1.sqlite3 -Destination .backups\croppulse_phase1-before-react.sqlite3
.\.venv\Scripts\python.exe -c "import sqlite3; c=sqlite3.connect('file:.backups/croppulse_phase1-before-react.sqlite3?mode=ro', uri=True); print(c.execute('PRAGMA integrity_check').fetchone()[0]); c.close()"
```

Configure the API terminal. Use the same database URL when running migrations, the API, and the administrator provisioning command:

```powershell
$env:CROP_PULSE_DATABASE_URL = "sqlite:///./data/croppulse_phase1.sqlite3"
$env:CROP_PULSE_SECRET_KEY = (& .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))")
$env:CROP_PULSE_CORS_ORIGINS = "http://127.0.0.1:5173,http://localhost:5173"
$env:CROP_PULSE_COOKIE_SECURE = "0"
$env:CROP_PULSE_ENVIRONMENT = "development"
$env:CROP_PULSE_STREAMLIT_URL = "http://127.0.0.1:8501"
$env:CROP_PULSE_SMTP_HOST = "smtp.example.org"
$env:CROP_PULSE_SMTP_PORT = "587"
$env:CROP_PULSE_SMTP_USERNAME = "<smtp-user>"
$env:CROP_PULSE_SMTP_PASSWORD = "<smtp-password>"
$env:CROP_PULSE_SMTP_FROM = "CropPulse <no-reply@example.org>"
$env:CROP_PULSE_SMTP_STARTTLS = "1"
$env:CROP_PULSE_SMTP_USE_SSL = "0"
$env:CROP_PULSE_PUBLIC_APP_URL = "http://127.0.0.1:5173"
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\alembic.exe current
```

The API validates the key during startup and refuses to run if it is missing, shorter than 32 bytes, a placeholder, or obviously weak. Do not reuse the example placeholder from `.env.example`. Keep the generated value in the API terminal/environment only; never set it as a `VITE_*` variable. Changing this key invalidates active login sessions.

Migration `0008_streamlit_handoff` adds an isolated table for hashed, expiring, single-use sign-in codes. It does not alter existing account or farm records. Apply it with the other pending migrations only after stopping API writers and making/verifying a backup. Apply them only to `data/croppulse_phase1.sqlite3`, not the separate legacy `data/croppulse_local.sqlite3` schema. The local development backup before migration 0007 is `.backups/croppulse_phase1_pre_0007_20261020.sqlite3`; keep it protected because it contains personal and farm records. See [field and evidence workflow](field-evidence-phase.md).

Start FastAPI in this terminal:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.api:app --host 127.0.0.1 --port 8001
```

Verify it from another PowerShell terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/health
Invoke-WebRequest http://127.0.0.1:8001/v1/browser-auth/csrf -Headers @{ Origin = "http://127.0.0.1:5173" } | Select-Object StatusCode
```

Both checks should succeed; the CSRF response should be HTTP 200 and include `Access-Control-Allow-Origin: http://127.0.0.1:5173`. `/health` checks database readiness. Startup checks that authentication signing is configured. The local launcher also checks CSRF and CORS before reusing an already-running API.

## Run React

In a second terminal from the repository root:

```powershell
Set-Location frontend
npm ci
Copy-Item .env.example .env.local
npm run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:5173`. The `.env.local` file contains only the public API base URL. It must use the same port as the FastAPI process: the example defaults to `http://127.0.0.1:8001`. If you run FastAPI on port 8001, set `VITE_API_BASE_URL=http://127.0.0.1:8001` and restart Vite. Never put a database URL, signing key, or password in a `VITE_*` variable.

Create an account from the React sign-in screen. To provision the first platform administrator, stop neither the database nor API, open another PowerShell terminal from the repository root, set the same `CROP_PULSE_DATABASE_URL`, and run:

```powershell
$env:CROP_PULSE_DATABASE_URL = "sqlite:///./data/croppulse_phase1.sqlite3"
.\.venv\Scripts\python.exe -m backend.admin_cli promote-first-admin your-account@example.com
```

The command asks you to type the exact email, requires an existing active account, refuses to run after an administrator already exists, and writes an audit event. Sign out and sign back in to refresh the UI role state. Do not run this against a database you do not administer.

## Run Streamlit locally

After applying database migrations, run `run_streamlit.ps1` from the repository root. It starts or reuses the current API on port 8001, configures the handoff destination as `http://127.0.0.1:8501`, sets `CROP_PULSE_API_URL` only for the Streamlit process, and stops the API it started when Streamlit exits. Before reusing an API process, it checks that both sign-in handoff directions are present. In local development, the Streamlit sidebar return link defaults to `http://127.0.0.1:5173/overview`. Port 8501 must be free because the React handoff URL is configured to that address.

```powershell
.\run_streamlit.ps1
```

Streamlit no longer accepts a separate password or account registration. Unauthenticated visitors use **Sign in to CropPulse**, which opens React; after a successful React login, the one-time handoff returns them to Streamlit. Handoff codes expire after five minutes and are consumed once. For a manual deployment, configure `CROP_PULSE_STREAMLIT_URL` on the API process to the public Streamlit URL and `CROP_PULSE_REACT_URL` to the public React base URL. Production requires HTTPS; credentials, query strings, and fragments are rejected.

A single DNS hostname can serve all three components when a TLS reverse proxy routes requests by path. For example, React can be at `https://crop.example.org/`, Streamlit at `https://crop.example.org/planning/`, and the API routes at `https://crop.example.org/v1/` plus `/health` and `/openapi.json`. Configure Streamlit with the matching `server.baseUrlPath` (such as `planning`), `CROP_PULSE_STREAMLIT_URL=https://crop.example.org/planning`, `CROP_PULSE_REACT_URL=https://crop.example.org`, and both Streamlit `CROP_PULSE_API_URL` and React `VITE_API_BASE_URL` to `https://crop.example.org` (the API client appends `/v1/...`). The proxy must route each API path to FastAPI, route `/planning/` to Streamlit, send other app paths to React, preserve WebSocket upgrades for Streamlit, and pass the correct forwarded scheme/host. Keep the public API paths as `/v1/...`; exposing them under an extra prefix such as `/api/v1` requires matching cookie-path rewriting because the CSRF cookie currently uses `Path=/v1`. Configure FastAPI CORS for the React origin `https://crop.example.org`; paths are not included in CORS origins. Because the session cookie is host-only with `Path=/`, using one hostname allows the browser to send it to both apps. Different DNS names require a separate cookie and SSO design; ports may differ but are not needed for a path-based deployment.

One DNS record alone does not combine the apps: DNS sends traffic to the proxy, while the proxy and each app still need correct path, TLS, API URL, cookie, and WebSocket configuration. Test the complete login, refresh, React-to-Streamlit, Streamlit-to-React, role, and sign-out flows behind the actual proxy before deployment. Keep host names consistent (`localhost` versus `127.0.0.1`) locally so browsers send the SameSite cookie. React sessions have a fixed 30-minute lifetime and are not extended by refreshing or visiting Streamlit; after expiry the user signs in again. Planning and analytics remain in Streamlit while migration to React continues.

### If the workspace button says the API is out of date

The React and Streamlit frontends must point to the current API process. Confirm that `/openapi.json` includes `/v1/browser-auth/streamlit-handoff`, `/v1/streamlit/handoff/exchange`, `/v1/streamlit/react-handoff`, and `/v1/browser-auth/react-handoff/exchange`. If any are absent, close the CropPulse Streamlit launcher with Ctrl+C and relaunch it from the current project directory using `.\run_streamlit.ps1`; it now rejects API processes that lack either handoff direction. If you start the API separately, stop that old process and start `backend.api:app` from this project with the same database and secret configuration. Do not run a migration for this route update; it reuses the existing `streamlit_handoffs` table from migration `0008_streamlit_handoff`. The frontend cannot repair an already-running API process itself.

## Verification commands

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe tests\windows_safe_pytest.py
Set-Location frontend
npm run typecheck
npm test
npm run build
```

The Python runner uses unique project-local temporary directories for this managed Windows environment. Close the Vite development server before running `npm ci`; Windows can refuse to replace the native Rolldown module while the server has it loaded. If sandboxed Vite/Vitest reports `spawn EPERM`, run the command from a normal developer terminal.

## Backup and recovery

Stop the API before copying the SQLite file. Keep backups outside the served web root, restrict access to them, and verify each copy with `PRAGMA integrity_check`. The `.backups/` directory is gitignored but remains on this machine; it is not an off-site or encrypted backup.

To restore a verified pre-migration copy after stopping all API processes, preserve the failed current database first, then restore the verified backup and confirm its integrity and Alembic revision:

```powershell
Copy-Item -LiteralPath data\croppulse_phase1.sqlite3 -Destination .backups\croppulse_phase1-before-restore.sqlite3
Copy-Item -LiteralPath .backups\croppulse_phase1-before-react.sqlite3 -Destination data\croppulse_phase1.sqlite3 -Force
.\.venv\Scripts\python.exe -c "import sqlite3; c=sqlite3.connect('file:data/croppulse_phase1.sqlite3?mode=ro', uri=True); print('integrity:', c.execute('PRAGMA integrity_check').fetchone()[0]); print('revision:', c.execute('SELECT version_num FROM alembic_version').fetchone()); c.close()"
```

Restoring the earlier revision also removes records written after that backup; coordinate recovery with the data owner. For a controlled pilot, add scheduled protected backups, retention, off-site storage, and a tested restore drill before collecting real farmer data.

## Remaining limits

The UI is English-only; the Streamlit experience retains English/Kinyarwanda options. Registration email verification, MFA, alerting, persistent field correction workflow, review request-to-farmer notification, audit read-history instrumentation, map coordinates, and historical snapshots remain absent. Email change and password reset do not function until SMTP and the public frontend URL are configured on the API. PostgreSQL, deployment TLS/proxy behavior, mobile devices, screen readers, and real-user workflows have not been verified. Do not treat this phase as production ready.
