import json
from datetime import date

from utils import agronomy_knowledge as ak


def _fixture_pack(tmp_path, monkeypatch):
    for name in ("sources.json", "statements.json", "rules.json", "review_decisions.json", "quality_issues.json", "schema.json", "MANIFEST.json"):
        (tmp_path / name).write_bytes((ak.PACK_DIR / name).read_bytes())
    monkeypatch.setattr(ak, "PACK_DIR", tmp_path)
    monkeypatch.setattr(ak, "SOURCES_PATH", tmp_path / "sources.json")
    monkeypatch.setattr(ak, "STATEMENTS_PATH", tmp_path / "statements.json")
    monkeypatch.setattr(ak, "RULES_PATH", tmp_path / "rules.json")
    monkeypatch.setattr(ak, "DECISIONS_PATH", tmp_path / "review_decisions.json")
    monkeypatch.setattr(ak, "ISSUES_PATH", tmp_path / "quality_issues.json")
    monkeypatch.setattr(ak, "SCHEMA_PATH", tmp_path / "schema.json")


def _write(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")
    if path.name in {"sources.json", "statements.json", "rules.json", "review_decisions.json", "quality_issues.json", "schema.json"}:
        manifest = ak.build_manifest()
        (ak.PACK_DIR / "MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")


def _test_rule(**updates):
    return {
        "rule_id": "TEST_ONLY.maize.huya",
        "version": "test-1",
        "category": "crop_suitability",
        "status": "draft",
        "crop": "Maize",
        "variety": None,
        "geography": {"type": "district", "scope": ["Huye"]},
        "season_scope": ["A"],
        "production_system": None,
        "conditions": [],
        "recommendation": "TEST-ONLY fixture; never for farmer use.",
        "parameters": [],
        "source_references": [{"source_id": "rab.crop-innovation-tech-transfer",
                               "locator": "TEST-ONLY page section", "paraphrase": "TEST-ONLY citation fixture."}],
        "limitations": ["TEST-ONLY fixture."],
        "review_status": "not_reviewed",
        "confidence_method": None,
        "effective_from": None,
        "revalidate_by": None,
        "supersedes": None,
        "change_history": [],
        **updates,
    }


def test_existing_pack_has_sources_but_no_approved_rules_and_keeps_nisr_separate():
    report = ak.validate_pack(today=date(2026, 10, 22))
    assert report["valid"]
    assert report["counts"]["sources"] == 5
    assert report["counts"]["source_statements"] == 4
    assert report["counts"]["agronomic_rules"] == report["counts"]["approved_rules"] == 0
    assert report["counts"]["nisr_rows"] == 2020
    assert report["nisr_dataset"]["integrity"] == "valid"
    assert report["coverage"]["districts_total"] == 30
    assert report["coverage"]["districts_with_approved_rules"] == []
    assert ak.approved_rules_for("Maize", "Huye", "A", today=date(2026, 10, 22)) == []


def test_nisr_source_registry_checksum_mismatch_fails_validation(tmp_path, monkeypatch):
    _fixture_pack(tmp_path, monkeypatch)
    sources = json.loads(ak.SOURCES_PATH.read_text(encoding="utf-8"))
    nisr = next(row for row in sources["sources"] if row["source_id"] == "nisr.sas-2023-2026")
    nisr["content_sha256"] = "0" * 64
    _write(ak.SOURCES_PATH, sources)

    report = ak.validate_pack(today=date(2026, 10, 22))
    assert not report["valid"]
    assert "nisr_source_registry_checksum_mismatch" in {finding["code"] for finding in report["findings"]}


def test_missing_rule_source_is_rejected(tmp_path, monkeypatch):
    _fixture_pack(tmp_path, monkeypatch)
    rule = _test_rule(source_references=[{"source_id": "missing.source", "locator": "TEST_ONLY", "paraphrase": "TEST_ONLY"}])
    _write(ak.RULES_PATH, {"schema_version": "1.0", "rules": [rule]})
    codes = {finding["code"] for finding in ak.validate_pack(today=date(2026, 10, 22))["findings"]}
    assert "unknown_rule_source" in codes


def test_modified_registered_evidence_file_fails_checksum(tmp_path):
    artifact = tmp_path / "source.txt"
    artifact.write_text("TEST_ONLY source evidence", encoding="utf-8")
    source = {"content_path": "source.txt", "content_sha256": ak._sha256(artifact)}
    assert ak._source_content_matches(source, root=tmp_path)
    artifact.write_text("TEST_ONLY modified evidence", encoding="utf-8")
    assert not ak._source_content_matches(source, root=tmp_path)
    assert not ak._source_content_matches({**source, "content_path": "..\\outside.txt"}, root=tmp_path)


def test_draft_rule_never_appears_in_approved_scope(tmp_path, monkeypatch):
    _fixture_pack(tmp_path, monkeypatch)
    _write(ak.RULES_PATH, {"schema_version": "1.0", "rules": [_test_rule()]})
    assert ak.validate_pack(today=date(2026, 10, 22))["valid"]
    assert ak.approved_rules_for("Maize", "Huye", "A", today=date(2026, 10, 22)) == []


def test_nisr_statistics_cannot_be_used_as_agronomic_evidence(tmp_path, monkeypatch):
    _fixture_pack(tmp_path, monkeypatch)
    rule = _test_rule(source_references=[{"source_id": "nisr.sas-2023-2026", "locator": "table 1", "paraphrase": "test only"}])
    _write(ak.RULES_PATH, {"schema_version": "1.0", "rules": [rule]})
    report = ak.validate_pack(today=date(2026, 10, 22))
    assert not report["valid"]
    assert "statistics_used_as_agronomy" in {f["code"] for f in report["findings"]}


def test_local_approval_attestation_cannot_activate_farmer_guidance(tmp_path, monkeypatch):
    _fixture_pack(tmp_path, monkeypatch)
    rule = _test_rule(status="approved", review_status="approved_for_scope",
                      effective_from="2026-01-01", revalidate_by="2027-01-01")
    _write(ak.RULES_PATH, {"schema_version": "1.0", "rules": [rule]})
    assert "local_review_missing" in {f["code"] for f in ak.validate_pack(today=date(2026, 10, 22))["findings"]}
    decision = {"rule_id": rule["rule_id"], "rule_version": rule["version"], "decision": "approved",
                "reviewer_id": "TEST_ONLY_REVIEWER", "reviewer_role": "qualified_local_agronomist",
                "qualification_verified": True, "decision_date": "2026-10-22",
                "rationale": "TEST-ONLY approval gate fixture; not a real review."}
    _write(ak.DECISIONS_PATH, {"schema_version": "1.0", "decisions": [decision]})
    report = ak.validate_pack(today=date(2026, 10, 22))
    assert not report["valid"]
    assert report["counts"]["declared_approved_rules"] == 1
    assert report["counts"]["approved_rules"] == 0
    assert report["coverage"]["districts_with_approved_rules"] == []
    assert "approval_identity_unverifiable" in {f["code"] for f in report["findings"]}
    assert "review_sequence_or_separation_failed" in {f["code"] for f in report["findings"]}
    assert ak.approved_rules_for("Maize", "Huye", "A", today=date(2026, 10, 22)) == []
    assert ak.approved_rules_for("Maize", "Karongi", "A", today=date(2026, 10, 22)) == []
    assert ak.approved_rules_for("Maize", "Huye", "B", today=date(2026, 10, 22)) == []


def test_expired_approved_rule_is_not_returned(tmp_path, monkeypatch):
    _fixture_pack(tmp_path, monkeypatch)
    rule = _test_rule(status="approved", review_status="approved_for_scope",
                      effective_from="2020-01-01", revalidate_by="2021-01-01")
    _write(ak.RULES_PATH, {"schema_version": "1.0", "rules": [rule]})
    decision = {"rule_id": rule["rule_id"], "rule_version": rule["version"], "decision": "approved",
                "reviewer_id": "TEST_ONLY_REVIEWER", "reviewer_role": "qualified_local_agronomist",
                "qualification_verified": True, "decision_date": "2020-01-01",
                "rationale": "TEST-ONLY expiry fixture."}
    _write(ak.DECISIONS_PATH, {"schema_version": "1.0", "decisions": [decision]})
    assert not ak.validate_pack(today=date(2026, 10, 22))["valid"]
    assert ak.approved_rules_for("Maize", "Huye", "A", today=date(2026, 10, 22)) == []


def test_unknown_district_and_duplicate_rule_versions_are_rejected(tmp_path, monkeypatch):
    _fixture_pack(tmp_path, monkeypatch)
    rule = _test_rule(geography={"type": "district", "scope": ["Atlantis"]})
    _write(ak.RULES_PATH, {"schema_version": "1.0", "rules": [rule, rule]})
    codes = {f["code"] for f in ak.validate_pack(today=date(2026, 10, 22))["findings"]}
    assert "unknown_district_scope" in codes
    assert "duplicate_rule_version" in codes


def _write_approved_fixture(rule):
    _write(ak.RULES_PATH, {"schema_version": "1.0", "rules": [rule]})
    decision = {"rule_id": rule["rule_id"], "rule_version": rule["version"], "decision": "approved",
                "reviewer_id": "TEST_ONLY_REVIEWER", "reviewer_role": "qualified_local_agronomist",
                "qualification_verified": True, "decision_date": "2026-10-22",
                "rationale": "TEST_ONLY approval scope fixture."}
    _write(ak.DECISIONS_PATH, {"schema_version": "1.0", "decisions": [decision]})


def test_variety_specific_rule_is_hidden_without_exact_variety_match(tmp_path, monkeypatch):
    _fixture_pack(tmp_path, monkeypatch)
    rule = _test_rule(variety="TEST_ONLY Hybrid A", conditions=[], status="approved",
                      review_status="approved_for_scope", effective_from="2026-01-01", revalidate_by="2027-01-01")
    _write_approved_fixture(rule)
    assert not ak._rule_matches_scope(rule, "Maize", "Huye", "A", today=date(2026, 10, 22))
    assert not ak._rule_matches_scope(rule, "Maize", "Huye", "A", variety="TEST_ONLY Hybrid B",
                                      today=date(2026, 10, 22))
    assert ak._rule_matches_scope(rule, "Maize", "Huye", "A", variety="test_only hybrid a",
                                  today=date(2026, 10, 22))
    assert ak.approved_rules_for("Maize", "Huye", "A", variety="test_only hybrid a",
                                 today=date(2026, 10, 22)) == []


def test_rule_conditions_fail_closed_without_matching_environmental_context(tmp_path, monkeypatch):
    _fixture_pack(tmp_path, monkeypatch)
    rule = _test_rule(variety=None, conditions=[{"parameter": "soil_ph", "operator": "gte", "value": 5.5, "unit": "pH"}],
                      status="approved", review_status="approved_for_scope",
                      effective_from="2026-01-01", revalidate_by="2027-01-01")
    _write_approved_fixture(rule)
    assert not ak._rule_matches_scope(rule, "Maize", "Huye", "A", today=date(2026, 10, 22))
    assert not ak._rule_matches_scope(rule, "Maize", "Huye", "A", condition_context={"soil_ph": 5.0},
                                      today=date(2026, 10, 22))
    assert ak._rule_matches_scope(rule, "Maize", "Huye", "A", condition_context={"soil_ph": 5.7},
                                  today=date(2026, 10, 22))
    assert ak.approved_rules_for("Maize", "Huye", "A", condition_context={"soil_ph": 5.7},
                                 today=date(2026, 10, 22)) == []


def test_unevaluable_rule_condition_invalidates_pack(tmp_path, monkeypatch):
    _fixture_pack(tmp_path, monkeypatch)
    _write(ak.RULES_PATH, {"schema_version": "1.0", "rules": [
        _test_rule(conditions=[{"parameter": "soil_ph", "state": "unknown"}])
    ]})
    assert "invalid_rule_condition" in {f["code"] for f in ak.validate_pack(today=date(2026, 10, 22))["findings"]}


def test_malformed_threshold_and_unsupported_units_are_rejected(tmp_path, monkeypatch):
    _fixture_pack(tmp_path, monkeypatch)
    rule = _test_rule(conditions=[{"parameter": "rainfall", "operator": "gte", "value": "a lot", "unit": "unknown"}])
    _write(ak.RULES_PATH, {"schema_version": "1.0", "rules": [rule]})
    assert "invalid_rule_condition" in {f["code"] for f in ak.validate_pack(today=date(2026, 10, 22))["findings"]}


def test_invalid_rule_date_and_unknown_rule_fields_are_rejected(tmp_path, monkeypatch):
    _fixture_pack(tmp_path, monkeypatch)
    rule = _test_rule(effective_from="2026-02-30", extra_status="trusted")
    _write(ak.RULES_PATH, {"schema_version": "1.0", "rules": [rule]})
    codes = {f["code"] for f in ak.validate_pack(today=date(2026, 10, 22))["findings"]}
    assert "invalid_rule_date" in codes
    assert "unknown_rule_fields" in codes


def test_stale_registry_manifest_is_a_hard_block(tmp_path, monkeypatch):
    _fixture_pack(tmp_path, monkeypatch)
    rule = _test_rule()
    _write(ak.RULES_PATH, {"schema_version": "1.0", "rules": [rule]})
    manifest = json.loads((tmp_path / "MANIFEST.json").read_text(encoding="utf-8"))
    manifest["dataset_sha256"] = "0" * 64
    _write(tmp_path / "MANIFEST.json", manifest)
    report = ak.validate_pack(today=date(2026, 10, 22))
    assert report["manifest_status"] == "stale"
    assert not report["valid"]
    assert "agronomy_manifest_stale" in {f["code"] for f in report["findings"]}


def test_later_withdrawal_prevents_declared_approval_from_remaining_current(tmp_path, monkeypatch):
    _fixture_pack(tmp_path, monkeypatch)
    rule = _test_rule(status="approved", review_status="approved_for_scope",
                      effective_from="2026-01-01", revalidate_by="2027-01-01")
    approved = {"rule_id": rule["rule_id"], "rule_version": rule["version"], "decision": "approved",
                "reviewer_id": "TEST_ONLY_REVIEWER", "reviewer_role": "qualified_local_agronomist",
                "qualification_verified": True, "decision_date": "2026-10-20", "rationale": "TEST_ONLY"}
    withdrawn = {**approved, "decision": "withdrawn", "decision_date": "2026-10-22",
                 "rationale": "TEST_ONLY withdrawal"}
    _write(ak.RULES_PATH, {"schema_version": "1.0", "rules": [rule]})
    _write(ak.DECISIONS_PATH, {"schema_version": "1.0", "decisions": [approved, withdrawn]})
    report = ak.validate_pack(today=date(2026, 10, 22))
    assert "approval_revoked_by_later_decision" in {item["code"] for item in report["findings"]}
    assert ak.approved_rules_for("Maize", "Huye", "A", today=date(2026, 10, 22)) == []


def test_conflicting_approved_versions_are_reported_and_never_served(tmp_path, monkeypatch):
    _fixture_pack(tmp_path, monkeypatch)
    first = _test_rule(status="approved", review_status="approved_for_scope",
                       effective_from="2026-01-01", revalidate_by="2027-01-01")
    second = _test_rule(version="test-2", status="approved", review_status="approved_for_scope",
                        effective_from="2026-01-01", revalidate_by="2027-01-01")
    _write(ak.RULES_PATH, {"schema_version": "1.0", "rules": [first, second]})
    report = ak.validate_pack(today=date(2026, 10, 22))
    assert "conflicting_active_rule_versions" in {item["code"] for item in report["findings"]}
    assert ak.approved_rules_for("Maize", "Huye", "A", today=date(2026, 10, 22)) == []


def test_withdrawn_and_superseded_states_never_match_active_scope():
    for status in ("withdrawn", "superseded", "expired", "rejected", "quarantined"):
        rule = _test_rule(status=status, review_status=status)
        assert not ak._rule_matches_scope(rule, "Maize", "Huye", "A", today=date(2026, 10, 22))


def test_resolved_quality_issue_requires_and_records_verification_evidence(tmp_path, monkeypatch):
    _fixture_pack(tmp_path, monkeypatch)
    issues = json.loads((tmp_path / "quality_issues.json").read_text(encoding="utf-8"))
    issue = next(row for row in issues["issues"] if row["issue_id"] == "AGQ-0005")
    issue.update(status="resolved", resolved_at="2026-10-29")
    issue.pop("resolution", None)
    _write(tmp_path / "quality_issues.json", issues)
    report = ak.validate_pack(today=date(2026, 10, 29))
    assert not report["valid"]
    assert any(item["code"] == "resolved_issue_missing_evidence" for item in report["findings"])

    issue["resolution"] = "Regression tests and output boundary were checked."
    _write(tmp_path / "quality_issues.json", issues)
    report = ak.validate_pack(today=date(2026, 10, 29))
    assert report["valid"]
    assert report["counts"]["open_quality_issues"] == 5
