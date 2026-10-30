# Demo environment isolation

The login page always shows a **Demo Account** section. In ordinary farmer builds it explains that demo access is disabled and shows no credentials or demo action. In an explicitly enabled demo build, it shows credentials only after the demo service verifies synthetic-only isolation. Authentication in demo mode routes only to the configured demo API. Demo mode is opt-in at build time and requires both `VITE_API_BASE_URL` and `VITE_DEMO_API_BASE_URL`; the origins must be distinct. In production both must be public HTTPS origins. Missing or invalid API isolation configuration fails the build and the API client also fails closed at startup. There is no fallback from the demo origin to the farmer API.

## Provisioning requirement

No separately isolated demo API and database have been provisioned or verified in this repository. Do not set `VITE_DEMO_MODE=true` until operators have created a dedicated demo service backed only by synthetic records, verified its database target and authorization boundaries, and configured the two distinct API origins. Never copy farmer records into that database. Demo credentials must belong only to synthetic accounts in that isolated service; the frontend must fetch them at runtime and must not embed them in source, build variables, or static assets.

When demo mode is enabled, the login page requests `GET /v1/demo/public-config` from the selected demo API. The isolated demo service must implement this endpoint and return the public login identifier/password only when it can assert `environment: demo`, `demo_enabled: true`, `isolation_verified: true`, and `synthetic_data_only: true`. If the endpoint is absent or any assertion is false, the frontend hides the credential section and disables sign-in. This endpoint does not exist in the shared backend. After a visitor chooses **Use Demo Account**, the existing normal sign-in flow posts the credentials to `/v1/browser-auth/login` on the demo API. The frontend never falls back to the farmer API.

The frontend trusts those response flags; it cannot inspect the API process's database target. The demo service must derive them from enforced deployment configuration and a reviewed database identity, not from client input or a hard-coded response. A distinct URL and a positive flag alone are not independent proof of isolation.

The existing shared demo account, its role, credentials, records, and database were not changed. The current authoritative application database identity remains unresolved, and its existing records have not been established as synthetic. Keep demo mode disabled until isolation is independently demonstrated.

## Build configuration

- Farmer build: set `VITE_DEMO_MODE=false` or leave it unset; configure `VITE_API_BASE_URL` for the farmer service.
- Demo build: set `VITE_DEMO_MODE=true`, `VITE_API_BASE_URL` for the farmer service, and `VITE_DEMO_API_BASE_URL` for the separately provisioned demo service. Both origins are public build configuration, not secrets. The frontend contains no demo credentials; the verified demo API supplies them at runtime.
- Do not place passwords, tokens, or database URLs in `VITE_*` variables. The production build guard rejects sensitive variable names, including demo account credentials.

This frontend restriction does not prove backend/database isolation, create a demo service, or make the current shared demo account safe for public use.
