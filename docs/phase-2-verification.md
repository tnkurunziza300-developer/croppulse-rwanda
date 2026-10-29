# CropPulse Rwanda Phase 2 verification

Verification date: 2026-10-16. This report records checks against the current source and the local Windows workspace. It does not certify production readiness.

## Startup configuration and live application findings

Documented clean-start settings are:

| Service | Command | Default address | Required configuration |
| --- | --- | --- | --- |
| FastAPI | `.\\.venv\\Scripts\\python.exe -m uvicorn backend.api:app --host 127.0.0.1 --port 8000` | `http://127.0.0.1:8000` | `CROP_PULSE_DATABASE_URL`, random `CROP_PULSE_SECRET_KEY` (32+ chars), explicit `CROP_PULSE_CORS_ORIGINS`, local `CROP_PULSE_COOKIE_SECURE=0`, `CROP_PULSE_ENVIRONMENT=development` |
| React/Vite | From `frontend`: `npm run dev -- --host 127.0.0.1` | `http://127.0.0.1:5173` | `VITE_API_BASE_URL` in `.env.local`, matching the API port |
| Streamlit | `.\\run_streamlit.ps1` | `http://127.0.0.1:8501` | Launcher supplies `CROP_PULSE_API_URL` and starts/reuses the current API on 8001 |

`data/croppulse_phase1.sqlite3` is the configured Phase 1 database. The React app's existing ignored `frontend/.env.local` points to port **8001**, while the tracked `.env.example` and setup guide default to **8000**. At the time of inspection, ports 5173 and 8501 served React and Streamlit, and port 8000 had a healthy API listener. That listener's OpenAPI schema did not include `/v1/browser-auth/*`, so it was an older API process. There was no listener on 8001; consequently, the active React configuration could not reach its configured backend.

Starting the current repository API on 8000 failed with Windows `WinError 10048` because that port was already occupied. The occupied process was left untouched. Starting current source on 8001 succeeded; health returned `{"status":"ok"}`, unauthenticated `/v1/me` returned 401, the CSRF endpoint returned 200 with the expected credentialed CORS origin, and both existing frontend roots returned 200. That temporary API process was stopped after verification. To run the current React configuration, start the current API on 8001; alternatively change `.env.local` to port 8000 and restart Vite after replacing/restarting the stale API listener. Keep `VITE_API_BASE_URL` and the API port aligned.

For the current ignored `.env.local` setting, start the API with this in the repository PowerShell terminal:

```powershell
$env:CROP_PULSE_DATABASE_URL = "sqlite:///./data/croppulse_phase1.sqlite3"
$env:CROP_PULSE_SECRET_KEY = (& .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))")
$env:CROP_PULSE_CORS_ORIGINS = "http://127.0.0.1:5173,http://localhost:5173"
$env:CROP_PULSE_COOKIE_SECURE = "0"
$env:CROP_PULSE_ENVIRONMENT = "development"
.\.venv\Scripts\python.exe -m uvicorn backend.api:app --host 127.0.0.1 --port 8001
```

The corrected secret-generation syntax in `react-app-setup.md` was used to start the current API. No database account or farm record was created by the live HTTP checks.

## Commands executed and results

- `.\\.venv\\Scripts\\python.exe tests\\windows_safe_pytest.py` — final run: **68 passed, 1 warning**, no skips. The expanded test run first exposed an incorrect assertion expecting 404 for an unsupported `PUT` method; FastAPI correctly returns 405, and the test now confirms the existing decision remains unchanged. The suite passed after that correction.
- `npm ci` — **failed** with Windows `EPERM` unlinking the native Rolldown module while the Vite development server was running. The generated `node_modules` folder was partially changed. `npm install` then restored it from the lockfile: 214 packages added, 58 changed, audit reported 0 vulnerabilities. `npm ls --depth=0` succeeded. For a clean install, stop Vite first and rerun `npm ci`.
- `npm run typecheck` — passed.
- `npm run lint` — passed.
- `npm test` — final run: **10 passed**. A sandboxed run initially failed at Vite startup with `spawn EPERM`; rerunning with Windows process spawning allowed passed.
- `npm run build` — passed; rerunning with Windows process spawning allowed succeeded.
- `CROP_PULSE_DATABASE_URL=sqlite:///./data/croppulse_phase1.sqlite3 .\\.venv\\Scripts\\alembic.exe current` — `0003_roles_review_and_admin (head)`.
- `.\\.venv\\Scripts\\alembic.exe check` — `No new upgrade operations detected.`
- Read-only SQLite checks — both databases returned `integrity_check=ok`. Phase 1 counts remain farmers 1, farms 1, plans 0, activities 1, sessions 3. Legacy counts remain farm_records 1 and market_quotes 0. SHA-256 values before and after this verification were unchanged: Phase 1 `8bff57dfa6eb…`, legacy `2fc77d426562…`. No migration was rerun against either database.
- HTTP checks — existing React `5173` root 200; existing Streamlit `8501` root 200; existing API `8000/health` 200 but its routes were stale; current source API temporarily on 8001 returned health 200, unauthenticated `/v1/me` 401, CSRF 200 with `Access-Control-Allow-Origin: http://127.0.0.1:5173`.
- Isolated live API restart workflow — created a unique synthetic-only SQLite file under ignored `.test-runtime/`, applied Alembic migrations to that new file, and ran current FastAPI on loopback port 8002. Browser registration returned 201 with an HttpOnly cookie and no token in JSON; `/v1/me` returned 200 before and after stopping/restarting the API; logout returned 204 and the revoked cookie then returned 401; invalid password returned 401; login after restart returned 200; expired cookie returned 401. The first ad hoc attempt used the reserved `.test` email suffix and was correctly rejected by email validation; the repeat used `example.com` and passed. Both existing databases were excluded from these writes.

## Authentication, authorization, and review findings

- Browser registration and login use a 30-minute HttpOnly `cp_session` cookie. Browser responses do not return an access token. The readable `cp_csrf` cookie and in-memory React CSRF value are only for CSRF protection, not authentication. React uses `credentials: include`; tests confirm it sends no bearer Authorization header and writes no localStorage/sessionStorage credentials. Streamlit continues to keep its bearer token in server-side Streamlit session state.
- API tests cover browser registration, invalid credentials, login, refresh via `/v1/me`, logout/session revocation, expired and malformed JWTs, missing credentials, server-side session revocation, CSRF rejection, and farmer registration without role self-assignment. Suspended accounts' sessions are revoked; prior sessions are rejected.
- Farmers cannot read, update, or delete another farmer's farm by changing IDs. Direct farmer self-approval is 403. Reviewer queue and decision access is restricted to assigned districts; out-of-scope records are hidden. A reviewer cannot modify farmer activity facts. There is no decision-update route (unsupported `PUT` returns 405), and the review-history row remains unchanged. Admin routes reject non-admin roles; elevation is not available at public registration.
- Review lifecycle tests verify pending activity, separate farmer-reported source and review status, reviewer decision history, farmer edit returning status to pending, and preservation of prior history.
- A verified frontend defect was fixed: when a protected API call returns 401 during an active session, React now clears the client session and returns to sign-in with a generic session-ended message. Registration, refresh, sign-in, logout, role navigation, and session-expiry UI checks pass.

## Browser and responsive inspection

The local React and Streamlit servers responded over HTTP. Visual/browser automation was unavailable in this workspace: no Playwright, Selenium, or geckodriver installation was found, and no browser-control tool is available. I did not claim a visual inspection. Desktop/tablet/mobile rendering, real keyboard traversal, focus visibility, actual screen-reader announcements, and browser-based registration/review/admin screens still require manual checks. Automated component tests check accessible names, role attributes, dialogs, loading and error states, but do not replace those checks.

## Warning review

- The remaining `PytestAssertRewriteWarning` says AnyIO was already imported when pytest tried to enable assertion rewriting. The Windows test runner imports Streamlit's AppTest helper before pytest starts; Streamlit imports AnyIO. The suite contains no async tests or AnyIO fixtures, so this is a test-runner warning and not an application defect. It is left visible rather than suppressing pytest warnings or disabling its plugin.
- The previous Starlette deprecation warning was actionable: Starlette 1.8 prefers `httpx2` for `TestClient`. `httpx2>=2,<3` is now declared for the test client. The application still declares `httpx` for its Streamlit API adapter. The warning disappeared on the final run.

## Prioritized release checklist

1. **Unify the live API process and URL.** Stop/restart the stale local API only after identifying its owning developer terminal; run this repository's current API on the port configured in `frontend/.env.local` (currently 8001), or align both to 8000. Confirm the browser CSRF and `/v1/me` requests in the running React app.
2. **Finish browser and clean-install verification.** Stop Vite, rerun `npm ci`, then visually exercise farmer registration/login/session expiry/logout, reviewer decisions, administrator routes, and error/loading/empty states at desktop, tablet, and mobile sizes with keyboard and screen-reader checks.
3. **Before any real-farmer pilot, complete deployment safeguards.** Provision and migrate PostgreSQL after a verified backup; configure TLS, stable secret management/rotation, trusted proxy/CORS/cookie settings, database and backup access controls, retention/deletion/consent policy, and a tested restore drill. Then get agronomic review and run a controlled farmer pilot.

The local API port mismatch and unavailable visual browser check remain open. No public deployment or destructive database operation was performed.
