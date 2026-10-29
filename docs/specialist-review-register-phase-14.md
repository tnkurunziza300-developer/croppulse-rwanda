# CropPulse Rwanda — Specialist Review Register, Phase 14

**Prepared:** 2026-10-28  
**Review status for every item:** **PENDING — no external review or approval recorded.**  
**Product status:** **DEVELOPMENT ONLY.** This register is a work queue, not an approval record.

## 1. How to use this register

The entries identify existing CropPulse claims or outputs that require a qualified Rwanda-based agricultural specialist’s review. They intentionally contain no agronomic thresholds or newly authored recommendations. Scope fields are placeholders to be completed from the evidence and the intended product claim, not filled by assumption.

The current internal knowledge pack is `knowledge.py`; claim behavior is implemented in `utils/recommender.py` and `utils/seasonal_plan.py`. The pack has 12 legacy entries, while `data/agronomy/rules.json` and `data/agronomy/review_decisions.json` contain zero rules and decisions. See the [Phase 14 evidence inventory](agronomic-evidence-inventory-phase-14.md) for source-by-source limits and the six open quality issues.

## 2. Candidate review topics

Each topic must be split into claim-level, crop-specific review records before any decision. “Pending” means no decision; it does not mean conditionally approved.

| ID / claim family | Current claim or decision needing review; source paths | Intended scope to specify | Current evidence and limitation | Risk if wrong | Required review questions and decision criteria | Status |
|---|---|---|---|---|---|---|
| R14-01 — crop ranking and broad-zone fit | The recommender ranks crops using the internal broad-zone fit and season entries. `knowledge.py`; `utils/recommender.py`; React crop comparison. | Crop and variety; season; named district/site and mapping resolution; farmer system; soil and water context; whether claim is ranking, fit label, or omission. | CropPulse-authored categories; no rule-level citation or approved local decision. NISR is historical aggregate context only. | Farmer may choose a poorly suited crop or misread sort order as validated likelihood. | Is the specific claim supported for the stated scope by current, traceable evidence? Are category labels and omitted/unknown cases clear? Accept only when evidence supports the exact scope, method is reproducible, limits and abstention behavior are explicit, and independent review agrees. Reject or narrow if support is absent, contradictory, stale, or broader than evidence. | **PENDING** |
| R14-02 — season entries and planting calendar | Existing crop/season entries and planting-month/calendar displays. `knowledge.py`; `utils/seasonal_plan.py`; planting calendar UI. | Crop and variety; season/year; district/site; planting system; relevant environmental conditions; whether display is a typical window or an instruction. | Internal approximate entries without claim-level citations; no weather-based timing validation. | Mistimed planting can cause missed rainfall window, input loss, or misleading expectations. | What source defines the stated timing, issue/revision, and geographic/season scope? Is it a range, locally conditional, and subject to forecast/extension confirmation? Accept only a sourced and bounded statement with uncertainty; reject exact instruction unsupported by evidence. | **PENDING** |
| R14-03 — elevation handling | Current provisional altitude range/fit fields and recommender’s handling of supplied elevation. `knowledge.py`; `utils/recommender.py`. | Crop/variety; elevation measurement method; site/district; season; local temperature, rainfall, and other stated conditions. | Internal ranges are unverified; district alone does not identify farm elevation or conditions. | Unsupported exclusion can hide options; unsupported inclusion can imply suitability. | Is elevation relevant and supported for this crop and scope? What measurement and uncertainty are appropriate? Does missing elevation abstain instead of silently implying fit? Accept only if provenance, scope, uncertainty, and missing-data behavior are documented; reject unsupported cutoffs or exclusion claims. | **PENDING** |
| R14-04 — water requirement / water fit | Qualitative water labels and associated fit behavior. `knowledge.py`; `utils/recommender.py`. | Crop/variety; production system; season; rainfall/irrigation source and reliability; soil/water conditions. | Internal qualitative labels; no verified local measurement or rule citation. Forecasts are not observed farm water availability. | Crop failure, water stress, or unsuitable irrigation burden. | What does each label mean operationally and what evidence supports it in this scope? How should missing water information be represented? Accept only with defined terms, sourced context, uncertainty and safe unknown handling; reject any inferred local sufficiency without supporting evidence. | **PENDING** |
| R14-05 — seed quantities and plan resource estimates | Seed quantity inputs and derived resource prompts in seasonal plan. `knowledge.py`; `utils/seasonal_plan.py`. | Crop/variety; planting method and spacing/system; area unit; seed quality assumptions; intended output (estimate vs instruction). | Internal values flow into a derived plan; no claim-level sources, local validation, or verified variety/planting assumptions. | Over/under-purchase, financial loss, poor stand, or false precision. | Are units, assumptions, and calculation auditable? Does output label an estimate and handle unknown area/variety/system safely? Accept only with source-backed assumptions and checks reproducible from stated inputs; reject unexplained precision or instruction-like output without support. | **PENDING** |
| R14-06 — duration, harvest window, and yield ranges | Internal crop duration/harvest and yield ranges surfaced by crop guide/planning outputs. `knowledge.py`; `utils/seasonal_plan.py`; relevant crop analytics. | Crop/variety; season; district/site; production system; management and measurement definition; range and confidence/uncertainty. | CropPulse-authored estimates without rule citations or independent Rwanda validation. NISR district production is not plot yield or causal evidence and lacks key conditions. | Misleading expectations, poor scheduling or economic decisions. | What exactly does the duration/yield measure, under which conditions and source population? Does output display uncertainty and avoid forecasting promises? Accept only if independently supported, scoped, defined, and uncertainty is visible; reject causal/profitability claims or ranges without provenance. | **PENDING** |
| R14-07 — crop-specific tips and agronomic reminders | Existing tips in crop entries, including any management, nutrient, pest, or disease statements. `knowledge.py`; any UI surface displaying them. | Crop/variety; district/site; season; system; specific condition and intended action. | Internal text may not have a source locator; no treatment or pesticide advice is authorized by this register. | Crop damage, unsafe/unlawful chemical use, unnecessary expenditure, or delayed expert support. | Is each statement evidence-backed and locally applicable? Does it imply diagnosis, a fertilizer rate, pesticide, treatment, or guaranteed result? Accept only bounded, sourced, non-ambiguous language within reviewer competence; reject unsupported prescriptions and route high-risk treatment topics to separate qualified review and applicable safety/legal review. | **PENDING** |

## 3. Minimum evidence package for an external decision

For each atomic claim, provide a versioned dossier containing:

1. Exact current UI/API claim and location, expected user interpretation, and proposed scope; do not ask reviewers to approve an entire crop pack at once.
2. Source title, publisher/author, stable URL or controlled copy, exact version/hash, issue/revision date, page/table/section locator, definitions, and permission/terms for the intended use.
3. Crop and variety, season, geographic level, farming system, relevant soil/environment/water conditions, and any exclusions. Unknown scope must be stated.
4. Every value and unit with its source and derivation; define threshold/range semantics, measurement method, uncertainty, confidence, applicability, and abstention behavior. Reviewers determine values; this template supplies none.
5. Relevant independent validation or field evidence: protocol, site and season, variety, management, sample definition, outcomes, missingness, and limitations. Do not treat historical district aggregates as local validation.
6. Conflicting evidence, known failure cases, safe fallback wording, revalidation date/trigger, and a change history linking the reviewed source version to the claim version.

## 4. Reviewer qualification and identity verification

The reviewer should have relevant agricultural training and current experience for the crop/topic and geographic scope, and authority to provide the requested review. Verify identity, institutional affiliation, qualifications, and authority independently through the issuing institution or an authoritative professional register/contact. Record only the minimum evidence needed: verifier, verification method, date, institution/contact or register reference, scope verified, and conflict-of-interest declaration. A reviewer-entered name, role, uploaded credential, or local `qualification_verified` field is an attestation, not independent verification.

No reviewer identity or qualification has been verified for Phase 14. Do not pre-fill names, credentials, signatures, institutions, or decisions.

## 5. Practical external-review workflow

This is a **proposed workflow**, not a capability claimed as implemented or tested.

1. **Assign ownership and scope.** Product owner identifies the exact claim, risk, intended audience, candidate scope, and a qualified independent reviewer. Separate related crop/season claims into reviewable items.
2. **Verify the reviewer.** Confirm legal identity, affiliation, relevant qualification and review authority directly with the issuing body/institution or authoritative register. Record minimal verification evidence and conflicts; do not rely on local JSON attestations.
3. **Freeze and share the dossier.** Create a static, versioned dossier with source hashes, locators, permission status, the current UI text, derivation, validation evidence, and known limitations. Give the reviewer only the scope being considered.
4. **Collect attributed comments.** Reviewer returns dated comments linked to item IDs and source passages, including uncertainties, unsupported claims, requested narrowing, and abstention cases. Preserve the original response and response version.
5. **Resolve evidence conflicts.** Product owner records each source/version and issue date, evaluates applicability and uncertainty with reviewer input, narrows scope or keeps the claim pending when conflict remains. Do not resolve disagreement by silently selecting a convenient threshold.
6. **Obtain an explicit decision.** Record approve, reject, or pending for each atomic claim, with rationale, exact scope, conditions, limitations, effective/review dates, reviewer identity-verification reference, and attributable signature or trusted external identity. Silence or a meeting note is not approval.
7. **Independent second review for high-risk claims.** Require a second qualified reviewer for claims that could materially affect crop choice, costly inputs, water, disease/pest response, or safety. Record disagreements and resolution.
8. **Revalidate and audit changes.** Recheck source hashes/versions, rule scope and dates, tests and no-evidence behavior. Maintain immutable decision/change/revocation history and an expiry or review trigger. A changed source or claim returns to review.
9. **Separate approval from activation.** External approval does not itself publish a rule. Future implementation must pass the configured trust-anchor and pack-validation process, with separate change control and release authorization. Phase 14 performs no activation.

### Current technical trust boundary

`utils/agronomy_knowledge.py` has `APPROVAL_TRUST_ANCHOR_CONFIGURED=False`. The validator blocks approval that relies only on editable local files. A local `reviewer_id`, role, or `qualification_verified: true` field cannot authenticate the person, establish professional qualification, or prove authority. Do not weaken this requirement or write approval-shaped entries into `review_decisions.json`.

## 6. Blank decision record (copy per atomic claim)

| Field | Entry |
|---|---|
| Register item / claim ID and exact UI text |  |
| Crop / variety / season / geographic scope / farmer context |  |
| Claim version and evidence dossier hash |  |
| Sources, exact locators, versions/hashes, and use permissions |  |
| Reviewer identity and independent verification reference/date |  |
| Relevant qualifications, scope, authority, and conflict declaration |  |
| Comments, uncertainties, contradictions, and requested changes |  |
| Decision: pending / approve / reject; rationale and conditions |  |
| Reviewer attributable signature or trusted identity reference |  |
| Effective date / revalidation date or trigger / revocation conditions |  |
| Independent second review (when required) |  |
| Product owner disposition and change-log reference |  |

## 7. Decision and release boundary

All R14 items remain **PENDING**. No qualified reviewer was engaged or verified, no evidence dossier was submitted for review, and no attributable decision was obtained. Unsupported, conflicting, out-of-scope, unlicensed, or unverifiable claims remain pending or are rejected; they are not promoted to rules to make coverage appear complete.

This phase changes documentation only. `rules.json`, `review_decisions.json`, recommender behavior, farmer-facing claims, database, migrations, and application configuration remain outside scope and must not be changed through this register. CropPulse remains **DEVELOPMENT ONLY**; this package authorizes neither a farmer pilot nor public release.
