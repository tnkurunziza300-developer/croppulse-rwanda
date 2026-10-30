# Vercel React frontend with a same-origin API proxy

Vercel hosts only the React/Vite frontend. FastAPI and Streamlit remain separate
Python services. The browser calls `/v1/...` on its Vercel origin; Vercel forwards
those paths to the configured HTTPS FastAPI origin. This avoids cross-site
browser cookies while keeping the upstream hostname out of the Vite bundle.

## Vercel project settings

Set **Root Directory** to `frontend`, **Framework Preset** to Vite, **Build
Command** to `npm run build`, **Output Directory** to `dist`, and leave the
Install Command automatic (`npm ci` from `frontend/package-lock.json`). Do not
configure a custom container build or a Services project. There is one Vercel
configuration file: `frontend/vercel.mjs`; the old root service-routing config
was removed because it conflicted with the separate Render API architecture.

The configuration requires `CROP_PULSE_API_ORIGIN` during Vercel configuration
evaluation. Add it as a non-`VITE_` project environment variable for Preview and
Production. It must be the public FastAPI HTTPS origin only, with no path,
credentials, query, or fragment. The config validates this value and emits a
rewrite for `/v1/:path*`, followed by the existing SPA fallback to `/index.html`.
The `/v1` scope matches the current React API calls and does not capture static
assets, health checks, or client-side routes. The `/v1` rewrite is marked
non-cacheable to protect account-specific responses.

Set `VITE_API_BASE_URL` to the literal `same-origin` for Vercel Preview and
Production builds. This is a public build-time switch, not a URL or secret. The
Vercel configuration origin is not a Vite variable and is not compiled into
browser JavaScript. Do not put database URLs, passwords, JWT/session secrets,
tokens, or API credentials in any `VITE_*` value. Keep demo mode disabled unless
separately reviewed and explicitly configured.

On FastAPI, set `CROP_PULSE_CORS_ORIGINS` to the exact HTTPS Vercel Preview and
Production origins that should be allowed. Use explicit origins; do not use
`*`. The backend must also remain configured for HTTPS secure cookies. The
frontend's existing credentialed fetches and CSRF token flow are unchanged.

## Local development

Do not set `VITE_API_BASE_URL=same-origin` locally. The existing Vite default
continues to call `http://127.0.0.1:8002`. No public backend URL is required for
local development.

## Proxy/header behavior and verification boundary

Vercel documents external-origin rewrites as reverse-proxy routing that leaves
the browser URL unchanged. The wildcard forwards the `/v1` path; no request or
response header transform is configured, so the proxy does not intentionally
remove authentication headers or upstream `Set-Cookie` headers. Vercel's
documentation does not explicitly guarantee `Set-Cookie` forwarding semantics,
so verify multiple `Set-Cookie` headers, cookie paths, `Secure`, and the CSRF
cookie flow in a protected Preview deployment before using the proxy with
accounts. Do not treat unit tests as proof of Vercel edge behavior. If Preview
testing shows cookies are not preserved correctly, replace the external rewrite
with a Vercel serverless proxy handler that explicitly forwards the request and
all upstream response headers, then test it in Preview.

## Local verification commands

From PowerShell:

```powershell
Set-Location 'C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda\frontend'
npm ci
npm test
npm run typecheck
npm run lint
$env:VITE_API_BASE_URL = 'same-origin'
$env:CROP_PULSE_API_ORIGIN = 'https://api.example.invalid'
npm run build
```

The example origin above is only a harmless build-test placeholder; replace it
in Vercel's Preview and Production environment configuration with the actual
FastAPI HTTPS origin. Do not commit the value to source control. After the local
build, inspect `dist` to confirm neither the placeholder nor any configured
upstream origin appears in JavaScript bundles.

Before considering the proxy verified, make a protected Preview deployment and
check the build log, SPA deep links, static assets, API methods/bodies/query
strings/status codes, `Cache-Control: no-store`, login/logout `Set-Cookie`
headers, and browser cookie/CSRF behavior. No Vercel deployment or browser test
was performed by this source change.
