# Weather forecast workflow

Weather alert preferences, the intentionally inactive rule registry, new field association behavior, licensing review, and scheduler gaps are documented in [weather-alert-readiness.md](weather-alert-readiness.md).

## Use

### React workspace

Sign in to the React workspace and open **Weather & climate** from the main navigation. Choose one of your farms and a saved field with coordinates, or enter the farm latitude and longitude manually in decimal degrees. Confirm the save checkbox and select **Get 7-day forecast**. Coordinates are sent to Open-Meteo and stored with the forecast under the signed-in account; this does not change the farm record. The API reuses coordinate validation, provider timeout, process cache, attribution, and stale fallback from `utils/weather.py`.

The app can only select saved field coordinates that the farmer supplied earlier. It does not infer coordinates from a district name or use a synthetic district centroid. The form checks general numeric coordinate ranges and the adapter checks the Rwanda bounding extent; neither check proves that the point lies inside Rwanda, the selected district, or the named farm.

### Streamlit during migration

The existing Streamlit workflow remains available at **Plan / Gahunda → Weather & Climate** while remaining farmer workflows are migrated. It retains the district-context selector, manual coordinates, and temporary local-observation form. The React forecast view does not yet include that session-only local-observation form.

Both clients request the same seven-day forecast from the same adapter. Choose the farm's latitude and longitude in decimal degrees and request a forecast; no API key is required by this implementation.

There is no environment variable or API credential to configure. The page sends the entered coordinates to the Open-Meteo forecast endpoint on submit. Open-Meteo currently documents the generic forecast API as globally available, with a seven-day default forecast (extendable to 16 days). CropPulse requests daily maximum and minimum 2 m temperature and daily precipitation total in the Africa/Kigali timezone. Values are labelled °C and mm/day.

The result is a model forecast, not a current observation, station reading, seasonal outlook, or planting recommendation. The page shows the provider's returned grid point and retrieval timestamp. During provider failure it may show a successful process-cache entry older than 30 minutes and no older than 24 hours; that result has a visible **STALE FORECAST** warning and approximate cache age. Entries older than 24 hours are not served. A fresh cache entry may be reused for 30 minutes. The cache is in process memory, shared only by sessions handled by that process, and is cleared at restart.

Before requesting a forecast, confirm the save checkbox. The authenticated API requires this explicit flag; it stores the provider response and the supplied point (rounded to four decimal places) under the current account. The record is private to that account, and account deletion cascades to it. `GET /v1/weather/forecasts` lists up to the 50 most recently retrieved saved locations; the database keeps the latest forecast for each requested point. Opening a saved item is visibly labelled **SAVED FORECAST** with its original retrieval age. Unavailable provider responses are not persisted. A stale fallback remains marked stale and retains its original retrieval timestamp. Forecast coordinates are not written to the farm or field record.

Local gauge or thermometer submissions remain a separate, user-entered, session-only observation workflow. They are labelled unverified and are never merged with provider forecasts.

### METEO RWANDA source bulletin library

The React page also lists the supplied METEO RWANDA monthly and seasonal forecast PDFs. These are preserved as original documents in the database, with their SHA-256 digest, publisher, PDF date, valid period, category, source page, and provenance caveat. The API serves the PDF only to a signed-in user. The archive does not extract map ranges into farm observations or connect those ranges to crop recommendations. Expired periods are shown as past bulletins.

Apply the additive Alembic migration, then import the source files from `data/raw/weather_climate/`:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m utils.import_weather_bulletins
```

The import command is idempotent by source filename and refreshes the stored PDF and digest if the source file changes. It expects all inventoried PDFs to be present. The current source archive is about 16.5 MB and storing it in the database increases backup size. For deployment, preserve the source files and run the import against the intended database; local ignored files are not included in a code checkout by default.

The documents appear to be METEO RWANDA products, but exact original-file matches are incomplete and the filename for the June 2026 monthly bulletin is inconsistent. See [weather data review](weather-data-review.md). Keep the UI attribution and forecast-period labels. Written permission for republishing the PDFs or their extracted data has not been confirmed; confirm reuse terms with METEO RWANDA before public or commercial deployment. These bulletin documents are forecasts/outlooks, not measured observations, and their district maps do not validate a specific farm location.

### Structured bulletin outlooks

Selected explicit national rainfall ranges from bulletin text are stored separately from the original PDF rows in `weather_bulletin_records`. The additive Alembic migration `0014_weather_bulletin_records` creates this table. Each row records its source bulletin, outlook type, nationwide scope, valid period, rainfall range and units, any published long-term-mean range/anomaly, page number, and a labeled transcription note (not a quotation). The importer refuses to create a record if its source PDF has not first been imported. It can be rerun safely:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m utils.import_weather_bulletins
.\.venv\Scripts\python.exe -m utils.import_weather_bulletin_records
```

The authenticated `GET /v1/weather/climate-data` endpoint accepts `year`, `record_type` (`monthly_outlook` or `seasonal_outlook`), and `search`. React displays national monthly and seasonal rainfall ranges as range charts and a source-linked table; users can filter by valid-period year/type and search the transcription note. Values are expressed as mm per month or mm per season. They are broad publisher outlook ranges, not station observations, farm-specific forecasts, or continuous historical measurements.

The initial curated import includes 13 numeric nationwide ranges from 19 archived PDFs: 9 monthly and 4 seasonal records, all linked to page 1 and their PDF record. Other bulletin contents remain available in original PDFs but have not been structured. No district/region map ranges or station-observation tables are imported in this first release. The June 2026 outlook PDF's archive filename says May 2025; the PDF's stated outlook period is used for the record and the mismatch remains a provenance limitation. The transcription manifest is `utils/weather_bulletin_records.json`; review any future additions against the named PDF/page before importing.

The chart/table is not a generated forecast and does not feed crop plans, disease assessments, or fertilizer advice. Source reuse permission remains unconfirmed; confirm METEO RWANDA's terms before redistributing numeric extracts or using them commercially. Migration `0014` is additive; follow the normal migration review and backup process before applying it to a deployment database.

## Location coverage and provenance

The district selector lists the 30 names in `utils/geography.py`; its total and five-province distribution match metadata for the [NISR-hosted District Boundary 2022 layer](https://gis-server.statistics.gov.rw/server/rest/services/Hosted/District_Boundary_2022/FeatureServer/0), which says boundary data were updated through 2022 census mapping. The individual district strings have not yet been compared record-by-record with the service. That service exposes district IDs and a sector-boundary layer, but CropPulse does not currently ingest its geometry or IDs. The adapter checks coordinates against the layer's published rectangular extent (`utils/weather.py`); the rectangle includes points outside Rwanda and is not point-in-country or point-in-district validation. The selected district and point-to-district relationship remain unverified. No district centroid or synthetic coordinate is substituted. A follow-up should ingest or query the NISR geometry, document its reuse terms and test spatial matches before claiming verified district/sector selection.

Open-Meteo's response coordinates represent its selected model grid point, not necessarily the exact entered farm location. Forecast quality and resolution vary by model and location; the coordinates alone do not imply farm-level accuracy. Network and malformed-response failures produce an unavailable state unless an eligible stale cache exists. Forecasts are not connected to CropPulse recommendations, disease diagnosis, or fertilizer planning.

## Provider attribution and licence

The UI displays: “Weather forecast data by Open-Meteo.com (CC BY 4.0).” This preserves attribution for the weather data and identifies the licence. See [Open-Meteo Forecast API documentation](https://open-meteo.com/en/docs) and [current terms](https://open-meteo.com/en/terms), checked 2026-10-18. The current terms restrict the free API to non-commercial use, including rate limits of fewer than 10,000 calls/day, 5,000/hour and 600/minute. The terms classify advertising, subscriptions, commercial products, and promotional activities as commercial. Do not deploy the free endpoint in those contexts; obtain an appropriate subscription/licence first. No paid service has been enabled or purchased. Open-Meteo disclaims guarantees of data accuracy, completeness, and uninterrupted availability.

The React account stores the latest forecast for each requested coordinate (rounded to four decimal places), with forecast values, source, retrieval time and available/stale status. The record is owner-scoped; the API only returns the signed-in user's records, and account deletion cascades to these forecasts. The page lists the saved locations and retrieval times so a stored forecast can be reopened with a saved/historical warning. Unavailable responses are not stored. The existing process-local cache remains separate, lasts 30 minutes for fresh results, and may provide stale fallback data up to 24 hours old. Streamlit has not been changed to save forecasts. A public or multi-worker deployment still needs server-level abuse controls, shared caching/rate limits, privacy review, monitoring and a deployment-specific provider licence assessment. Coordinates are transmitted to Open-Meteo and may appear in provider technical logs under its privacy terms.
