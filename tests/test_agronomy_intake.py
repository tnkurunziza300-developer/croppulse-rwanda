"""TEST_ONLY fixtures for the isolated local knowledge-intake workflow."""
import json
from pathlib import Path
import zipfile

import pytest

import utils.agronomy_intake as intake
from utils.agronomy_intake import MAX_ARTIFACT_BYTES, IntakeError, coverage_report, list_records, receive, transition


def _metadata(**overrides):
    return {
        "dataset_id": "TEST_ONLY.dataset", "version": "test-v1",
        "record_kind": "unverified_submission", "source_organization": "TEST_ONLY organization",
        "source_identity": "TEST_ONLY source record", "title": "TEST_ONLY fixture; not real evidence",
        "received_date": "2026-10-22", "publication_date": None, "data_owner": "TEST_ONLY owner",
        "source_contact_or_provenance": "TEST_ONLY fixture only", "permission_status": "retain_original",
        "license_status": "open", "format": "csv", "preservation_reference": None,
        "geographic_scope": ["TEST_ONLY: field"], "crops": ["TEST_ONLY: maize"],
        "varieties": [], "seasons": ["TEST_ONLY: A"], "soil_scope": [], "production_systems": [],
        "original_units": ["TEST_ONLY: ha"], "transformations": [],
        "limitations": ["TEST_ONLY fixture; not for guidance"], "source_locators": ["TEST_ONLY locator"],
        "geography_type": "site", "guidance_categories": ["crop_suitability"], "conditions": [],
        "effective_from": "2026-01-01", "revalidate_by": "2027-01-01", "supersedes": None,
        "submitter_id": "TEST_ONLY_submitter",
        "submitter_role": "TEST_ONLY_contributor", **overrides,
    }


def test_intake_preserves_original_checksum_and_starts_unapproved(tmp_path):
    source = tmp_path / "evidence.csv"
    source.write_text("district,value\nTEST_ONLY Huye,1\n", encoding="utf-8")
    result = receive(source, _metadata(), root=tmp_path / "store")
    assert result["state"] == "received"
    record_dir = Path(result["path"])
    assert (record_dir / "original.csv").read_bytes() == source.read_bytes()
    assert json.loads((record_dir / "events.json").read_text())[0]["state"] == "received"
    assert json.loads((record_dir / "validation.json").read_text())["structural_validation"] == "passed"
    assert json.loads((record_dir / "validation.json").read_text())["provenance_review"] == "pending"
    assert list_records(root=tmp_path / "store")[0]["state"] == "received"
    with pytest.raises(IntakeError, match="already exists"):
        receive(source, _metadata(), root=tmp_path / "store")


def test_intake_publishes_only_after_complete_package_copy(tmp_path, monkeypatch):
    source = tmp_path / "evidence.txt"
    source.write_text("TEST_ONLY source", encoding="utf-8")
    root = tmp_path / "store"
    real_copyfile = intake.shutil.copyfile
    publication_copy_saw_pending_marker = []

    def checked_copyfile(source_path, target_path):
        destination = Path(target_path)
        if destination.parent.name == intake.hashlib.sha256(b"TEST_ONLY.dataset\0test-v1").hexdigest()[:24]:
            publication_copy_saw_pending_marker.append((destination.parent / ".publication_pending").is_file())
        return real_copyfile(source_path, target_path)

    monkeypatch.setattr(intake.shutil, "copyfile", checked_copyfile)
    result = receive(source, _metadata(format="txt"), root=root)

    assert publication_copy_saw_pending_marker == [True, True, True, True]
    assert Path(result["path"]).is_dir()
    assert not (Path(result["path"]) / ".publication_pending").exists()
    assert list_records(root=root)[0]["submission_id"] == result["submission_id"]


def test_failed_publication_preserves_hidden_recoverable_package(tmp_path, monkeypatch):
    source = tmp_path / "evidence.txt"
    source.write_text("TEST_ONLY source", encoding="utf-8")
    root = tmp_path / "store"

    def deny_publication(source_path, target_path):
        if Path(target_path).parent.name == intake.hashlib.sha256(b"TEST_ONLY.dataset\0test-v1").hexdigest()[:24]:
            raise PermissionError("TEST_ONLY simulated Windows publication denial")
        return real_copyfile(source_path, target_path)

    real_copyfile = intake.shutil.copyfile
    monkeypatch.setattr(intake.shutil, "copyfile", deny_publication)
    with pytest.raises(IntakeError, match="hidden staged data was preserved"):
        receive(source, _metadata(format="txt"), root=root)

    staged = list((root / "records").glob(".staging-*"))
    submission_id = intake.hashlib.sha256(b"TEST_ONLY.dataset\0test-v1").hexdigest()[:24]
    pending = root / "records" / submission_id
    assert len(staged) == 1
    assert (pending / ".publication_pending").is_file()
    assert (staged[0] / "metadata.json").is_file()
    assert (staged[0] / "validation.json").is_file()
    assert (staged[0] / "events.json").is_file()
    assert (staged[0] / "original.txt").read_text(encoding="utf-8") == "TEST_ONLY source"
    assert list_records(root=root) == []
    assert coverage_report(root=root)["active_current_guidance_packages"] == 0
    assert list((root / ".staging").glob("*.lock")) == []


def test_structural_csv_rejects_ragged_rows_without_archiving(tmp_path):
    source = tmp_path / "bad.csv"
    source.write_text("a,b\n1\n", encoding="utf-8")
    with pytest.raises(IntakeError, match="same number"):
        receive(source, _metadata(), root=tmp_path / "store")
    assert not (tmp_path / "store" / "records").exists()


@pytest.mark.parametrize("payload", [b'{"x":1,"x":2}', b"null", b"\xff"])
def test_json_rejects_duplicate_keys_non_collection_and_bad_encoding(tmp_path, payload):
    source = tmp_path / "evidence.json"
    source.write_bytes(payload)
    with pytest.raises(IntakeError):
        receive(source, _metadata(format="json"), root=tmp_path / "store")


def test_file_size_limit_and_malformed_pdf_are_rejected(tmp_path):
    oversized = tmp_path / "large.txt"
    with oversized.open("wb") as stream:
        stream.truncate(MAX_ARTIFACT_BYTES + 1)
    with pytest.raises(IntakeError, match="25 MiB"):
        receive(oversized, _metadata(format="txt"), root=tmp_path / "store")
    malformed = tmp_path / "truncated.pdf"
    malformed.write_bytes(b"%PDF-1.7\n")
    with pytest.raises(IntakeError, match="end-of-file"):
        receive(malformed, _metadata(format="pdf"), root=tmp_path / "store")

    large_json = tmp_path / "large.json"
    with large_json.open("wb") as stream:
        stream.truncate(5 * 1024 * 1024 + 1)
    with pytest.raises(IntakeError, match="5 MiB"):
        receive(large_json, _metadata(format="json"), root=tmp_path / "json-store")


def test_docx_container_is_checked_and_zip_entry_bomb_rejected(tmp_path):
    valid = tmp_path / "valid.docx"
    with zipfile.ZipFile(valid, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<document/>")
    result = receive(valid, _metadata(format="docx"), root=tmp_path / "valid-store")
    assert result["stored"] is True

    many = tmp_path / "many.docx"
    with zipfile.ZipFile(many, "w") as archive:
        archive.writestr("[Content_Types].xml", "x")
        archive.writestr("word/document.xml", "x")
        for index in range(1000):
            archive.writestr(f"word/extra-{index}.xml", "x")
    with pytest.raises(IntakeError, match="entry limits"):
        receive(many, _metadata(format="docx"), root=tmp_path / "bomb-store")

    malformed = tmp_path / "malformed.docx"
    malformed.write_bytes(b"PK not a valid zip archive")
    with pytest.raises(IntakeError, match="end-of-directory"):
        receive(malformed, _metadata(format="docx"), root=tmp_path / "malformed-store")

    traversal = tmp_path / "traversal.docx"
    with zipfile.ZipFile(traversal, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<document/>")
        archive.writestr("../escape.txt", "TEST_ONLY")
    with pytest.raises(IntakeError, match="unsafe path"):
        receive(traversal, _metadata(format="docx"), root=tmp_path / "traversal-store")


def test_docx_member_crc_corruption_is_rejected(tmp_path):
    corrupted = tmp_path / "corrupted.docx"
    with zipfile.ZipFile(corrupted, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "TEST_ONLY_PAYLOAD")
    raw = corrupted.read_bytes()
    marker = b"TEST_ONLY_PAYLOAD"
    assert marker in raw
    corrupted.write_bytes(raw.replace(marker, b"X" + marker[1:], 1))
    with pytest.raises(IntakeError, match="malformed"):
        receive(corrupted, _metadata(format="docx"), root=tmp_path / "corrupt-store")


def test_metadata_only_keeps_reference_and_does_not_copy_original(tmp_path):
    source = tmp_path / "evidence.txt"
    source.write_text("TEST_ONLY source", encoding="utf-8")
    metadata = _metadata(format="txt", permission_status="metadata_only", license_status="restricted",
                         preservation_reference="TEST_ONLY permitted source locator")
    result = receive(source, metadata, root=tmp_path / "store")
    record_dir = Path(result["path"])
    assert not list(record_dir.glob("original.*"))
    stored = json.loads((record_dir / "metadata.json").read_text())
    assert stored["storage"] == "metadata_reference_only"
    assert stored["preservation_reference"] == "TEST_ONLY permitted source locator"


def test_unknown_reuse_rights_block_progression(tmp_path):
    source = tmp_path / "evidence.txt"
    source.write_text("TEST_ONLY source", encoding="utf-8")
    metadata = _metadata(format="txt", permission_status="unknown", license_status="unknown",
                         preservation_reference="TEST_ONLY permitted locator")
    result = receive(source, metadata, root=tmp_path / "store")
    transition(result["submission_id"], "validation", actor_id="TEST_ONLY_operator",
               actor_role="admin", rationale="TEST_ONLY structural check", root=tmp_path / "store")
    with pytest.raises(IntakeError, match="blocks review"):
        transition(result["submission_id"], "technical_review", actor_id="TEST_ONLY_reviewer",
                   actor_role="technical_reviewer", rationale="TEST_ONLY fixture", root=tmp_path / "store")


def test_lifecycle_requires_distinct_reviewers_approval_and_admin_activation(tmp_path):
    source = tmp_path / "evidence.csv"
    source.write_text("column\nTEST_ONLY value\n", encoding="utf-8")
    root = tmp_path / "store"
    result = receive(source, _metadata(record_kind="agronomic_guidance"), root=root)
    submission = result["submission_id"]
    transition(submission, "validation", actor_id="TEST_ONLY_operator", actor_role="admin",
               rationale="TEST_ONLY structural check", root=root)
    transition(submission, "technical_review", actor_id="TEST_ONLY_technical", actor_role="technical_reviewer",
               rationale="TEST_ONLY review", root=root)
    with pytest.raises(IntakeError, match="differ from technical reviewer"):
        transition(submission, "specialist_review", actor_id="TEST_ONLY_technical",
                   actor_role="qualified_local_agronomist", qualification_verified=True,
                   rationale="TEST_ONLY fixture", root=root)
    transition(submission, "specialist_review", actor_id="TEST_ONLY_specialist1",
               actor_role="qualified_local_agronomist", qualification_verified=True,
               rationale="TEST_ONLY specialist review", root=root)
    with pytest.raises(IntakeError, match="distinct from both prior reviewers"):
        transition(submission, "approved", actor_id="TEST_ONLY_technical",
                   actor_role="qualified_local_agronomist", qualification_verified=True,
                   rationale="TEST_ONLY approval", root=root)
    with pytest.raises(IntakeError, match="distinct from both prior reviewers"):
        transition(submission, "approved", actor_id="TEST_ONLY_specialist1",
                   actor_role="qualified_local_agronomist", qualification_verified=True,
                   rationale="TEST_ONLY approval", root=root)
    transition(submission, "approved", actor_id="TEST_ONLY_specialist2",
               actor_role="qualified_local_agronomist", qualification_verified=True,
               rationale="TEST_ONLY approval", root=root)
    with pytest.raises(IntakeError, match="knowledge_administrator"):
        transition(submission, "active", actor_id="TEST_ONLY_specialist2", actor_role="admin",
                   rationale="TEST_ONLY activation", root=root)
    with pytest.raises(IntakeError, match="independent"):
        transition(submission, "active", actor_id="TEST_ONLY_specialist2", actor_role="knowledge_administrator",
                   rationale="TEST_ONLY activation", root=root)
    transition(submission, "active", actor_id="TEST_ONLY_admin", actor_role="knowledge_administrator",
               rationale="TEST_ONLY activation", root=root)
    assert list_records(root=root)[0]["state"] == "active"
    from utils import agronomy_knowledge
    assert agronomy_knowledge.approved_rules_for("Maize", "Huye", "A") == []
    coverage = coverage_report(root=root)
    assert coverage["active_current_guidance_packages"] == 1
    assert coverage["by_crop"]["TEST_ONLY: maize"]["sources"] == ["TEST_ONLY organization"]
    assert coverage["districts_with_active_guidance"] == []
    events = json.loads((root / "records" / submission / "events.json").read_text())
    assert all(event["reason"].startswith("TEST_ONLY") for event in events[1:])


def test_intake_is_not_added_to_current_farmer_approved_registry(tmp_path):
    from utils import agronomy_knowledge

    source = tmp_path / "fixture.csv"
    source.write_text("column\nTEST_ONLY\n", encoding="utf-8")
    receive(source, _metadata(), root=tmp_path / "store")
    assert agronomy_knowledge.approved_rules_for("Maize", "Huye", "A") == []


def test_event_chain_tampering_blocks_further_review(tmp_path):
    source = tmp_path / "evidence.txt"
    source.write_text("TEST_ONLY source", encoding="utf-8")
    root = tmp_path / "store"
    result = receive(source, _metadata(format="txt"), root=root)
    event_path = root / "records" / result["submission_id"] / "events.json"
    events = json.loads(event_path.read_text())
    events[0]["reason"] = "modified"
    event_path.write_text(json.dumps(events), encoding="utf-8")
    assert list_records(root=root)[0]["integrity"] == "invalid"
    with pytest.raises(IntakeError, match="integrity check failed"):
        transition(result["submission_id"], "validation", actor_id="TEST_ONLY_operator",
                   actor_role="admin", rationale="TEST_ONLY check", root=root)


def test_original_artifact_tampering_blocks_coverage_and_review(tmp_path):
    source = tmp_path / "evidence.txt"
    source.write_text("TEST_ONLY source", encoding="utf-8")
    root = tmp_path / "store"
    result = receive(source, _metadata(format="txt"), root=root)
    original = root / "records" / result["submission_id"] / "original.txt"
    original.write_text("modified", encoding="utf-8")
    assert list_records(root=root)[0]["integrity"] == "invalid"
    assert coverage_report(root=root)["active_current_guidance_packages"] == 0
    with pytest.raises(IntakeError, match="integrity check failed"):
        transition(result["submission_id"], "validation", actor_id="TEST_ONLY_operator",
                   actor_role="admin", rationale="TEST_ONLY check", root=root)


@pytest.mark.parametrize("file_name", ["metadata.json", "validation.json"])
def test_metadata_or_validation_tampering_blocks_coverage_and_review(tmp_path, file_name):
    source = tmp_path / "evidence.txt"
    source.write_text("TEST_ONLY source", encoding="utf-8")
    root = tmp_path / "store"
    result = receive(source, _metadata(format="txt"), root=root)
    record_dir = root / "records" / result["submission_id"]
    target = record_dir / file_name
    value = json.loads(target.read_text())
    value["title"] = "tampered" if file_name == "metadata.json" else value.get("state", "tampered")
    target.write_text(json.dumps(value), encoding="utf-8")
    assert list_records(root=root)[0]["integrity"] == "invalid"
    assert coverage_report(root=root)["active_current_guidance_packages"] == 0
    with pytest.raises(IntakeError, match="integrity check failed"):
        transition(result["submission_id"], "validation", actor_id="TEST_ONLY_operator",
                   actor_role="admin", rationale="TEST_ONLY check", root=root)


def test_active_state_without_recorded_approval_fails_lifecycle_integrity(tmp_path):
    from utils.agronomy_intake import _event_digest

    source = tmp_path / "evidence.txt"
    source.write_text("TEST_ONLY source", encoding="utf-8")
    root = tmp_path / "store"
    result = receive(source, _metadata(format="txt"), root=root)
    event_path = root / "records" / result["submission_id"] / "events.json"
    events = json.loads(event_path.read_text())
    event = {"event_id": "TEST_ONLY forged", "state": "active", "actor_id": "TEST_ONLY_admin",
             "actor_role": "knowledge_administrator", "qualification_verified": False,
             "occurred_at": "2026-10-22T00:00:00+00:00", "reason": "TEST_ONLY forged event",
             "previous_event_sha256": events[-1]["event_sha256"]}
    event["event_sha256"] = _event_digest(event)
    events.append(event)
    event_path.write_text(json.dumps(events), encoding="utf-8")
    assert list_records(root=root)[0]["integrity"] == "invalid"
    assert coverage_report(root=root)["active_current_guidance_packages"] == 0


def test_coverage_report_excludes_unverified_submission_and_reports_all_district_gaps(tmp_path):
    source = tmp_path / "evidence.csv"
    source.write_text("column\nTEST_ONLY\n", encoding="utf-8")
    root = tmp_path / "store"
    receive(source, _metadata(), root=root)
    report = coverage_report(root=root)
    assert report["active_current_guidance_packages"] == 0
    assert report["districts_with_active_guidance"] == []
    assert report["districts_total"] == 30
    assert len(report["districts_without_active_guidance"]) == 30
