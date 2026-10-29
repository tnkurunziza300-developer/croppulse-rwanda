# Phase 3 browser verification

Date: 2026-10-22  
Browser: Google Chrome 155.0.8059.85 (headless, local development services)  
Application: React at `http://127.0.0.1:5173`; FastAPI at `http://127.0.0.1:8001`

## What was verified

- The React app returned HTTP 200 and rendered its sign-in screen after initialization.
- FastAPI `/health` returned `{"status":"ok"}`. The live OpenAPI schema exposed the crop-planning recommendation and saved-plan routes.
- `frontend/.env.local` points the frontend at `http://127.0.0.1:8001`. A browser-origin CSRF request returned HTTP 200 with `Access-Control-Allow-Origin: http://127.0.0.1:5173`.
- An unauthenticated `/v1/me` request returned HTTP 401, as expected. Farm data also requires an authenticated farmer session.
- Chrome reported no JavaScript console errors or uncaught exceptions on the sign-in page.
- The sign-in screen was captured at 1440x1000, 768x1024, and 390x844. At all three sizes, the document width matched the viewport. The 390px capture exposed form and account-link overflow before the CSS fix; the corrected layout keeps those controls within the viewport and wraps the account links.
- The browser initially requested a missing favicon and received HTTP 404. The React document now references the added CropPulse leaf favicon; `http://127.0.0.1:5173/favicon.svg` serves the asset.
- During repeated CDP navigation, one in-flight CSRF request was canceled (`ERR_ABORTED`); a completed browser-origin CSRF request returned HTTP 200. This occurred during the repeated QA navigations, not as a persistent API outage.

Screenshots:

- [Desktop sign-in, 1440x1000](phase3-desktop-signin.png)
- [Tablet sign-in, 768x1024](phase3-tablet-signin.png)
- [Mobile sign-in, 390x844](phase3-mobile-signin.png)

## Not verified in this browser run

No authorized test account credentials were available in the request, so I did not sign in, modify farm records, create plans, or alter the local database. As a result, farm selection, recommendation generation, comparisons, saved-plan reload, editing, status restrictions, timeline behavior, and planner accessibility remain unverified in an authenticated browser. The screenshots are of the sign-in screen only; they are not evidence of the farmer planning workflow.

## Windows manual completion steps

1. In the repository root, follow [React app setup](../react-app-setup.md) to use an isolated or approved test database, configure the local API environment, apply any needed migrations only after backing up the test database, and start FastAPI on port 8001.
2. In a second PowerShell window, run `Set-Location frontend`, ensure `.env.local` has `VITE_API_BASE_URL=http://127.0.0.1:8001`, then run `npm run dev -- --host 127.0.0.1`. Open `http://127.0.0.1:5173` in Chrome.
3. Sign in with an existing authorized test farmer account. Open **My farms**, select an owned farm, and check its district and missing optional information.
4. Generate the crop comparison. Confirm the provisional fit, unverified planting months, unknown elevation/water disclosures, and NISR historical-context labels. Compare up to three crops and check that no missing measurements appear as invented values.
5. Select a recommendation, save a plan, reload the page, and confirm the plan is attached to the selected farm. Edit the planned draft, save, reload, and confirm the revised fields persist.
6. Progress a disposable test plan using a farmer-recorded actual planting date. Confirm the timeline shows only the proposed date, entered actual date, and saved status. Try editing after the plan has progressed; confirm the API rejects it. Also verify another account cannot read or edit the plan.
7. Use Chrome responsive mode at 1440px, 768px, and 390px for the authenticated workflow. Tab through form labels and actions and check loading, error, and empty states. Record screenshots after sign-in without including personal data.

Do not use a production account or production database for these steps. No deployment or production-readiness claim follows from this local verification.

## Automated checks

From the repository root, `.\.venv\Scripts\python.exe tests\windows_safe_pytest.py` completed with **120 passed** and one pytest plugin rewrite warning. From `frontend/`, `npm run test` completed with **33 passed**, `npm run typecheck` passed, `npm run lint` passed, and `npm run build` passed. The build transformed 2,515 modules. These checks do not substitute for the authenticated browser steps above.
