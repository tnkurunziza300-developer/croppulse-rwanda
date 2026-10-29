# Agronomic Evidence Issues and Rule Review Workflow — Phase 24

**Date:** 2026-10-29  
**Status:** Development only. This workflow does not establish reviewer qualifications or activate agricultural recommendations.

## Verified starting state

- Alembic was at `0019_soil_records` before this change; the NISR file was 2,020 rows with SHA-256 `98de5073d00f60231df496da3c19912834a3156a7f2f044bd6eaa5108f313927`, matching the verified-data manifest.
- The registry held zero rules and zero decisions, six open quality issues, and no configured approval trust anchor.
- No verified source, permission, local agronomist decision, field evaluation, or browser workflow was inferred from the prior phase reports.

## Six issue dispositions

| ID | Current disposition | Classification and evidence needed |
|---|---|---|
| AGQ-0001 | **Open** | Requires crop-specific authoritative sources, atomic claim scope, and qualified Rwanda agronomist review. Existing provisional CropPulse claims are not promoted. |
| AGQ-0002 | **Open** | Requires authorized access to RwaSIS or a publisher-provided extract, with definitions, coverage, units, provenance, and applicable access conditions. |
| AGQ-0003 | **Open** | Requires source-specific permission/terms from RAB and METEO RWANDA for storage, derived values, and redistribution in the intended service. |
| AGQ-0004 | **Open** | Requires dated confirmation from RAB or another authoritative current source; the 2024 launch announcement is not current-status evidence. |
| AGQ-0005 | **Resolved** | Recommender regression tests establish that NISR context does not affect rank and a generic `validated` state is insufficient to claim NISR provenance. Farmer comparison exposes source, period, retrieval date, units, and limitations. The quality-issue schema now requires dated resolution evidence. |
| AGQ-0006 | **Open** | Requires actual scoped approved evidence and review coverage. National availability of the application is not national agronomic validation; district, crop, season, variety, soils, and production systems remain uncovered. |

The registry currently has **five open issues**, **zero rules**, and **zero approved rules**. AGQ-0005 closure is a code-boundary resolution only; it does not validate agricultural claims or source estimates.

## Rule proposal and review workflow

Migration `0020_agronomy_review_workflow` adds three tables: append-only reviewer authorization events, immutable versioned proposals, and append-only decisions. It does not modify farmer records or the existing agronomic rules registry.

An administrator explicitly grants or revokes agronomy-review access for an active account whose existing role is reviewer or administrator. No account receives this permission by default. Each authorization change stores its actor, time, reason, and action and also appears in the admin audit log. Every proposal and decision request rechecks account status, role, and the latest authorization event.

Authorized reviewers can create a proposal with a stable rule ID/version, topic/category, claim, geographic and seasonal scope, units, assumptions, limitations, uncertainty, and source references. A revision is a new proposal version linked to its predecessor. Decision requests accept only the decision and rationale; reviewer identity comes from the authenticated session. Proposers cannot decide their own proposal. Approval requires source citation metadata with a version/date, defined geography and season, units, assumptions, limitations, and uncertainty. A terminal decision cannot be edited; subsequent changes require a new revision. Rejected, withdrawn, and superseded proposals remain in history.

The System Health admin dashboard now supports explicit reviewer authorization and revocation. Proposal creation, listing, and decisions are exposed by authenticated API routes (`/v1/agronomy/rule-proposals`); no specialist credentials or external identity are captured or claimed. API authorization is not professional qualification.

An API decision of `approved` records an internal review workflow outcome only. `guidance_activation` remains false, and the recommender still reads only the separately controlled versioned knowledge pack. `APPROVAL_TRUST_ANCHOR_CONFIGURED` remains false; no database proposal, metadata, hash, or passing test can activate farmer guidance. The authorization workflow must not be mistaken for specialist certification or a public-ready approval system.

## Safety and evidence boundary

- NISR remains historical district context. Structural checks verify local file integrity and format, not survey estimates or suitability for a field.
- Farmer-reported soil and irrigation entries remain unverified. Missing values remain unknown.
- Weather forecasts remain forecasts; no active approved weather-alert rules or automatic agricultural alerts were added.
- No soil/yield thresholds, fertilizer rates, irrigation schedules, disease treatments, or example agronomic rules were added.
- Source permissions, reviewer qualifications, local field validation, privacy/retention decisions, security operations, browser QA, and recovery verification remain unresolved release prerequisites.

## Database and migration boundary

The migration is additive and tested by upgrading and downgrading a disposable SQLite database from `0019` while preserving existing farmer and farm-feature tables/records. The real application database was not connected to, migrated, seeded, or modified. No deployment or browser test occurred. PostgreSQL compatibility is not claimed.
