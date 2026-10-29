# CropPulse Rwanda national platform audit and implementation status

Audit date: 2026-10-18. This is a source and local-test audit, not a certification of the agricultural data or deployed services.

## Baseline

- Architecture: Streamlit farmer, planning and analytics workflows; FastAPI authenticated Phase 1 API with SQLite/Alembic; React/Vite administration and farmer workspace; pandas-based ingestion, validation and crop ranking.
- Existing strengths: canonical 30-district/5-province reference; unknown districts are rejected rather than guessed; data manifests and checksums; quarantine and duplicate checks; synthetic sample data is explicitly labelled and excluded from recommendation ranking; recommendations disclose missing soil, weather and market evidence; farmer records are separate from demonstration statistics.
- Existing test inventory: Python suite in `tests/`, React/Vitest suite in `frontend/src/`, plus TypeScript checking, lint and production build scripts. The project documents prior passing runs in `docs/phase-2-verification.md`; that historical report is not a fresh baseline for this change.
- Pre-change baseline run: `tests/windows_safe_pytest.py` was started before editing, but exceeded the command wait window and did not return a final summary. No pre-change pass count is claimed.
- Prior iteration verification (2026-10-18): Python suite **71 passed, 1 warning**; frontend typecheck passed, Vitest **10 passed**, build passed and lint completed. Initial sandboxed Vitest/build attempts hit Windows `spawn EPERM`; reruns with process spawning enabled succeeded.
- Phase 2 final Python verification: `.venv\\Scripts\\python.exe tests\\windows_safe_pytest.py` — **76 passed, 1 warning** (17.95 seconds). The same AnyIO rewrite warning remains.
- Phase 2 frontend commands: `npm run typecheck` — exit 0; `npm run lint` — exit 0; `npm test -- --reporter=dot` — **10 passed**; `npm run build` — exit 0. Vite test/build first returned `spawn EPERM` in the sandbox; the same commands passed with Windows process spawning enabled.
- A direct targeted pytest run initially could not write AppTest's default OS-temp files under the managed Windows ACL. The repository's `windows_safe_pytest.py` configures the project-local writable temp directory; the complete suite including all weather UI tests passed through that runner.

## National coverage assessment

District selection covers 30 names grouped into five provinces. On 2026-10-18, the NISR-hosted District Boundary 2022 layer metadata was checked; the project list's total and province distribution match, and NISR describes boundaries updated through 2022 census mapping. Individual district strings have not been compared record-by-record. The service also exposes district IDs and a sector layer, but the project has not ingested the geometry or IDs, nor tested exact name/ID equivalence or point-in-polygon matches. Therefore weather location is farmer-entered and only checked against the layer's bounding rectangle. Soil tests, locally validated crop calendars, and equally reliable agricultural statistics across districts are not established. `data/sample/sample_crops.csv` is synthetic demonstration data. The crop knowledge pack is explicitly unverified and does not represent approved national agronomic recommendations.

| Capability | Current evidence and limit | Status |
| --- | --- | --- |
| District selection | 30 names/5-province distribution align with NISR 2022 service metadata; exact string match and boundary geometry/IDs not ingested | National list available; spatial match outstanding |
| Sector selection | NISR service exposes a sector layer, but CropPulse has not ingested or validated its identifiers | Not available in app |
| Crop recommendations | General compiled crop/zone guidance; only validated manifested statistics can influence ranking | Provisional, not nationally validated |
| Weather | Streamlit forecast page accepts user-entered coordinates for any selected district context; 7-day model forecast, attribution and stale warning; no weather-derived recommendation | Integrated; district-coordinate relation unverified |
| Crop image screening | Experimental PlantVillage model supplies maize candidate labels for reviewer attention; not a diagnosis or treatment engine | Limited experimental screening implemented; Rwanda field validation and advice remain unimplemented |
| Fertilizer planning | Farm planner avoids prescribing rates without verified local guidance | No rate calculator |
| SMS/USSD | No provider integration or tested sandbox | Not implemented |
| Offline | No service worker or multi-device offline synchronization identified | Not implemented |

## Change in this iteration

Integrated `utils/weather.py` into the existing Streamlit `Weather & Climate` page. Users select a district for context and provide farm coordinates; no district centroid is invented. The UI shows provider-returned grid coordinates, a seven-day table with °C and mm/day units, retrieval timestamp, attribution, loading indication, unavailable states, and a prominent stale warning with approximate cache age. Local gauge/thermometer entries remain separate. The adapter requires coordinates within a broad Rwanda bounding box, validates response structure, dates, and numeric values, sets an eight-second timeout, caches in process memory for 30 minutes, and may return a cached forecast for up to 24 hours as `stale`. `tests/test_weather.py` and `tests/test_weather_ui.py` cover response validation, national selection list, loading wrapper, rendering, provider failure, provenance, caching and stale fallback. Tests use a mocked provider; no live-provider availability or forecast-accuracy claim was tested.

Open-Meteo documents global forecast coverage, weather data under CC BY 4.0, and free API access as non-commercial only. CropPulse must not use the free endpoint for an advertising, subscription, or other commercial deployment without securing a suitable licence. Forecast coverage does not imply farm-level accuracy. See [Open-Meteo forecast documentation](https://open-meteo.com/en/docs) and [terms](https://open-meteo.com/en/terms).

## Prioritized next work

1. Ingest or query NISR's district/sector geometry and IDs, document reuse terms, validate canonical-name/ID joins and point-in-polygon behavior, and version the source before claiming administrative coordinate validation.
2. Add deployment-level weather rate limits/shared caching and review location privacy; monitor provider terms and forecast errors. Keep forecasts separate from crop ranking until agronomists define and validate a defensible use.
3. Build provenance manifests for crop guidance as well as statistics: publisher, document/version, geography, crop/variety, season, valid dates, licence, review status and reviewer. Obtain qualified local review before calling advice verified.
4. Evaluate disease models on Rwanda-relevant, field-collected images with documented class coverage, licensing, performance by crop and conditions, and an extension escalation path. Keep diagnosis unavailable until that evaluation exists.
5. Add fertilizer calculations only from sourced, crop/soil-specific recommendations and display units, assumptions and missing information.
6. Evaluate Rwanda operator/provider coverage, pricing, consent and sandbox access before an SMS/USSD adapter. Prototype offline public guidance separately from private account data.
7. Run a representative pilot across varied agroecological conditions; geographic selection tests must not be presented as evidence of agronomic accuracy.

## Remaining limits and deployment requirements

The weather page is currently Streamlit-only and is not called by React or FastAPI. Its process-local cache is not shared across workers and is lost on restart. The NISR layer's rectangular extent can include points outside Rwanda and is not point-in-polygon validation. There is no sector lookup, live disease classifier, treatment guidance, fertilizer-rate source, SMS/USSD connection, service worker or sync queue. The crop guidance still requires qualified verification. No production readiness or nationwide agronomic accuracy is claimed.
