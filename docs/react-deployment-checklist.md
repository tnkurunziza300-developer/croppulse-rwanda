# React / FastAPI deployment checklist

This is a deployment planning checklist, not evidence that a deployment exists or is production ready.

## Origin, cookies, and API configuration

- Prefer serving React, FastAPI, and Streamlit through one HTTPS hostname/reverse proxy. The host-only `cp_session` cookie uses `Path=/` so Streamlit can revalidate it after reload; only trusted CropPulse services should share that hostname. If separate origins are used for React/API, keep them same-site for the `SameSite=Lax` browser cookie, configure the exact React origin in `CROP_PULSE_CORS_ORIGINS`, and test browser credentialed requests and Streamlit cookie recovery in the target browser.
- Set `CROP_PULSE_ENVIRONMENT=production` and `CROP_PULSE_COOKIE_SECURE=1`. Keep `CROP_PULSE_SECRET_KEY` in a managed secret store and rotate it using a reviewed session invalidation plan.
- API startup fails when `CROP_PULSE_ENVIRONMENT` is missing/unsupported. Staging and production require an explicit HTTPS-only `CROP_PULSE_CORS_ORIGINS` allowlist; wildcard origins, insecure cookies, and `CROP_PULSE_AUTO_CREATE_SCHEMA=1` are rejected.
- The API caps each body-bearing request at 8 MiB before FastAPI parses it. Enforce a compatible or stricter limit at the reverse proxy and add concurrency/connection controls there; the application body cap is not a DDoS defense.
- Never use wildcard CORS with credentials. Do not expose database credentials or the JWT secret through React environment variables.
- Apply Alembic migrations as a reviewed release step after a verified database backup. Do not use `CROP_PULSE_AUTO_CREATE_SCHEMA=1` outside isolated development.
- Serve `frontend/dist` with SPA route fallback, correct MIME types, HTTPS, and static asset caching. Keep `/v1/*` dynamic and non-cacheable.

## Security and operations still required

- Review cookie scope, CSRF behavior, CORS, TLS termination, forwarded headers, security headers, rate limits, secret rotation, dependency updates, vulnerability response, logging, monitoring, and incident response with the actual hosting configuration.
- The login limiter uses hashed IP/email buckets persisted in the application database. Validate thresholds, privacy implications, cleanup behavior, and load under the chosen database and deployment topology. Add edge/network rate limits as a second layer.
- Application throttles cover account-sensitive actions only. Apply gateway rate limits to other API routes, especially crop-health uploads, forecasts, and messaging, and monitor rejected/abusive traffic.
- Configure protected encrypted backups with access controls, retention, and off-site copies; monitor backup outcomes and rehearse restoration. The app does not currently monitor backups.
- Establish account recovery/deletion, privacy/retention policy, legal review, data residency, support contacts, and user communication before real farmer data collection.
- Use the [Phase 3A security, privacy, and recovery review](security-privacy-recovery-phase-3a.md) as the source inventory for protected database/source files and recorded local restore evidence.
- Conduct farmer/reviewer/admin authorization review, district assignment review, penetration testing, dependency scanning, accessibility review, low-bandwidth/mobile testing, and agronomic review. Pilot with synthetic or consented test data and documented rollback criteria.

The current automated tests and local build do not verify infrastructure, public security, performance, disaster recovery, or real-world usability.
