# CropPulse Rwanda — Agricultural Evidence Governance, Phase 5

**Audit date:** 2026-10-28  
**Repository:** `C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda`  
**Outcome:** Phase 5 software safeguards implemented and locally verified; overall readiness remains **DEVELOPMENT ONLY**.

## 1. Executive summary

The current repository contains five source records, four source statements, six open quality issues, and **zero agronomic rules and zero review decisions**. The NISR SAS dataset is integrity-checked historical district context. It is not crop-suitability evidence. No real agronomic rule was added, approved, or promoted.

The main confirmed software risk was that editable `review_decisions.json` fields, including `qualification_verified: true`, could satisfy the local approval check. The project has no authenticated reviewer identity provider, qualification registry, or signed approval trust anchor. The recommender could therefore treat operator-authored local attestations as qualification verification if a rule and decision were added to the registry. The farmer-facing approval path now fails closed: a locally declared approval is invalid and is never served. Coverage counts effective approved rules separately from declarations and remains zero until a trusted approval mechanism is implemented.

The validator now rejects malformed provenance, dates, rule fields, threshold values/units, missing references, modified registered artifacts, stale manifests, revoked decisions, and conflicting approved versions. It recognizes withdrawn and superseded lifecycle states. Existing React wording and Streamlit crop-plan disclosures already describe their output as provisional; tests now cover the shared semantic boundary. Weather-alert rules remain empty, and crop-health screening remains experimental and non-diagnostic.

These changes improve software controls and transparency. They do not establish agricultural correctness, professional qualifications, institutional approval, reuse rights, hosting safety, or production readiness.

## 2. Repository baseline and pre-existing state

- `git` was unavailable and `.git` was absent in the inspected project root. A clean Git status or complete baseline diff could not be established. The report therefore does not claim all repository modifications originated in this phase.
- Current agronomic files, Phase 3/4 reports, recommender, API route, React presentation/test, Streamlit plan builder, weather rules, crop-health guidance, intake code/docs, and their relevant tests were inspected.
- The agronomic pack validated before changes as current, with zero rules/decisions, six open issues, and NISR structural/hash validation. The owner-designated local database was not opened or queried during this phase.
- No application process was started, stopped, or contacted. Automated API tests use isolated test fixtures.

## 3. Evidence-to-recommendation data path

```text
Source registry + source statements + optional source artifact hashes
                         │
                         ├── Local evidence intake packages
                         │   (separate store; not consumed by farmer recommender)
                         │
                         └── rules.json + review_decisions.json
                                  │
                     agronomy_knowledge.validate_pack()
                                  │
                     approved_rules_for() / scoped matcher
                                  │
             recommender.recommend() ── NISR history loader
                    │                         │
                    └── FastAPI POST /v1/crop-planning/recommendations
                                      │
                               React crop comparison
```

The NISR loader contributes descriptive historical data only; `utils/recommender.py` records `statistics_used_for_ranking: false`. The React API route calls that shared recommender and labels the ranking method provisional. React renders the API status, reasons, risks, and evidence limitations.

Streamlit's crop plan is a distinct path: `product_pages.crop_plan_page()` calls `utils.seasonal_plan.build_plan()`, which uses the provisional `knowledge.py` table to prepare planning prompts and estimated ranges. It does not use the approved-rule registry or call the React recommendation endpoint. Its plan evidence is marked provisional and not locally verified. Current farmer-facing labels are consistent about uncertainty, but the two clients do not share one recommendation implementation. Consolidating them would require a separately reviewed product/API change.

`utils.agronomy_intake` stores versioned packages with integrity checks and an append-only event hash chain. Its documentation and tests confirm those packages are not automatically promoted into `rules.json` and are not read by the farmer recommender. Intake actor roles and qualification flags remain local operator attestations, not authenticated identity or professional qualification.

## 4. Findings and severity

### Fixed in this phase

- **High — local approval attestation could be mistaken for verified qualification.** `qualification_verified: true` in a local editable JSON decision was accepted by the prior registry validator. No signed/authenticated trust anchor existed. The validator now blocks every declared approved rule while that trust anchor is unconfigured; it emits `approval_identity_unverifiable`, reports zero effective approved rules, and the farmer matcher returns no guidance. A source hash or current manifest cannot grant approval.
- **High — stale manifest did not stop approved-rule serving.** A stale agronomy manifest now makes validation fail; the matcher requires a valid, current manifest before considering guidance.
- **Medium — weak shape and threshold checks.** Rule/source/review/issue records now receive stricter manual field/type checks. Invalid dates, unknown fields, malformed operators/values, unsupported threshold units, missing local content, and checksum mismatches are rejected. Numeric threshold comparisons require a supported explicit unit; unknown values fail closed at applicability time.
- **Medium — lifecycle/version ambiguity.** Withdrawn and superseded states are recognized and are not active. Later non-approval decisions block an earlier approval claim; duplicate/conflicting active versions are reported. Missing source/rule references and malformed local source files are rejected.

### Still open or intentionally blocked

- **Critical readiness dependency — qualified local evidence is absent.** No approved rules or trusted qualification-verification process exists. Farmer guidance must remain provisional; this is the intended safe state.
- **High — review identities are not authenticated.** The local intake CLI and JSON registry cannot prove who submitted, reviewed, or approved a package or whether qualifications are genuine. Distinct local actor strings and hash chains are not cryptographic identity proof.
- **High — external rights and specialist decisions remain unresolved.** RAB/RwaSIS, METEO RWANDA, NISR, Open-Meteo, and PlantVillage/model reuse conditions require product-specific legal/organizational review. No new source was downloaded or treated as approval.
- **Medium — separate Streamlit planning implementation.** It is explicitly provisional and has a regression test, but its prompt builder is not the same engine as React/API and does not render the registry's scoped approved-rule status. Since no approved rules exist, no contradictory verified status is currently presented.
- **Medium — no authenticated browser workflow or production runtime was available.** Automated tests and mocked React requests are not browser, hosted, or live-provider verification.

## 5. Approval and lifecycle before and after

**Before:** a rule with `status: approved`, `review_status: approved_for_scope`, current dates, a citation, and a separate decision object containing `reviewer_role: qualified_local_agronomist` plus `qualification_verified: true` could pass the local check. Those fields were editable and did not authenticate the reviewer or qualification. Intake transitions enforced scope and distinct actor IDs, but were also a local operator workflow and did not authenticate qualifications.

**After:** local JSON review fields remain audit assertions only. Because no authenticated trust anchor is configured, a declared approved rule produces a validation error, is not included in active coverage, and cannot be returned by `approved_rules_for()` or `farmer_facing_guidance_for()`. Manifest hashes are integrity checks, not approval signatures. The application does not fabricate a reviewer identity system. Draft, evidence-collected, technical-review, local-specialist-review, approved, rejected, expired, withdrawn, superseded, and quarantined states remain distinguishable; only the active approval path is currently disabled.

No production rules or review decisions were populated. `rules.json` and `review_decisions.json` remain empty. Synthetic approval scenarios exist only in temporary `TEST_ONLY` test fixtures.

## 6. Source, manifest, and registry integrity

- The validator checks source IDs/URLs/provenance fields, optional ISO publication/access dates, optional repository-relative artifact paths and hashes, rule/source references, NISR registry checksum agreement, and the agronomic manifest.
- A stale manifest is now an error. The `--write-manifest` operator command can refresh the derived manifest only when the stale-manifest finding is the sole blocking error; it does not override malformed records or approval failures.
- The revised JSON schema now describes strict rule conditions, supported threshold units, review states, source records, statements, review decisions, and quality issues. Runtime checks are implemented in `utils/agronomy_knowledge.py`; this project does not add a separate JSON Schema runtime dependency.
- The existing NISR CSV SHA-256 remains `98de5073d00f60231df496da3c19912834a3156a7f2f044bd6eaa5108f313927` and matches its unchanged `data/verified/MANIFEST.json` entry. The CSV remains 2,020 historical rows; no observation is converted into a rule.
- The agronomy `MANIFEST.json` and `validation_report.json` were intentionally regenerated after changing the agronomy schema and validator's declared/effective approval count. Those generated files are derived validation outputs, not source evidence.

## 7. Recommendation trust boundaries and farmer-facing behavior

The recommender itself already describes its broad crop-zone categories, months, water categories, and elevation ranges as provisional. It does not use NISR records to rank crops, create a success probability, or claim farm-level validation. Its `evidence_record` carries provisional status, source limitations, and an empty `approved_guidance` list for the current registry. The API test now asserts those exact fields and that a status label says `Provisional guide fit`.

React already displays the API status, reasons, risks/unknowns, and a details section stating that no approved source-backed scoped rule is loaded and NISR is historical context only. Its mocked-fetch test was corrected to use the real provisional status wording and now asserts it is displayed. No React product component change was needed.

Streamlit's crop-plan content already sets `verification_status` and `evidence_status` to provisional, has no reviewed date, and includes cautions about local conditions, diagnosis, and pesticide rates. A new test covers those status and warning fields. No Streamlit product code change was needed.

## 8. Weather and crop-health boundaries

- `utils/weather_alert_rules.py` still contains no approved alert rules. API responses state that preferences do not create or schedule alerts. Existing alert tests verify the empty active-rule set; no threshold or alert was invented.
- Weather forecast prompts are not official warnings, field observations, or crop-specific approved rules.
- Crop-health screening remains experimental and maize-only. Existing API/UI/guidance describe model results as candidates, not diagnoses; the model does not create treatment dosages, medicines, or pesticide schedules. Existing crop-health API and guidance tests were rerun.
- Those paths remain separate from the agronomic rule registry. No weather, crop-health, or disease record was promoted as an agronomic rule.

## 9. Files changed

- `utils/agronomy_knowledge.py` — stricter provenance/rule/lifecycle validation; stale-manifest blocking; local approval trust gate; effective versus declared counts; supported threshold-unit checks and fail-closed scoped lookup.
- `data/agronomy/schema.json` — stricter record and condition definitions, explicit review states, supported units, and closed object shapes.
- `data/agronomy/MANIFEST.json` — regenerated derived hashes/count metadata after the schema change.
- `data/agronomy/validation_report.json` — regenerated current report; pack valid, zero rules/approvals, six open issues.
- `tests/test_agronomy_knowledge.py` — regression cases for local self-attested approval, invalid dates/fields/units, source absence/tampering, stale manifest, revocation, scope, and version conflict.
- `tests/test_seasonal_plan.py` — new TEST_ONLY-free assertion test of the Streamlit plan's existing provisional status and safety warnings; it creates no records.
- `tests/test_backend_api.py` — asserts API recommendations expose provisional status and no approved guidance.
- `frontend/src/App.test.tsx` — uses the API's real provisional status label and asserts it appears in the React crop comparison.
- `docs/agricultural-evidence-governance-phase-5.md` — this report.
- `README.md` — link to this report.

No changes were made to `utils/recommender.py`, API routes/schemas, Streamlit product logic, alert rules, crop-health model or guidance, intake transition behavior, account data, migrations, or deployment configuration because the existing farmer paths already presented the relevant safety limits and no confirmed defect required those changes.

## 10. Verification performed

Commands ran from the project root unless stated otherwise.

| Command/check | Result |
|---|---|
| `Get-Command git`; `Test-Path .git` | Git unavailable; `.git` absent in this project root. Pre-existing working-state attribution remains unknown. |
| `\.venv\Scripts\python.exe tests\windows_safe_pytest.py tests\test_agronomy_knowledge.py tests\test_agronomy_intake.py tests\test_recommender.py tests\test_weather_alert_rules.py tests\test_crop_health_guidance.py tests\test_backend_api.py tests\test_crop_health_api.py tests\test_seasonal_plan.py` | **84 passed** in the focused cross-path run; one same warning. |
| `\.venv\Scripts\python.exe tests\windows_safe_pytest.py` | First full run: **180 passed, 1 failed** in the existing private-messaging unread-order assertion. The exact test then passed alone (**1 passed**), and the subsequent full rerun passed **181 tests**, one AnyIO warning, 61.27 seconds. The intermittent timestamp/tie-order cause is not confirmed; no messaging code or assertion was changed. Migrations/writes used temporary isolated test databases only. |
| In `frontend`: `npm.cmd test -- --configLoader native --pool=threads --maxWorkers=1 --testTimeout=30000` | **48 passed across 6 files**. Vitest emitted a non-failing `Not implemented: navigation to another Document` diagnostic. |
| In `frontend`: `npm.cmd run typecheck` | Passed. |
| In `frontend`: `npm.cmd run lint` | Passed. |
| In `frontend`: `npx.cmd vite build --configLoader native --outDir ..\.test-runtime\phase5-20261028-build --emptyOutDir false` | Passed; 2,517 modules transformed. Output went to a separate test directory; existing `frontend/dist` was not targeted. |
| `\.venv\Scripts\python.exe -m utils.agronomy_knowledge --write-manifest --write-report` | Passed; pack valid/current, zero rules, zero approved rules, zero review decisions, six open issues, 2,020 NISR rows. This wrote only derived agronomy manifest/report files listed above. |
| NISR file SHA-256 compared with `data/verified/MANIFEST.json` | Match; CSV and verified-data manifest unchanged. |
| Browser E2E, live API/provider, authenticated reviewer qualification, hosted data-rights checks | Not performed. No browser/runtime/provider access was used to imply those results. |

The successful full rerun includes the new Streamlit and API assertions and all application test files. The intermittent messaging assertion is recorded as unresolved test evidence rather than hidden or attributed to the agronomy change.

## 11. Data preservation

- `data/verified/nisr_sas_2023_2026.csv` is unchanged and still matches its existing checksum.
- `data/verified/MANIFEST.json` is unchanged.
- `data/agronomy/rules.json` remains empty (SHA-256 `619f664181af91448a0070c2dc4febe6e5c497183bbab82fb09da003b5116b1d`); `review_decisions.json` remains empty (SHA-256 `5bc0f737622f40ac572fec99ec54829ac0747fa444dc764a9dd490f120da5ff4`).
- No application database was opened, written, migrated, or replaced. The Phase 4 diagnostic's previously recorded development database metadata remained unchanged in the final metadata check.
- Source PDFs, model/dataset artifacts, existing intake packages, farmer records, crop plans, messages, and earlier audit reports were not modified by these changes. Automated intake tests used temporary roots; the full suite's synthetic database files were isolated under `.test-runtime` and retained.
- Only the agronomy JSON schema and its derived manifest/validation report were changed among evidence-registry data files. These outputs now describe the strengthened validation policy; no agricultural evidence or approval was fabricated.

## 12. Remaining dependencies and Phase 6 checklist

1. Obtain actual crop/variety/season/location/condition-specific source material with permitted use, exact locators, units, dates, uncertainty, and limitations. Do not derive suitability from NISR yield observations.
2. Establish an authenticated reviewer identity and independently verified qualification process, a protected decision store or cryptographic trust anchor, role separation, audit, withdrawal, and appeal/review controls before enabling any rule. Keep the current hard gate until then.
3. Have qualified Rwanda specialists review source-backed rules for exact scope and approve them through that trusted process. Test expiry, withdrawal, conflict, district/province mismatch, variety mismatch, and missing-condition cases before rule publication.
4. Resolve institutional reuse/licensing and attribution for NISR, METEO RWANDA, RwaSIS, Open-Meteo, and PlantVillage/model artifacts for the intended service and commercial status.
5. Obtain organizational/legal decisions for farmer notice/consent, retention, deletion/export, data residency, access support, incident response, and data-controller responsibilities.
6. Verify intended runtime/database identity, protected backups and isolated restore, HTTPS/CORS/secrets, rate/concurrency controls, monitoring, SMTP, and rollback in controlled staging.
7. Run authenticated browser workflows for farmer, reviewer, and admin roles against isolated test data, including cross-user/district denial, saved plan persistence, session/CSRF behavior, weather failure states, messaging, crop-health follow-up, desktop/mobile, and Kinyarwanda review.
8. Decide whether Streamlit's separate planning builder should call a shared recommendation service before any approved guidance is enabled, so clients cannot drift in rule applicability or evidence status.

**Phase 6 can safely begin as a planning/design phase for authenticated evidence review and source acquisition. It cannot safely begin rule activation, external-user contribution, or a farmer pilot until the trust, source-rights, runtime, privacy, and specialist-review prerequisites above are satisfied.**

## 13. Final readiness verdict

**Phase 5 local software safeguards: COMPLETE. Overall CropPulse readiness: DEVELOPMENT ONLY.** The registry remains valid with no active agronomic guidance. The approval hard gate prevents local JSON attestation from representing a verified qualification. Tests establish software checks only; they do not validate agricultural advice, reviewer credentials, licenses, privacy compliance, hosted security, or field performance.
