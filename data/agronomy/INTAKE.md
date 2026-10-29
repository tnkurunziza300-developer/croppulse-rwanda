# Agronomic evidence intake (local operator workflow)

The intake registry stores immutable versioned packages under `data/agronomy/intake/records/`. Each package contains provenance metadata, the original file when retention permission explicitly allows it, a SHA-256 checksum, a structural validation report, and append-only lifecycle events with a SHA-256 hash chain. The initial event binds both metadata and the validation report; reads and lifecycle transitions check those hashes, the event sequence, and archived-file checksum. Submitter, technical reviewer, specialist reviewer, approver, and activating administrator must be distinct identities. This is tamper-evident against accidental edits, not signed proof against an operator who can rewrite the whole local directory. A new version gets a separate package; existing versions are never overwritten. This store is separate from NISR statistics, weather data, the reviewed agronomic rule registry, and farm-private records.

## Intake metadata

Create a UTF-8 JSON file with these fields. Unknown values must remain explicit (for example, `[]`, `null`, or `"unknown"`); do not guess them.

```json
{
  "dataset_id": "institution.dataset-name",
  "version": "publisher-version-or-received-version",
  "record_kind": "historical_statistics | agronomic_guidance | official_document | weather_climate | unverified_submission",
  "source_organization": "publisher or contributing organization",
  "source_identity": "specific document/dataset identity or permitted source reference",
  "title": "original title",
  "publication_date": null,
  "received_date": "YYYY-MM-DD",
  "data_owner": "owner when provided",
  "source_contact_or_provenance": "legitimately provided contact/provenance or explicit unknown",
  "permission_status": "retain_original | metadata_only | unknown | prohibited",
  "license_status": "open | restricted | unknown | prohibited",
  "preservation_reference": null,
  "format": "csv | json | pdf | docx | txt",
  "geographic_scope": [],
  "crops": [],
  "varieties": [],
  "seasons": [],
  "soil_scope": [],
  "production_systems": [],
  "original_units": [],
  "transformations": [],
  "limitations": [],
  "source_locators": [],
  "geography_type": "national | province | district | sector | site | unknown",
  "guidance_categories": [],
  "conditions": [],
  "effective_from": null,
  "revalidate_by": null,
  "supersedes": null,
  "submitter_id": "operator identity",
  "submitter_role": "authorized contributor role"
}
```

`retain_original` copies the byte-identical artifact into the record. Otherwise the artifact is not copied and a permitted `preservation_reference` is required. The checksum is still calculated from the submitted file, so the operator must handle that temporary file consistently with its access restrictions. Never upload private or restricted material into a repository unless its terms allow it.

## Commands

Run from the repository root with the project virtual environment:

```powershell
\.venv\Scripts\python.exe -m utils.agronomy_intake receive --file .\incoming\source.csv --metadata .\incoming\metadata.json
\.venv\Scripts\python.exe -m utils.agronomy_intake list
\.venv\Scripts\python.exe -m utils.agronomy_intake coverage
\.venv\Scripts\python.exe -m utils.agronomy_intake transition --id <submission-id> --state validation --actor-id <operator-id> --actor-role admin --rationale "Structural checks reviewed"
```

Transitions then proceed separately through `technical_review`, `specialist_review`, `approved`, and `active`; rejection, quarantine, expiry, and supersession are recorded as distinct states. Transition events require an actor, role, timestamp and rationale. The submitter cannot review their own package. Approval requires separate specialist identities, explicit crop/geography/category/season scope, source locators, effective and revalidation dates, and known permission/licensing. Only an `agronomic_guidance` package may be approved as guidance. Superseded versions remain stored and can be reactivated only through an explicit administrator rollback event. The `coverage` command counts only integrity-valid, active, in-date agronomic guidance and lists district gaps; it never counts pending records, statistics, weather, or ordinary documents.

## Important operational boundary

This phase is a **local, operator-run intake foundation**. It has no public upload endpoint, contributor login, qualification registry, identity provider, malware scanner, external immutable object store, backup replication, or browser review queue. The `actor_role` and `qualification_verified` CLI fields are operator attestations, not cryptographic proof or account authorization. Restrict repository and intake-directory access at the operating-system/deployment level; a production multi-user workflow requires authentication-backed roles, verified organization/qualification records, independent approval, storage encryption, backup/restore tests, and an authorized retention policy. Do not claim authenticated specialist approval based on this CLI alone.

CSV is parsed row by row with consistent header/row widths; JSON has a 5 MiB cap, duplicate-key rejection, and root/encoding checks. All files have a 25 MiB cap. PDF gets a header/version and EOF-envelope check but is not fully parsed. DOCX central-directory entries are bounded before archive listing, ZIP64 is rejected, paths are checked, member CRCs are verified by bounded streaming, and expanded size is capped at 50 MiB (with a per-member compression-ratio limit). TXT is UTF-8 checked. These are safety/structure checks, not malware scanning or proof of publisher authenticity, scientific correctness, completeness, lawful reuse, or suitability for Rwanda. No automated document values are converted into recommendations. Intake packages are **not read by the farmer recommender**. Promoting an approved, scoped rule remains a deliberate, reviewed change to `data/agronomy/rules.json` and `review_decisions.json`, followed by registry validation and manifest regeneration. The registry matcher fails closed for variety-specific rules without an exact variety and condition-specific rules without matching context. NISR and weather records remain in their separate pipelines.

The local folder is not by itself a production durability guarantee. Back it up using an approved storage policy, verify restore, restrict access, and keep restricted originals outside source control unless permission expressly allows committing them.
