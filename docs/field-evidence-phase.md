# Field records and crop-plan evidence

## Current workflow

Sign in to the React workspace and open **My farms**. Select one of your farms, add a named field, and optionally record its area in hectares and a latitude/longitude pair. Coordinates are entered by the farmer and checked against the rectangular extent of the NISR District Boundary 2022 layer; this is only a coarse out-of-country input guard and does not verify district boundaries or field position. A district and sector are inherited as farm context, not treated as a surveyed field boundary. Field area, coordinates, and soil properties may remain unknown.

When creating a crop plan, select an active field or leave **Field** at **Farm-level plan**. Existing plans remain farm-level after migration. Archiving a field removes it from new plan choices while retaining the field record and links in existing plans. The existing crop-plan status workflow is unchanged.

## Storage and provenance

Migration `0007_fields_and_evidence` adds `farm_fields`, nullable `crop_plans.field_id`, and `crop_plan_evidence`. Fields cascade with their owning farm. Deleting a field sets a linked plan's field to null; archiving retains links. Evidence snapshots are plan-linked and have fields for claim, crop and geographic applicability, source organization/name/URL/identifier, publication/retrieval dates, evidence period, units, confidence, limitations, dataset/recommender version, generation timestamp, and verification status.

The React farm workflow calls the FastAPI crop-planning recommendation endpoint; it does not call the Streamlit recommender. A farmer can compare those provisional results and save a selected result’s recommendation context with a plan. That context is not an independently verified evidence snapshot, and the API evidence list can remain empty. CropPulse-compiled guidance remains unverified. No soil measurements, field boundaries, recommendation confidence, or source records are fabricated. Independently sourced evidence ingestion remains planned until traceable, versioned agronomic evidence is available.

## Farmer-reported harvest and water records

Harvest outcomes are stored separately from crop plans. Post-harvest observations are linked to a harvest and do not change its quantity or the plan lifecycle. Missing quantities remain absent, an explicitly recorded zero remains zero, and comparison is limited to quantities that use the same unit.

The **Irrigation and water-management log** stores a farmer-reported event under its farm, with optional links to a field and crop plan. Water-source values are rainwater, river, lake, pond/reservoir, well/borehole, piped supply, irrigation scheme, Other (with a description), or Unknown. Method values are Unknown, manual watering, watering can, hose, sprinkler, drip, furrow, basin, or Other (with a description). Optional water volume uses L or m³; optional duration uses minutes or hours. Each amount is stored only with its explicit unit; CropPulse does not convert amounts, infer water adequacy, create schedules, or provide water prescriptions. Unknown is the default and a record can be saved with no quantity or duration.

Migration `0018_irrigation_records` adds a separate event table after harvest and post-harvest migrations `0016` and `0017`. Server-side authorization checks farm ownership and verifies any linked field or crop plan belongs to the same farm. A field-specific crop plan must match the selected field. Entries are editable as farmer-reported records; no agronomic interpretation or crop-plan lifecycle transition is triggered.

## Farmer-reported soil observations and soil-test records

The React farm workspace has separate persistent logs for visible farmer soil observations and for values a farmer enters from a soil-test report. Both are linked to the authenticated farmer's farm and may optionally reference a field on that same farm. An observation can include a date, farmer-described soil type, drainage or erosion observations, practices, and notes. A soil-test record can include an optional pH on the conventional unitless 0–14 scale, optional reported nitrogen/phosphorus/potassium values with explicit units (`mg/kg`, `g/kg`, `cmol/kg`, or `%`), optional organic matter with `g/kg` or `%`, and optional lab/provider, report-reference, source, and notes fields. Incomplete records are allowed; blank measurements remain null and are not treated as zero.

All soil entries are marked `farmer_reported`. A provider or laboratory name is farmer-entered and does not verify the source or report. Values are stored as entered, with no unit conversion, thresholds, soil-health diagnosis, fertilizer rates, product recommendations, or district-specific claims. No soil dataset, laboratory integration, or approved soil agronomy rules are assumed by this feature.

Migration `0019_soil_records` adds `soil_observations` and `soil_test_records` with nullable field links, ownership-scoped farm links, indexes, unit/value pairing, and pH range checks. Its upgrade/downgrade and preservation behavior are tested only on disposable SQLite databases. Apply schema upgrades only after the configured database has been identified and backed up; never run migration tests against the farmer database.

## Read-only farm activity timeline

The React farm workspace includes a unified timeline backed by `GET /v1/farms/{farm_id}/timeline`. It assembles existing crop-plan creation timestamps, recorded actual planting dates, dated farm activity entries, irrigation events, soil observations and soil-test records, harvests, and post-harvest observations. It writes no records and has no database migration. Every request verifies that the authenticated farmer owns the requested farm; field names are resolved only from that farm's fields. Results are bounded to 300 by default (up to 500) and indicate when more recent entries are being shown.

Timeline ordering is newest stored event date first; entries with no stored date, if legacy/corrupt data produces one, sort last and display “Date not recorded.” Required date fields are shown as stored. A crop plan's creation entry uses its stored `created_at`; a separate planting entry appears only when `actual_planting_date` exists. Other status transitions such as monitoring/completed have no dated history in the current schema and are not assigned inferred dates. Farmer activity and observation records are labeled farmer-reported; crop plan creation is labeled provisional. Timeline entries link to the existing farm-workspace sections rather than duplicating or mutating source records. A missing timeline item does not imply the activity did not occur.

## Field decision-support summary

Phase 21 adds a read-only, farmer-selected whole-farm or field summary in the React workspace. It reuses the owner-scoped plans, irrigation, soil observation, soil-test, harvest, timeline, and saved-forecast APIs. Field summaries include records only when a stored field link matches; farm-level records are not silently attributed to a field. The view is a convenience summary of existing records, not an agronomic recommendation engine. See [Phase 21 implementation and verification](field-decision-support-summary-phase-21.md).

The summary distinguishes provisional crop plans, farmer-reported observations/transcriptions/harvests, and external weather model forecasts. It does not infer a missing event or measurement, combine unlike units, assess crop suitability, or prescribe fertilizer/irrigation. Weather forecasts remain forecasts, not field observations. The saved forecast API returns a bounded latest list, so absence from the summary is not proof that no older forecast exists.

## Setup and limitations

Back up the configured database before applying schema upgrades, then run:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

The repository's current Alembic head is `0019_soil_records`. Production databases are not upgraded by this local development step. Test migrations against a disposable SQLite database and separately validate the configured production database, backup recovery, and PostgreSQL compatibility before deployment.

Geographic coverage is national at the farm administrative-name level using the existing 30-district NISR metadata reference. Individual farmer-entered locations are not independently verified; this is not nationwide field-boundary coverage. There is no trusted soil source connected to the field model. Agronomic recommendations and evidence ingestion remain outside this phase.
