# Weather and climate files: provenance review

Reviewed: 2026-10-22

## Result

There are 19 PDF bulletins in `data/raw/weather_climate/`: 13 monthly forecast bulletins and 6 seasonal outlooks. The PDFs contain METEO RWANDA branding/contact details and references to `meteorwanda.gov.rw`; their embedded PDF creation dates align with most filename periods. This supports identifying METEO RWANDA as the apparent publisher. It does **not** prove that every local PDF is an authentic byte-for-byte copy of the corresponding original publication, nor does it verify the forecasts against observations.

These files are forecasts/outlooks, not a continuous archive of observed farm weather. They are generally Rwanda-wide and describe district or sub-district zones, not individual field coordinates. They must not be presented as point observations or as a farm-specific forecast.

## Inventory

Issue dates below are read from the PDFs' embedded creation metadata. Periods are taken from the filenames and their internal year/month markers; where the local filename conflicts with those markers, the conflict is called out. Map zones and station-observation tables have not been transcribed. A limited set of explicit national rainfall outlook ranges has now been transcribed from PDF text and linked to each bulletin and page in the database; these are not independently verified forecast results.

| Local file | Period indicated | Review finding |
|---|---|---|
| `April_2026_Monthly_climatology_and_rainfall_forecast_for_May_2026.pdf` | May 2026 | PDF metadata: 2026-05-05. Publisher indicators present. |
| `August__2024_Monthly_climatology_and_rainfall_forecast_for_September_2024.pdf` | September 2024 | PDF metadata: 2024-09-06. Publisher indicators present. |
| `December_2024_Monthly_climatology_and_rainfall_forecast_for_January_2025.pdf` | January 2025 | PDF metadata: 2025-01-06. Publisher indicators present. |
| `February_2026_Monthly_climatology_and_rainfall_forecast_for_March_2026.pdf` | March 2026 | PDF metadata: 2026-03-05. Publisher indicators present. |
| `January_2026_Monthly_climatology_and_rainfall_forecast_for_February_2026.pdf` | February 2026 | PDF metadata: 2026-02-05. Publisher indicators present. |
| `July_2026_Monthly_climatology_and_rainfall_forecast_for_August_2026.pdf` | August 2026 | PDF metadata: 2026-08-05. Publisher indicators present. |
| `June_2026_Monthly_climatology_and_rainfall_forecast_for_July_2026.pdf` | July 2026 | PDF metadata: 2026-07-05. Publisher indicators present. |
| `March_2026_Monthly_climatology_and_rainfall_forecast_for_April_2026.__1_.pdf` | April 2026 | PDF metadata: 2026-04-06. Publisher indicators present. |
| `May_2025_Monthly_climatology_and_rainfall_forecast_for_June_2026.pdf` | **June 2026**, not June 2025 | Filename is misleading: PDF markers identify bulletin No. 5/2026 and metadata date 2026-06-06. The unchanged PDF is stored with an explicit filename-mismatch flag; do not treat extracted figures as verified until the original source record is reconciled. |
| `November_2024_Monthly_climatology_and_rainfall_forecast_for_December_2024.pdf` | December 2024 | PDF metadata: 2024-12-07. Publisher indicators present. |
| `November_2025_Monthly_climatology_and_rainfall_forecast_for_December_2025.pdf` | December 2025 | PDF metadata: 2025-12-05. Publisher indicators present. |
| `October__2024_Monthly_climatology_and_rainfall_forecast_for_November_2024.or.pdf` | November 2024 | PDF metadata: 2024-11-06. Publisher indicators present; local filename also has an unusual `.or` suffix. |
| `September_2026_Monthly_climatology_and_rainfall_forecast_for_October_2026_.pdf` | October 2026 | PDF metadata: 2026-10-05. Publisher indicators present. |
| `SEASONAL_FORECAST_FOR_JUNE_TO_AUGUST_2025.pdf` | June–August 2025 | PDF metadata: 2025-06-11. Exact METEO RWANDA publication is discoverable on its official site. |
| `SEASONAL_FORECAST_FOR_JUNE_TO_AUGUST_2026.pdf` | June–August 2026 | PDF metadata: 2026-06-09. Publisher indicators present; exact original not matched in the accessible official listing during this review. |
| `SEASONAL_FORECAST_FOR_MARCH-MAY_2025.pdf` | March–May 2025 | PDF metadata: 2025-01-22. Exact METEO RWANDA publication is discoverable on its official site. |
| `SEASONAL_FORECAST_FOR_MARCH-MAY_2026.pdf` | March–May 2026 | PDF metadata: 2026-02-10. Publisher indicators present; exact original not matched in the accessible official listing during this review. |
| `SEASONAL_FORECAST_FOR_SEPTEMBER-DECEMBER_2026.pdf` | September–December 2026 | PDF metadata: 2026-08-21. METEO RWANDA's official announcement for this outlook confirms the period and national forecast, but not a byte-level match to this local PDF. |
| `SEASONAL_FORECAST_FOR_SEPTEMBER_TO_DECEMBER_2025.pdf` | September–December 2025 | PDF metadata: 2025-08-29. Exact METEO RWANDA publication is discoverable on its official site. |

## What has and has not been verified

- **Publisher evidence:** METEO RWANDA identity, website, and/or contact details occur inside the inspected PDFs. Official METEO RWANDA pages describe monthly and seasonal forecast products and its agriculture climate services.
- **Cross-checks:** Official-site search results were found for the 2025 MAM, JJA, and SOND seasonal documents and official announcements/pages confirm the 2026 SOND forecast. Official monthly publication search results confirm the January and April 2026 product pattern. Exact source-document matches were not established for every PDF.
- **Time and geographic meaning:** Monthly and seasonal forecasts describe future periods from the issue date. Long-term mean ranges in a forecast are reference climatology, not observed rainfall for the forecast period. District/sub-district map descriptions do not support exact farm-coordinate values without digitizing and validating the source maps.
- **Scientific validation:** Forecast skill, uncertainty, local accuracy, and measured outcomes were not tested. A government-issued forecast is authoritative as a publication, but it is still a forecast and can differ from observed weather.
- **Reuse rights:** No explicit open licence or permission for republication/repackaging was found in the files reviewed. METEO RWANDA's climate-data request route indicates that data access is handled by request and approval; that alone does not establish the licence for these public bulletins. Obtain written terms from METEO RWANDA before redistributing extracted tables/maps or using them in a commercial service. Attribution is necessary but is not a substitute for permission.
- **System integration:** The supplied PDFs remain in ignored `data/raw/weather_climate/` and have also been imported unchanged as 19 PDF blobs plus provenance metadata into the local CropPulse database. The React page lists them through authenticated API endpoints. In addition, 13 nationwide numeric rainfall outlook ranges (9 monthly, 4 seasonal) are curated in `utils/weather_bulletin_records.json`, persisted as source-linked rows by migration `0014`, and displayed as filters, range charts, and a source-linked table. The June 2026 bulletin's local filename mismatch remains flagged. District-map bands and station-observation tables remain untranscribed; these ranges are not fed to the point forecast or agronomic recommendations. Other deployments need the source files and separate import commands after applying migrations.

## Recommended status and next action

Keep the original PDFs as source artifacts. Do not label them “verified weather observations.” The initial explicit national ranges are transcribed with page references; the June 2026 filename conflict still needs source reconciliation. Before adding further values, record exact source links, retrieval dates, licence/permission, geographic coverage, variables, units, and period definitions. Retain page/table/map references, compare each transcription to the PDF, and keep issue/valid periods so past outlooks cannot appear current. Preserve the distinction between observed measurements, climatological normals, monthly outlooks, seasonal outlooks, and Open-Meteo point forecasts.

For a field forecast based on measured historical climate, request station-level data and use permission from METEO RWANDA. For an official forecast display, prefer a supported official feed or a publication-linked bulletin view with issue and expiry dates over manually treating map ranges as field measurements.

## Sources checked

- [METEO RWANDA seasonal forecast products](https://www.meteorwanda.gov.rw/products/seasonal-forecast)
- [METEO RWANDA weather forecast scales and definitions](https://www.meteorwanda.gov.rw/services/weather-forecast)
- [METEO RWANDA climate services for agriculture](https://www.meteorwanda.gov.rw/services/climate-services-for-agriculture)
- [METEO RWANDA March–May 2025 seasonal forecast](https://www.meteorwanda.gov.rw/fileadmin/user_upload/Meteorwanda/Seasonal_Forecast/2025/MAM_2025_SEASONAL_FORECAST.pdf)
- [METEO RWANDA September–December 2025 seasonal forecast](https://meteorwanda.gov.rw/fileadmin/user_upload/SOND_2025_SEASONAL_FORECAST.pdf)
- [METEO RWANDA June–August 2025 seasonal forecast](https://www.meteorwanda.gov.rw/index.php?eID=dumpFile&f=140725&t=f&token=199c0184b0b06d56fd79d1c215603c5ecf9490fa)
- [METEO RWANDA September–December 2026 announcement](https://www.meteorwanda.gov.rw/publications-1/news/news-detail?cHash=7e7904cef04ef17f7f4c3057981be5f9&tx_news_pi1%5Baction%5D=detail&tx_news_pi1%5Bcontroller%5D=News&tx_news_pi1%5Bnews%5D=82767)
- [Irembo instructions for requesting METEO RWANDA climate data](https://support.irembo.gov.rw/en/support/solutions/articles/47001263560-how-to-request-for-climate-data)
