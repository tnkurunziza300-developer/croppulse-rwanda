# Agricultural Evidence Quality and Provenance — Phase 23

**Review date:** 2026-10-29  
**Status:** Development only; no external scientific, legal, or production approval is implied.

## Verified repository state

- Alembic source head is `0019_soil_records`. No migration was added or run in this phase.
- `data/agronomy/rules.json` and `review_decisions.json` contain no rules or decisions. `utils.agronomy_knowledge` validates the pack and reports **0 approved rules** and 6 open quality issues. Its approval trust anchor remains disabled, so JSON attestations cannot activate authoritative guidance.
- `data/verified/nisr_sas_2023_2026.csv` is a 2,020-row district aggregate covering 2023–2025 Seasons A/B/C and 2026 Seasons A/B. Its actual SHA-256 remains `98de5073d00f60231df496da3c19912834a3156a7f2f044bd6eaa5108f313927`, matching the unchanged `data/verified/MANIFEST.json` and agronomy source registry.
- The NISR manifest specifies cultivated area in hectares and production in tonnes. It records source workbook/table references and limitations, including omitted missing/dash cells and explicit zero/zero non-cultivation pairs. Structural/checksum validation verifies the local artifact and parsing rules; it does not independently verify the survey estimates or establish reuse permission.
- The existing recommender ranks only using provisional CropPulse guide categories. NISR historical values are not used to rank, exclude, predict yield, or assert field suitability. Missing elevation/water inputs remain unknown and do not silently exclude a crop. No soil, fertilizer, irrigation, disease-treatment, or yield-prediction advice is introduced.
- The weather adapter labels Open-Meteo data as model forecasts, carries provider attribution and retrieval time, labels stale cache, and says forecasts are not observations. The weather alert registry is empty; no alert-generation rules are active.
- The field decision summary labels plans provisional, farmer observations and soil-test transcriptions as farmer-entered, and saved forecasts as forecasts with coordinate limitations. Missing values remain unknown.

## Changes in this phase

The crop-comparison page now shows the NISR dataset title, publisher, reference period, retrieval date, declared units, source link, and expandable limitations from the existing manifest. It explicitly states that CropPulse checksum/structural checks do not verify NISR estimates, field suitability, or future harvests.

The recommender no longer treats a generic `state: validated` as proof that its history came from NISR. NISR-specific historical context is labeled as structurally/checksum checked only when the status also contains NISR/SAS publisher and source metadata with a SHA-256. The output explicitly says estimates are not independently verified. All results remain provisional; approved guidance stays empty.

No source CSV, manifest, review decision, agronomic rule, model, forecast record, or application database was changed.

## External data and reuse status

- **NISR SAS:** the [official SAS source page](https://gis.statistics.gov.rw/data-sources/surveys/Seasonal-Agricultural-Survey) describes the survey's statistical purpose. The repository records attribution and provenance, but source-specific reuse/redistribution permission for the compiled CSV has not been established. A current official [NISR 2025 SAS report](https://www.statistics.gov.rw/sites/default/files/documents/2025-12/SAS%202025%20Final%20report.pdf) displays a copyright notice; this does not determine the rights for every workbook or the local compilation. Obtain applicable terms before redistributing.
- **Open-Meteo:** its [current terms](https://open-meteo.com/en/terms) describe Free API use as non-commercial, publish request caps, require CC BY 4.0 attribution for data, and disclaim accuracy/availability warranties. The [pricing page](https://open-meteo.com/en/pricing) describes a commercial-use subscription. CropPulse's intended service/commercial status and provider plan remain unresolved. Terms were checked 2026-10-29 and may change.
- **METEO RWANDA bulletins:** local PDFs and limited source-linked transcriptions exist; repository review did not establish permission for product redistribution of the PDFs or extracted values. Obtain written applicable terms. Bulletins remain forecasts, not observations; transcription coverage is incomplete.
- **PlantVillage/model:** the current [Hugging Face dataset page](https://huggingface.co/datasets/mohanty/PlantVillage) tags the dataset CC BY-SA 3.0. The local model snapshot is not pinned to an immutable dataset revision, and no legal analysis establishes obligations for the weights or commercial redistribution. No Rwanda field accuracy/calibration validation is evidenced. Model output remains experimental maize-only screening, not diagnosis; no treatment advice is produced.
- **Privacy, retention, security, operations:** farmer accounts, farm locations, reports/photos, messages, and records persist. Organizational decisions for legal basis, retention/deletion/export, access requests, data residency, incident response, support, deployment hardening, rate/concurrency limits, and live backup/restore remain outstanding. Automated tests do not resolve those decisions.

## Release boundary and next work

Keep CropPulse development-only. Do not use NISR aggregate statistics as agronomic rules or field-specific suitability. Authoritative guidance requires traceable current source material, a scoped rule, qualified local specialist review, valid approval and expiry, and independent checking. Weather alerts require approved source-backed rules plus validation and operational monitoring. Disease-model expansion requires immutable data/model provenance, consented and specialist-labeled Rwanda field data, farm/time-separated evaluation, calibration/abstention, and independent error review.

Before any farmer pilot or public release, also resolve source permissions, privacy/retention policy, secure staging and runtime database identity, gateway abuse controls, tested recovery objectives, authenticated browser workflows, and accessibility/language/low-bandwidth checks. No browser or field validation was performed for this phase.
