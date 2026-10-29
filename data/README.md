# Data
- `sample/sample_crops.csv`: **Illustrative sample data, not official statistics.** Randomly generated (seed 7).
- `raw/nisr_sas/`: private source-workbook location (git-ignored). Preserve the original NISR workbooks here.
- `verified/`: normalized NISR-derived CSV and manifest (git-ignored). When present they replace the sample for Streamlit analytics and the signed-in React National statistics page via the shared data loader.

## Import the supplied NISR SAS tables

Place the five source workbooks in `data/raw/nisr_sas/` using their supplied filenames, then run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m utils.nisr_sas_import
```

The importer reads only the district-level cultivated-area and crop-production tables listed in `utils/nisr_sas_import.py`. It does not edit the source workbooks. It writes `verified/nisr_sas_2023_2026.csv` and `verified/MANIFEST.json`, including source URLs, table references, retrieval date, output checksum, each source workbook checksum, processing notes, and excluded-record counts. CropPulse's existing `utils.data_loader.load_data()` checks the manifest and CSV and uses this dataset instead of demonstration data. The Streamlit analytics and the signed-in React **National statistics** page use that same loader through the read-only `/v1/agricultural-statistics/nisr` API. The API serves only a validated NISR-published dataset; it does not expose demo data as NISR statistics.

The imported coverage is 30 districts and 8 explicitly mapped crop categories (Maize, Beans, Cassava, Irish potato, Sorghum, Paddy rice, Sweet potato, Banana), across 2023–2025 Seasons A/B/C and 2026 Seasons A/B. 2026 C is not present in the supplied workbooks. The importer retains observed zeros, omits missing/dash cells and explicit 0/0 non-cultivation pairs, and records area/production pairs with zero area and positive production as exclusions instead of silently repairing them. CropPulse structural validation checks schema, units, geography, duplicate keys, and checksums; it does not independently validate NISR sampling or estimates. These are district-level survey aggregates, not farmer records, disease labels/prevalence, causal findings, or stand-alone crop advice. Do not use them as inputs to the crop image model.

For source context, use the [NISR SAS 2023 publication](https://www.statistics.gov.rw/data-sources/surveys/Seasonal-Agricultural-Survey/Seasonal-Agricultural-Survey/seasonal-agricultural-survey-2023), [NISR SAS 2024 annual report](https://www.alpha.statistics.gov.rw/statistical-publications/agriculture-environment/seasonal-agricultural-survey-2024-annual-report-2024), [NISR SAS 2025 publication](https://www.statistics.gov.rw/data-sources/surveys/Seasonal-Agricultural-Survey/Seasonal-Agricultural-Survey/seasonal-agricultural-survey-2025-), and the [NISR 2026 Season A](https://statistics.gov.rw/statistical-publications/agriculture-environment/seasonal-agricultural-survey-season-2026) and [Season B](https://statistics.gov.rw/statistical-publications/agriculture-environment/seasonal-agricultural-survey-season-b-2026) releases. Check NISR for updated tables before refreshing this import.

Required columns: `district, crop, season, year, area_ha, production_t` (optional: `data_origin`).
For sources not handled by the importer, prepare this long format carefully and record source and retrieval date in the manifest.

Rows with negative cultivated area or negative production are quarantined during loading and excluded from analytics. Zero or missing area remains visible for data-quality review but cannot contribute to yield calculations. A dataset marked `pending` or `warning` can be explored, but is excluded from recommendation ranking until its manifest, checksum, and validation checks pass. The manifest `units` field must identify production in tonnes (`t`, `tonne`, or `tonnes`) and area in hectares (`ha`, `hectare`, or `hectares`).

Farmer records and saved crop plans are separate from this statistics dataset. With the Phase 1 API configured, they persist under a signed-in farmer account; without it, guest records remain in the active Streamlit session. Extension notes, market observations, feedback, review submissions, pest reports, cooperative activities, and weather observations remain session-only and exportable. None of these entries are verified simply because they are saved.
