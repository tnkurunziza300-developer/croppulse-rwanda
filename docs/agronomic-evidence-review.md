# Rwanda agronomic evidence review

Review date: 2026-10-22

## Existing recommendation rules

`knowledge.py` currently contains a CropPulse-maintained rules pack for 12 crops. The values below are application assumptions, not records imported from a cited Rwanda crop guide:

- Broad four-zone groupings and district-to-zone assignments.
- Crop-by-zone fit classes that determine recommendation order.
- Season-by-crop planting months, including the words “Plant now” in the general calendar helper.
- Altitude ranges and water categories, including hard exclusions when entered elevation is far outside a range or water is low for a high-water crop without irrigation.
- Growing-duration ranges, planting-material rates, indicative harvest/yield ranges, and generic crop tips.

The pack itself labels the information approximate and unverified. Its zone groupings are explicitly not official Rwanda agroecological zones. There are no source identifiers, publication dates, crop-specific RAB evidence records, or recorded expert-review dates attached to those individual values. They therefore cannot be presented as verified for a farmer's district, field, or season.

The existing NISR SAS loader remains the only route for the verified agricultural statistics. It validates manifest/checksum and record structure. SAS describes observed crop area, production, and yield. Those observations do not establish an individual farm's suitability. In this update, NISR history is descriptive context only; it no longer affects the crop rank, suitability status, or risk list.

## Rwanda-specific sources reviewed

| Publisher and source | Date and geographic/crop coverage | What it supports | Decision limitations and use in CropPulse |
|---|---|---|---|
| Rwanda Agriculture and Animal Resources Development Board (RAB), [“RAB Through Twigire Muhinzi Trains 14000 Farmer Promoters on agricultural practices”](https://www.rab.gov.rw/1-1/news-details/rab-through-twigire-muhinzi-trains-14000-farmer-promoters-on-agricultural-practices) | The page describes preparations for 2022B and says training was tailored to priority crops in respective districts/sectors across Rwanda. The page does not expose a publication date in the reviewed text. Beans and soybean demo plots are mentioned. | Confirms that Rwanda has district/sector-level extension activity and crop-specific season preparation. | It does not publish the crop/area-by-district planting windows, thresholds, or technical recommendations needed to replace the CropPulse rules. Not imported as a recommendation. |
| RAB, [Cereals Program](https://www.rab.gov.rw/rw/amakuru-1/cereals-program) | The page has no visible publication/update date. It discusses maize, rice, wheat/barley, and sorghum research and variety development nationally. | It describes research objectives including high-altitude maize traits and development of wheat agronomic practices such as planting depth/date. | It provides no applicable planting dates, altitude limits, field-level soil/water thresholds, or crop-by-district tables. Research objectives are not farmer prescriptions. Not imported as a recommendation. |
| RAB, [“RAB launches Rwanda Digital Soil Information System to improve agricultural productivity”](https://www.rab.gov.rw/1-1/news-details/rab-launches-rwanda-digital-soil-information-system-to-improve-agricultural-productivity) | The article states that RwaSIS launched on 2024-11-29. It names potato, rice, maize, wheat, beans, and cassava. At launch, potato and rice fertilizer recommendations were reported complete; testing for maize, wheat, cassava, and beans was still ongoing. It describes location-specific soil information accessed using a soil UPI. | Strong evidence that site-specific soil assessment and crop guidance exist in Rwanda and that blanket prescriptions are inappropriate. | The article is a system announcement, not the underlying trial tables or a downloadable crop suitability dataset. It does not provide values that can be encoded. CropPulse farm coordinates are not RwaSIS UPI values. No API, export, or redistribution terms for underlying recommendations were identified in the reviewed material. Not imported. |
| RAB, [RwaSIS portal](https://rwasis.rab.gov.rw/) | A current RAB-hosted digital soil service. A publication date, export specification, and machine-readable public dataset were not available in the reviewed page content. | Identifies an official route for location-specific soils and crop information. | The system's underlying data could not be inspected or imported as an auditable dataset here. Access, permitted reuse, attribution, and technical integration need confirmation with RAB/RwaSIS. Not connected. |
| FAO Global Soil Partnership, Dr. Rushemuka N. Pascal, [“Priorities for Sustainable soils fertility management for Rwanda”](https://www.fao.org/fileadmin/user_upload/GSP/docs/elmina/Rwanda_Priorities.pdf) | Presentation date is not shown in the document text reviewed. National soil/agroecological overview; it distinguishes broad regions and notes substantial soil fertility differences within an AEZ and across slope positions. | Supports the caution that broad agroecological zones alone cannot establish plot suitability and that soil/land-unit variation matters. | It is not a current crop-by-district planting guide or plot-level soil dataset. Its date and applicability to present-day decisions are uncertain. Used only to justify the limits of broad zones, not to create crop rules. |
| National Institute of Statistics of Rwanda (NISR), [Seasonal Agricultural Survey](https://statistics.gov.rw/data-sources/surveys/Seasonal-Agricultural-Survey) | Annual survey series; the page lists 2023–2026 releases and says survey outputs cover Rwanda's A/B/C seasons. | Establishes SAS as an agricultural statistics source for land use, area, yield, and production. CropPulse imports its verified SAS extract under `data/verified/`. | Survey observations are not agronomic suitability recommendations, forecasts, or guarantees. Kept separate from crop fit and ranking. |
| Ministry of Agriculture and Animal Resources (MINAGRI), [“MINAGRI Rallies Stakeholders to Boost Seeds and Fertilizer Distribution for 2026A Agricultural Season”](https://www.minagri.gov.rw/updates/news-details/minagri-rallies-stakeholders-to-boost-seeds-and-fertilizer-distribution-for-2026a-agricultural-season-1) | Meeting dated 2025-08-11; national preparation for 2026A. It describes the 2026A operating period as September–December and highlights maize, beans, Irish potato, cassava, and wheat. | Shows the value of time-specific national planning and tailored extension. | It is not a stable crop-specific planting calendar, district recommendation, or suitability threshold. A single campaign announcement cannot replace season-specific local advice. Not imported as a rule. |

## Evidence-backed model and current decision policy

No reviewed source supplied an auditable crop × location × season table with enough current detail to support a verified recommendation for this application. The existing recommendation response already carries a structured `evidence_record`; it now explicitly includes evidence status, broad applicability, `source_reference`, publication date, review date, limitations, and the role of NISR statistics. Where no crop-specific evidence exists, reference/date are null and status remains `provisional`. No database migration was needed, and no source has been promoted to verified status.

Current policy:

1. The candidate order still uses the existing CropPulse guide's provisional zone category, with alphabetical tie-breaking. The interface names this a **provisional guide fit**, and discloses that district-zone mapping is not official. It is not a probability or guarantee.
2. Existing elevation/water exclusion rules and explanations are retained for regression compatibility, but now visibly state that thresholds are provisional and not verified Rwanda exclusion limits. Missing elevation/water never excludes a crop.
3. Season month lists remain visible only as provisional CropPulse calendar months. Recommendation cards no longer say “Plant now” or imply a verified planting date.
4. NISR observations are shown as historical context only. They do not change crop ordering, suitability, or risk statements. Demonstration/pending/warning data remain ineligible as validated history.
5. Weather remains disconnected from crop ranking and planting timing.

## Work still needed for verified Rwanda recommendations

- Obtain RAB/RwaSIS source tables, rule documentation, or a permitted API/export, with crop, geography/UPI mapping, season, applicable date range, publication/revision date, and reuse terms.
- Ask RAB or district/sector agronomists to review each proposed rule, especially district/AEZ mapping and the altitude, water, planting window, growing duration, soil, and crop management values.
- Record source and reviewer provenance per rule, preserve the original source artifact/checksum, and add ingestion/validation tests before any rule becomes `verified`.
- Keep field-level soil recommendations dependent on plot/UPI soil evidence; do not infer them from the farm district or from national production statistics.

## Verification record

Verification on 2026-10-22: `.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests -q` — 120 passed. In `frontend`, `npm run test` — 33 passed; `npm run typecheck`, `npm run lint`, and `npm run build` — passed. Browser verification was not performed; use the manual checklist in the final report. This review does not constitute agronomist approval or farmer usability validation.

## Agronomic knowledge foundation

Implemented foundation version: **0.1.0** (2026-10-22). Files are in `data/agronomy/`; the Python validator and scoped-rule reader are `utils/agronomy_knowledge.py`. This is a version-controlled JSON registry, not a new application database or admin editing feature. The workflow is: edit a source/statement/rule record in a reviewable code change; run the validator; have an authorized technical and local specialist review the source and scope; record a real review decision; regenerate the manifest/report only after validation; keep changes in version control. Git history provides rollback; no destructive importer overwrites the live database.

### Source inventory and access

The registry currently contains five source records and four concise source-description statements. Sources were accessed or inspected on 2026-10-22 unless the row states otherwise. No agronomic rule was extracted from these institutional pages.

| Source | What was actually checked | Use/status |
|---|---|---|
| RAB, [Crop Innovation & Tech Transfer](https://www.rab.gov.rw/agriculture-development/crop-innovation-tech-transfer) | Page sections describe crop research, extension, and good-practice training. | Accessible; authority/source discovery only, no crop-specific values imported. |
| RAB, [RwaSIS launch announcement](https://www.rab.gov.rw/1-1/news-details/rab-launches-rwanda-digital-soil-information-system-to-improve-agricultural-productivity) | Announcement dated 2024-11-29; its launch-time crop/testing status is recorded as historical context. | Accessible; not the underlying trials or current recommendation status. No rules imported. |
| RAB, [RwaSIS portal](https://rwasis.rab.gov.rw/) | Portal was identified, but its content was not readable to the inspection tool. | Not ingested. Data, API/export, current recommendation status, and reuse terms require direct confirmation with RAB. |
| METEO RWANDA, [Climate Services for Agriculture](https://www.meteorwanda.gov.rw/services/climate-services-for-agriculture) | Page describes short-, medium-, seasonal-, and inter-annual services. | Weather-context source only; no forecast values or crop rules imported. Product-specific dates/geography and reuse permission still apply. |
| NISR, [Seasonal Agricultural Survey](https://statistics.gov.rw/data-sources/surveys/Seasonal-Agricultural-Survey) | Existing project CSV and manifest, not a new extraction. | Used only for district-level historical statistics; excluded from agronomic rule evidence. |

The NISR extract is `data/verified/nisr_sas_2023_2026.csv`; its existing manifest/checksum pipeline remains authoritative. The current file has **2,020 records** and matches the manifest SHA-256 `ebb90da343bddac95e77e9dde12ae5433d0dbd92a713689376b4847afc924b6c`. Coverage is 2023-2025 Seasons A/B/C and 2026 Seasons A/B, for the selected crops encoded in that file; it is a district aggregate, not farm-level evidence. Those records do not validate crop suitability or management prescriptions.

### Rule and review status

The registry contains **0 agronomic rules, 0 approved rules, and 0 review decisions**. The existing `knowledge.py` still contains 12 CropPulse-maintained provisional crop entries; those are inventoried separately from source-backed coverage and remain clearly labelled provisional in React, Streamlit, and recommendation output. There are no approved rules for any of the 30 districts, crops, categories, or seasons. The generated `data/agronomy/validation_report.json` provides a crop-by-crop coverage matrix; all listed districts remain without directly scoped approved guidance.

`schema.json` defines the rule contract; `utils/agronomy_knowledge.py` enforces IDs, source links, citations, known district and season vocabulary, NISR separation, approval/review requirements, and revalidation dates. `approved_rules_for()` fails closed on an invalid registry and only returns rules approved for the requested crop, district, and season while in date. Farmer-facing rule records omit reviewer identities. There is no knowledge edit API, admin UI, or database migration. Repository write access and code review are the current governance boundary; protect and review registry changes like source code.

`rules.json` must stay empty until actual source text or data is available and a scoped review has occurred. Source descriptions in `statements.json` are not farmer advice and cannot be used as substitute rules. `review_decisions.json` must contain real, auditable decisions; do not copy test fixture reviewers into it. The validator rejects a NISR statistical source as agronomic evidence. Fertilizer and pest-treatment rules require additional category-specific controls before activation (soil/context and rate basis; applicable, current legal product-use evidence, respectively); this initial registry is not a pesticide prescribing system.

### Reproduce validation and inspect files

From repository root in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m utils.agronomy_knowledge
.\.venv\Scripts\python.exe -m utils.agronomy_knowledge --write-manifest --write-report
```

The first command is read-only. The second writes the deterministic manifest and validation report only after the pack validates. It does not connect to or modify the app database. Run the NISR importer/data-loader checks separately when changing its CSV or manifest. No external RwaSIS data has been imported, no crop rule has been locally reviewed, and no guidance is approved for farmer use.

### Remaining blockers

- Obtain accessible primary RAB crop-specific manuals/released-variety tables and RwaSIS data with source locators, coverage, and reuse terms.
- Confirm currently valid scopes for any RwaSIS crop/fertilizer output; its 2024 launch announcement explicitly describes testing as still ongoing for some crops at that time.
- Obtain METEO RWANDA product-level data and permission before storing or redistributing it; do not use weather pages alone to justify crop-management rules.
- Identify authoritative Rwandan plant-health sources and applicable pesticide registration/legal-use information before any treatment advice.
- Have a qualified local agronomist/extension specialist review each exact rule version, assumptions, districts/seasons, exclusions, and revalidation date.
- Complete category-specific evidence requirements and conflict review before adding an approved rule. No claim of national agronomic coverage or farmer-ready verified recommendations is justified now.

### Verification added for foundation 0.1.0

## Permanent evidence intake foundation

Added a separate local intake store under `data/agronomy/intake/` and an operator CLI in `utils/agronomy_intake.py`. It accepts CSV, JSON, PDF, DOCX, and TXT up to 25 MiB; checks extensions/signatures, parses CSV/JSON structurally, rejects duplicate JSON keys and malformed rows, preserves exact originals only when metadata says retention is permitted, and records SHA-256 checksums and provenance. Restricted or permission-unknown material is not copied; unknown/prohibited retention requires a permitted reference. Dataset versions receive distinct immutable package directories. Audit events record state, actor ID/role, time, rationale, qualification attestation, and a tamper-evident hash chain. Archived bytes and event-chain hashes are checked before review transitions.

The package metadata separates historical statistics, original agronomic guidance, official documents, weather/climate records, and unverified submissions. Review states are distinct (`received`, `validation`, `technical_review`, `specialist_review`, `approved`, `active`, `superseded`, `expired`, `rejected`, `quarantined`). Approval for farmer-guidance lifecycle requires agronomic-guidance type, scope, source locators, dates, known permission/licensing, and separate submitter, technical reviewer, specialist reviewer, and approver identities. Activation is a separate knowledge-administrator event. Prior versions remain available for rollback. No record becomes farmer-visible from intake; the existing recommendation service continues to read only the separately validated, current, scope-matched approved rule registry.

Test fixtures are labeled `TEST_ONLY` and created only under temporary test paths. They never enter the real knowledge registry. The existing NISR SAS CSV and manifest were not rewritten; current integrity is rechecked by the existing knowledge validator. Intake is local and filesystem-backed, not a production multi-user service: CLI identities and role/qualification flags are operator attestations, not authenticated access control or qualification verification. There is no upload API, contributor login, browser review queue, malware scanner, encrypted object storage, replica backup, or institution integration. PDF/DOCX/TXT are not semantically extracted. Before production use, implement authentication-backed permissions and qualification verification, independent review audit, secure storage/backup/restore, retention policy, and malware scanning. Do not commit restricted source artifacts.

On 2026-10-22, `.\.venv\Scripts\python.exe -m utils.agronomy_knowledge --write-manifest --write-report` validated the committed inputs. A subsequent read-only `.\.venv\Scripts\python.exe -m utils.agronomy_knowledge` reported a current manifest: 5 sources, 4 statements, 0 agronomic rules, 0 approved rules, 0 review decisions, 6 open quality issues, and 2,020 checksum-matching NISR rows. The 12 legacy entries are provisional, and approved district coverage is 0/30.

Automated verification: `.\.venv\Scripts\python.exe tests\windows_safe_pytest.py` — 132 passed with one existing `PytestAssertRewriteWarning` for `anyio`. In `frontend`, `npm test -- --configLoader native --pool=threads --maxWorkers=1` — 35 passed; `npm run typecheck`, `npm run lint`, and `npm run build -- --configLoader native` — all passed. Tests include checksum and registry counts, draft-vs-approved gates, NISR/rule separation, approval evidence, district/season scope matching, expiry, duplicate IDs, and regression coverage for provisional recommendation output. These automated checks do not constitute agronomist review or browser/farmer testing.
