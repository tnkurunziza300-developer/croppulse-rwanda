"""Local, immutable intake packages for future CropPulse evidence.

This module never writes the application database or publishes intake records to
farmers. It stores originals only when permission explicitly allows it.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import shutil
import struct
import uuid
import zipfile
import zlib
from datetime import date, datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from utils.geography import ALL_DISTRICTS

ROOT = Path(__file__).resolve().parents[1]
INTAKE_ROOT = ROOT / "data" / "agronomy" / "intake"
MAX_ARTIFACT_BYTES = 25 * 1024 * 1024
MAX_JSON_BYTES = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {".csv", ".json", ".pdf", ".docx", ".txt"}
STATES = {"received", "validation", "technical_review", "specialist_review",
          "approved", "active", "superseded", "expired", "rejected", "quarantined"}


class IntakeError(ValueError):
    """Expected validation or lifecycle rejection."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _event_digest(event: dict[str, Any]) -> str:
    payload = {key: value for key, value in event.items() if key != "event_sha256"}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _json_digest(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def verify_record(path: Path, metadata: dict[str, Any], events: list[dict[str, Any]]) -> list[str]:
    """Check metadata, archived bytes, event chain, and review sequence integrity."""
    findings = []
    previous = None
    state = None
    reviewers: dict[str, str] = {}
    transitions = {"received": {"validation", "quarantined"},
                   "validation": {"technical_review", "quarantined"},
                   "technical_review": {"specialist_review", "rejected", "quarantined"},
                   "specialist_review": {"approved", "rejected", "quarantined"},
                   "approved": {"active", "expired", "rejected"},
                   "active": {"superseded", "expired", "quarantined"},
                   "superseded": {"active"}, "expired": set(), "rejected": set(), "quarantined": set()}
    metadata_bytes = json.dumps(metadata, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if not events:
        findings.append("event_log_empty")
    for index, event in enumerate(events):
        if event.get("previous_event_sha256") != previous or event.get("event_sha256") != _event_digest(event):
            findings.append("event_chain_mismatch")
            break
        event_state = event.get("state")
        if index == 0:
            if (event_state != "received" or event.get("actor_id") != metadata.get("submitter_id")
                    or event.get("metadata_sha256") != hashlib.sha256(metadata_bytes).hexdigest()):
                findings.append("metadata_or_initial_event_mismatch")
            try:
                validation = json.loads((path / "validation.json").read_text(encoding="utf-8"))
                if event.get("validation_sha256") != _json_digest(validation):
                    findings.append("validation_report_mismatch")
            except (OSError, json.JSONDecodeError, TypeError):
                findings.append("validation_report_missing_or_invalid")
        elif state is None or event_state not in transitions.get(state, set()):
            findings.append("invalid_lifecycle_sequence")
        actor = event.get("actor_id")
        role = event.get("actor_role")
        if not isinstance(actor, str) or not actor.strip() or not isinstance(role, str) or not role.strip() or not str(event.get("reason", "")).strip():
            findings.append("incomplete_audit_event")
        if event_state == "technical_review":
            if actor == metadata.get("submitter_id") or role not in {"technical_reviewer", "admin"}:
                findings.append("invalid_technical_review")
            reviewers["technical"] = actor
        elif event_state == "specialist_review":
            if (actor == metadata.get("submitter_id") or actor == reviewers.get("technical")
                    or role not in {"qualified_local_agronomist", "authorized_specialist"}
                    or event.get("qualification_verified") is not True):
                findings.append("invalid_specialist_review")
            reviewers["specialist"] = actor
        elif event_state == "approved":
            if (metadata.get("record_kind") != "agronomic_guidance" or actor == metadata.get("submitter_id")
                    or actor in {reviewers.get("technical"), reviewers.get("specialist")}
                    or role not in {"qualified_local_agronomist", "authorized_specialist"}
                    or event.get("qualification_verified") is not True
                    or not metadata.get("guidance_categories") or not metadata.get("crops")
                    or not metadata.get("geographic_scope") or metadata.get("geography_type") == "unknown"
                    or not metadata.get("seasons") or not metadata.get("source_locators")
                    or not metadata.get("effective_from") or not metadata.get("revalidate_by")
                    or metadata.get("permission_status") in {"unknown", "prohibited"}
                    or metadata.get("license_status") in {"unknown", "prohibited"}):
                findings.append("invalid_guidance_approval")
            else:
                reviewers["approver"] = actor
        elif event_state == "active":
            if (role != "knowledge_administrator" or actor == metadata.get("submitter_id")
                    or actor in {reviewers.get("technical"), reviewers.get("specialist"), reviewers.get("approver")}):
                findings.append("invalid_activation")
        state = event_state
        previous = event["event_sha256"]
    if metadata.get("storage") == "original_archived":
        suffix = metadata.get("format", "")
        artifact = path / f"original.{suffix}"
        if not artifact.is_file() or _sha256(artifact) != metadata.get("artifact", {}).get("sha256"):
            findings.append("artifact_checksum_mismatch")
    return findings


def _json_no_duplicates(text: str) -> Any:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise IntakeError(f"JSON contains a duplicate key: {key}")
            result[key] = value
        return result
    return json.loads(text, object_pairs_hook=pairs)


def _validate_artifact(path: Path, expected_format: str) -> dict[str, Any]:
    suffix = path.suffix.casefold()
    if suffix not in ALLOWED_EXTENSIONS:
        raise IntakeError("Unsupported file type; allowed types are CSV, JSON, PDF, DOCX, and TXT.")
    if not isinstance(expected_format, str) or expected_format.casefold() != suffix.lstrip("."):
        raise IntakeError("The declared format does not match the file extension.")
    size = path.stat().st_size
    if size <= 0 or size > MAX_ARTIFACT_BYTES:
        raise IntakeError("Artifact must be non-empty and no larger than 25 MiB.")
    if suffix == ".json" and size > MAX_JSON_BYTES:
        raise IntakeError("JSON artifacts must be no larger than 5 MiB.")
    if path.is_symlink() or not path.is_file():
        raise IntakeError("Artifact must be a regular file, not a link.")
    raw = path.read_bytes()
    if len(raw) != size or len(raw) > MAX_ARTIFACT_BYTES:
        raise IntakeError("Artifact changed during reading or exceeded the size limit.")
    summary: dict[str, Any] = {"format": suffix[1:], "size_bytes": size}
    if suffix == ".csv":
        try:
            text = raw.decode("utf-8-sig")
            reader = csv.reader(io.StringIO(text, newline=""), strict=True)
            header = next(reader)
            row_count = 0
            for row in reader:
                if len(row) != len(header):
                    raise IntakeError("CSV rows must have the same number of fields as the header.")
                row_count += 1
        except (UnicodeDecodeError, csv.Error, StopIteration, RecursionError) as exc:
            raise IntakeError("CSV must be non-empty UTF-8 with a valid header and rows.") from exc
        if not header or any(not cell.strip() for cell in header) or len({c.casefold() for c in header}) != len(header):
            raise IntakeError("CSV headers must be non-empty and unique.")
        summary.update(columns=header, data_rows=row_count)
    elif suffix == ".json":
        if len(raw) > MAX_JSON_BYTES:
            raise IntakeError("JSON artifacts must be no larger than 5 MiB.")
        try:
            data = _json_no_duplicates(raw.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
            raise IntakeError("JSON must be valid UTF-8 without duplicate object keys.") from exc
        if not isinstance(data, (dict, list)):
            raise IntakeError("JSON root must be an object or array.")
        summary.update(root_type="object" if isinstance(data, dict) else "array",
                       records=len(data) if isinstance(data, list) else None)
    elif suffix == ".pdf":
        if not raw.startswith(b"%PDF-1.") and not raw.startswith(b"%PDF-2."):
            raise IntakeError("PDF header or version marker is invalid.")
        if b"%%EOF" not in raw[-2048:]:
            raise IntakeError("PDF end-of-file marker is missing; the document may be truncated.")
    elif suffix == ".docx":
        # Bound central-directory work before ZipFile allocates ZipInfo objects.
        eocd = raw.rfind(b"PK\x05\x06", max(0, len(raw) - 65557))
        if eocd < 0 or eocd + 22 > len(raw):
            raise IntakeError("DOCX archive has no valid end-of-directory record.")
        signature, disk, directory_disk, disk_entries, entry_count, directory_size, directory_offset, comment_len = struct.unpack_from("<4s4H2LH", raw, eocd)
        if (signature != b"PK\x05\x06" or eocd + 22 + comment_len != len(raw)
                or disk != 0 or directory_disk != 0 or disk_entries != entry_count
                or entry_count == 0xFFFF or directory_size == 0xFFFFFFFF or directory_offset == 0xFFFFFFFF
                or entry_count > 1000 or directory_size > 2 * 1024 * 1024
                or directory_offset + directory_size > eocd):
            raise IntakeError("DOCX archive directory is invalid or exceeds safe entry limits.")
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                names = archive.namelist()
                if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                    raise IntakeError("DOCX archive does not contain the expected document parts.")
                infos = archive.infolist()
                if len(names) != entry_count or sum(item.file_size for item in infos) > 50 * 1024 * 1024:
                    raise IntakeError("DOCX archive exceeds safe expanded-content limits.")
                if any(PurePosixPath(name).is_absolute() or PureWindowsPath(name).is_absolute()
                       or bool(PureWindowsPath(name).drive)
                       or ".." in PurePosixPath(name).parts or ".." in PureWindowsPath(name).parts
                       for name in names):
                    raise IntakeError("DOCX archive contains an unsafe path.")
                for item in infos:
                    if item.file_size and (not item.compress_size or item.file_size / item.compress_size > 200):
                        raise IntakeError("DOCX member compression ratio exceeds safe limits.")
                    with archive.open(item) as member:
                        while member.read(1024 * 1024):
                            pass  # Streaming reads enforce decompression bounds and verify each member CRC.
        except IntakeError:
            raise
        except (zipfile.BadZipFile, OSError, ValueError, OverflowError, RuntimeError, EOFError, zlib.error) as exc:
            raise IntakeError("DOCX archive is malformed.") from exc
    elif suffix == ".txt":
        try:
            if "\x00" in raw.decode("utf-8-sig"):
                raise IntakeError("Text documents must not contain NUL bytes.")
        except UnicodeDecodeError as exc:
            raise IntakeError("Text documents must be valid UTF-8.") from exc
    summary["sha256"] = hashlib.sha256(raw).hexdigest()
    summary["content_parsed"] = suffix in {".csv", ".json"}
    return summary


def _required_metadata(metadata: dict[str, Any]) -> None:
    if not isinstance(metadata, dict):
        raise IntakeError("Metadata must be a JSON object.")
    required = {"dataset_id", "version", "record_kind", "source_organization", "source_identity",
                "title", "received_date", "data_owner", "permission_status", "license_status",
                "format", "geographic_scope", "crops", "varieties", "seasons", "soil_scope",
                "production_systems", "original_units", "transformations", "limitations", "source_locators",
                "geography_type", "guidance_categories", "conditions",
                "source_contact_or_provenance", "submitter_id", "submitter_role"}
    missing = sorted(required - metadata.keys())
    if missing:
        raise IntakeError("Metadata is missing required fields: " + ", ".join(missing))
    if not isinstance(metadata["record_kind"], str) or metadata["record_kind"] not in {"historical_statistics", "agronomic_guidance", "official_document",
                                      "weather_climate", "unverified_submission"}:
        raise IntakeError("Unsupported record_kind.")
    if not isinstance(metadata["geography_type"], str) or metadata["geography_type"] not in {"national", "province", "district", "sector", "site", "unknown"}:
        raise IntakeError("geography_type must identify the recorded geographic granularity.")
    if not isinstance(metadata["permission_status"], str) or metadata["permission_status"] not in {"retain_original", "metadata_only", "unknown", "prohibited"}:
        raise IntakeError("permission_status must identify retention permission explicitly.")
    if not isinstance(metadata["license_status"], str) or metadata["license_status"] not in {"open", "restricted", "unknown", "prohibited"}:
        raise IntakeError("license_status must identify licensing status explicitly.")
    if not isinstance(metadata["format"], str) or metadata["format"].casefold() not in {ext[1:] for ext in ALLOWED_EXTENSIONS}:
        raise IntakeError("format must be one of CSV, JSON, PDF, DOCX, or TXT.")
    for key in ("dataset_id", "version", "source_organization", "source_identity", "title", "data_owner",
                "source_contact_or_provenance", "submitter_id", "submitter_role"):
        if not isinstance(metadata[key], str) or not metadata[key].strip():
            raise IntakeError(f"{key} must be a non-empty string.")
    if metadata.get("supersedes") is not None and not isinstance(metadata["supersedes"], str):
        raise IntakeError("supersedes must be a prior version identifier or null.")
    if metadata["permission_status"] != "retain_original" and not metadata.get("preservation_reference"):
        raise IntakeError("When the original is not retained, provide a permitted preservation_reference.")
    for key in ("crops", "varieties", "seasons", "geographic_scope", "soil_scope", "production_systems",
                "original_units", "transformations", "limitations", "source_locators", "guidance_categories", "conditions"):
        if not isinstance(metadata[key], list):
            raise IntakeError(f"{key} must be an array; preserve unknowns as explicit empty arrays.")
    for key in ("crops", "varieties", "seasons", "geographic_scope", "soil_scope", "production_systems",
                "original_units", "transformations", "limitations", "source_locators", "guidance_categories"):
        if any(not isinstance(item, str) for item in metadata[key]):
            raise IntakeError(f"{key} must contain only strings.")
    valid_categories = {"crop_suitability", "planting", "soil", "fertilizer", "water", "crop_management", "pest_disease", "other"}
    if set(metadata["guidance_categories"]) - valid_categories:
        raise IntakeError("guidance_categories contains an unsupported category.")
    if not isinstance(metadata["conditions"], list):
        raise IntakeError("conditions must be an array.")
    allowed_operators = {"eq", "ne", "in", "not_in", "gt", "gte", "lt", "lte"}
    if any(not isinstance(item, dict) or not isinstance(item.get("parameter"), str)
           or not item["parameter"].strip() or item.get("operator") not in allowed_operators
           or "value" not in item for item in metadata["conditions"]):
        raise IntakeError("conditions must use parameter, supported operator, and value fields.")
    if metadata["geography_type"] == "district" and set(metadata["geographic_scope"]) - set(ALL_DISTRICTS):
        raise IntakeError("District scope must use verified Rwanda district names.")
    try:
        date.fromisoformat(metadata["received_date"])
        if metadata.get("publication_date"):
            date.fromisoformat(metadata["publication_date"])
        for field in ("effective_from", "revalidate_by"):
            if metadata.get(field):
                date.fromisoformat(metadata[field])
    except (TypeError, ValueError) as exc:
        raise IntakeError("received_date and publication_date must be ISO dates.") from exc


def receive(artifact: str | Path, metadata: dict[str, Any], *, root: Path | None = None) -> dict[str, Any]:
    """Validate and create a new immutable received package; duplicate versions fail."""
    _required_metadata(metadata)
    supplied_path = Path(artifact)
    if supplied_path.is_symlink():
        raise IntakeError("Artifact must not be a symbolic link.")
    source_path = supplied_path.resolve(strict=True)
    result = _validate_artifact(source_path, metadata["format"])
    base = root or INTAKE_ROOT
    if base.is_symlink():
        raise IntakeError("Intake root must not be a symbolic link.")
    base.mkdir(parents=True, exist_ok=True)
    identity = hashlib.sha256(f"{metadata['dataset_id']}\0{metadata['version']}".encode()).hexdigest()[:24]
    target = base / "records" / identity
    if target.exists():
        raise IntakeError("This dataset version already exists; versions are immutable and cannot be overwritten.")
    records_directory = base / "records"
    lock_directory = base / ".staging"
    if records_directory.is_symlink() or lock_directory.is_symlink():
        raise IntakeError("Intake storage directories must not be symbolic links.")
    records_directory.mkdir(parents=True, exist_ok=True)
    lock_directory.mkdir(parents=True, exist_ok=True)
        # Keep the complete package in a hidden sibling until the final destination
        # has been assembled. Windows can deny directory renames even when source
        # and destination share a parent, so publication uses a pending sentinel.
    staging = records_directory / (".staging-" + identity + "-" + uuid.uuid4().hex)
    staging.mkdir(parents=True, exist_ok=False)
    preserve_staging = False
    try:
        packaged_metadata = dict(metadata)
        packaged_metadata["publication_date"] = metadata.get("publication_date")
        packaged_metadata["original_filename"] = source_path.name
        packaged_metadata["received_at"] = datetime.now(timezone.utc).isoformat()
        packaged_metadata["artifact"] = {k: v for k, v in result.items() if k != "content_parsed"}
        packaged_metadata["storage"] = "original_archived" if metadata["permission_status"] == "retain_original" else "metadata_reference_only"
        if metadata["permission_status"] == "retain_original":
            shutil.copyfile(source_path, staging / ("original" + source_path.suffix.casefold()))
            if _sha256(staging / ("original" + source_path.suffix.casefold())) != result["sha256"]:
                raise IntakeError("Archived artifact checksum mismatch.")
        (staging / "metadata.json").write_text(json.dumps(packaged_metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        validation_report = {"state": "received", "structural_validation": "passed",
            "provenance_review": "pending", "artifact_check": result,
            "limitations": ["Structural validation does not verify publisher authenticity, scientific correctness, or reuse rights."]}
        (staging / "validation.json").write_text(json.dumps(validation_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        event = {"event_id": str(uuid.uuid4()), "state": "received", "actor_id": metadata["submitter_id"],
                 "actor_role": metadata["submitter_role"], "occurred_at": packaged_metadata["received_at"],
                 "reason": "Intake package created; no review or approval is implied.", "previous_event_sha256": None,
                 "metadata_sha256": _json_digest(packaged_metadata), "validation_sha256": _json_digest(validation_report)}
        event["event_sha256"] = _event_digest(event)
        (staging / "events.json").write_text(json.dumps([event], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if target.exists():
            raise IntakeError("This dataset version already exists; versions are immutable and cannot be overwritten.")
        reservation = lock_directory / (identity + ".lock")
        try:
            descriptor = os.open(reservation, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise IntakeError("Another intake operation is using this dataset version; retry after checking its status.") from exc
        os.close(descriptor)
        try:
            if target.exists():
                raise IntakeError("This dataset version already exists; versions are immutable and cannot be overwritten.")
            # From destination creation onward, retain the complete staging copy
            # for any failure so an operator can recover without guessing.
            preserve_staging = True
            target.mkdir(exist_ok=False)
            pending_marker = target / ".publication_pending"
            with pending_marker.open("x", encoding="ascii") as marker:
                marker.write("Package publication is incomplete.\n")
                marker.flush()
                os.fsync(marker.fileno())
            for package_file in staging.iterdir():
                if package_file.is_symlink() or not package_file.is_file():
                    raise IntakeError("Staged package contains an unexpected filesystem entry.")
                shutil.copyfile(package_file, target / package_file.name)
            copied_metadata = json.loads((target / "metadata.json").read_text(encoding="utf-8"))
            copied_events = json.loads((target / "events.json").read_text(encoding="utf-8"))
            copied_validation = json.loads((target / "validation.json").read_text(encoding="utf-8"))
            if (_json_digest(copied_validation) != copied_events[0].get("validation_sha256")
                    or verify_record(target, copied_metadata, copied_events)):
                raise IntakeError("Copied package integrity check failed; it remains unpublished.")
            pending_marker.unlink()
        except FileExistsError as exc:
            preserve_staging = True
            raise IntakeError("This dataset version already exists; versions are immutable and cannot be overwritten.") from exc
        except OSError as exc:
            preserve_staging = True
            raise IntakeError(
                "Validated package publication failed; hidden staged data was preserved and cannot be listed or activated."
            ) from exc
        finally:
            reservation.unlink(missing_ok=True)
    except Exception:
        if not preserve_staging:
            shutil.rmtree(staging, ignore_errors=True)
        raise
    shutil.rmtree(staging, ignore_errors=True)
    return {"submission_id": identity, "state": "received", "artifact_sha256": result["sha256"],
            "stored": metadata["permission_status"] == "retain_original", "path": str(target)}


def _load_record(submission_id: str, root: Path) -> tuple[Path, dict, list]:
    if len(submission_id) != 24 or any(c not in "0123456789abcdef" for c in submission_id):
        raise IntakeError("Invalid submission ID.")
    path = root / "records" / submission_id
    if path.is_symlink() or (root / "records").is_symlink():
        raise IntakeError("Submission storage path must not be a symbolic link.")
    metadata = json.loads((path / "metadata.json").read_text(encoding="utf-8"))
    events = json.loads((path / "events.json").read_text(encoding="utf-8"))
    if verify_record(path, metadata, events):
        raise IntakeError("Submission integrity check failed; isolate it and do not review or activate it.")
    return path, metadata, events


def transition(submission_id: str, target_state: str, *, actor_id: str, actor_role: str,
               rationale: str, qualification_verified: bool = False, root: Path | None = None) -> dict[str, Any]:
    """Append a lifecycle event with gates; identity/role verification belongs to authorized operations."""
    base = root or INTAKE_ROOT
    if not isinstance(actor_id, str) or not actor_id.strip() or not isinstance(actor_role, str) or not actor_role.strip():
        raise IntakeError("Every lifecycle event requires a non-empty actor identity and role.")
    path, metadata, events = _load_record(submission_id, base)
    current = events[-1]["state"]
    allowed = {"received": {"validation", "quarantined"},
               "validation": {"technical_review", "quarantined"},
               "technical_review": {"specialist_review", "rejected", "quarantined"},
               "specialist_review": {"approved", "rejected", "quarantined"},
               "approved": {"active", "expired", "rejected"},
               "active": {"superseded", "expired", "quarantined"},
               "superseded": {"active"}, "expired": set(), "rejected": set(), "quarantined": set()}
    if target_state not in STATES or target_state not in allowed.get(current, set()):
        raise IntakeError(f"Invalid lifecycle transition: {current} to {target_state}.")
    if not isinstance(rationale, str) or not rationale.strip():
        raise IntakeError("Every lifecycle event requires a rationale.")
    if target_state in {"technical_review", "specialist_review", "approved", "active"}:
        if actor_id == metadata["submitter_id"]:
            raise IntakeError("Submitter and reviewer/approver must be different people.")
        if metadata["permission_status"] in {"unknown", "prohibited"} or metadata["license_status"] in {"unknown", "prohibited"}:
            raise IntakeError("Unknown or prohibited permission/licensing blocks review advancement and activation.")
    if target_state == "technical_review" and actor_role not in {"technical_reviewer", "admin"}:
        raise IntakeError("Technical review requires a technical_reviewer or admin role.")
    if target_state == "specialist_review":
        technical = next((e for e in reversed(events) if e["state"] == "technical_review"), None)
        if actor_role not in {"qualified_local_agronomist", "authorized_specialist"} or not qualification_verified:
            raise IntakeError("Specialist review requires a verified qualified specialist role.")
        if not technical or technical["actor_id"] == actor_id:
            raise IntakeError("Specialist approver must differ from technical reviewer.")
    if target_state == "approved":
        specialist = next((e for e in reversed(events) if e["state"] == "specialist_review"), None)
        if actor_role not in {"qualified_local_agronomist", "authorized_specialist"} or not qualification_verified:
            raise IntakeError("Approval requires a verified qualified specialist.")
        technical = next((e for e in reversed(events) if e["state"] == "technical_review"), None)
        if not specialist or specialist["actor_id"] == actor_id or (technical and technical["actor_id"] == actor_id):
            raise IntakeError("Approval must be performed by a specialist distinct from both prior reviewers.")
        if metadata["record_kind"] != "agronomic_guidance":
            raise IntakeError("Only original agronomic guidance may enter the farmer-guidance approval lifecycle.")
        if not metadata["guidance_categories"]:
            raise IntakeError("Guidance approval requires at least one explicit guidance category.")
        if not metadata["crops"] or not metadata["geographic_scope"] or not metadata["seasons"] or metadata["geography_type"] == "unknown":
            raise IntakeError("Guidance approval requires explicit crop, geography, and season scope.")
        if not metadata["source_locators"] or not metadata.get("effective_from") or not metadata.get("revalidate_by"):
            raise IntakeError("Guidance approval requires source locators and effective/revalidation dates.")
        if date.fromisoformat(metadata["revalidate_by"]) < date.today():
            raise IntakeError("Expired guidance cannot be approved.")
        if date.fromisoformat(metadata["effective_from"]) > date.today():
            raise IntakeError("Future-effective guidance cannot be approved yet.")
    if target_state == "active":
        if actor_role != "knowledge_administrator":
            raise IntakeError("Activation requires a knowledge_administrator.")
        if actor_id in {event.get("actor_id") for event in events if event.get("state") in {"technical_review", "specialist_review", "approved"}}:
            raise IntakeError("The activating knowledge administrator must be independent of the reviewers and approver.")
        if current == "superseded":
            approval = next((e for e in reversed(events) if e["state"] == "approved"), None)
            if not approval:
                raise IntakeError("Rollback requires a previously approved version.")
            if any(record["dataset_id"] == metadata["dataset_id"] and record["version"] != metadata["version"]
                   and record["state"] == "active" for record in list_records(root=base)):
                raise IntakeError("Supersede the currently active replacement version before rollback.")
        else:
            if not any(e["state"] == "approved" for e in events):
                raise IntakeError("Only an explicitly approved package may become active.")
            if metadata["permission_status"] != "retain_original" and not metadata.get("preservation_reference"):
                raise IntakeError("Activation requires a traceable permitted artifact reference.")
            if metadata.get("supersedes") and any(
                record["dataset_id"] == metadata["dataset_id"] and record["version"] == metadata["supersedes"]
                and record["state"] != "superseded" for record in list_records(root=base)
            ):
                raise IntakeError("The prior version must be explicitly superseded before its replacement is activated.")
    if target_state == "superseded":
        replacement = next((record for record in list_records(root=base)
                            if record["dataset_id"] == metadata["dataset_id"]
                            and record["version"] != metadata["version"]
                            and record["state"] == "approved"), None)
        if not replacement:
            raise IntakeError("Supersession requires a separately approved replacement version.")
        _, replacement_metadata, _ = _load_record(replacement["submission_id"], base)
        if replacement_metadata.get("supersedes") != metadata["version"]:
            raise IntakeError("Replacement metadata must explicitly identify the version it supersedes.")
    event = {"event_id": str(uuid.uuid4()), "state": target_state, "actor_id": actor_id,
             "actor_role": actor_role, "qualification_verified": bool(qualification_verified),
             "occurred_at": datetime.now(timezone.utc).isoformat(), "reason": rationale.strip(),
             "previous_event_sha256": events[-1]["event_sha256"]}
    event["event_sha256"] = _event_digest(event)
    events.append(event)
    temporary = path / (".events-" + uuid.uuid4().hex + ".tmp")
    with temporary.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(events, ensure_ascii=False, indent=2) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path / "events.json")
    return {"submission_id": submission_id, "previous_state": current, "state": target_state}


def list_records(*, root: Path | None = None) -> list[dict[str, Any]]:
    base = root or INTAKE_ROOT
    records = []
    directory = base / "records"
    if directory.is_symlink():
        raise IntakeError("Intake records directory must not be a symbolic link.")
    for folder in sorted(directory.glob("*")) if directory.exists() else []:
        if folder.name.startswith(".staging-"):
            continue
        if folder.is_symlink():
            records.append({"submission_id": folder.name, "dataset_id": None, "version": None,
                            "kind": None, "state": "invalid", "artifact_sha256": None,
                            "integrity": "invalid", "integrity_findings": ["submission_path_is_symlink"]})
            continue
        if not folder.is_dir():
            continue
        if (folder / ".publication_pending").exists():
            continue
        try:
            metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
            events = json.loads((folder / "events.json").read_text(encoding="utf-8"))
            integrity = verify_record(folder, metadata, events)
            records.append({"submission_id": folder.name, "dataset_id": metadata.get("dataset_id"),
                            "version": metadata.get("version"), "kind": metadata.get("record_kind"),
                            "state": events[-1].get("state", "invalid") if events else "invalid",
                            "artifact_sha256": metadata.get("artifact", {}).get("sha256"),
                            "integrity": "valid" if not integrity else "invalid",
                            "integrity_findings": integrity})
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, AttributeError, KeyError):
            records.append({"submission_id": folder.name, "dataset_id": None, "version": None,
                            "kind": None, "state": "invalid", "artifact_sha256": None,
                            "integrity": "invalid", "integrity_findings": ["package_metadata_or_events_invalid"]})
    return records


def coverage_report(*, root: Path | None = None, today: date | None = None) -> dict[str, Any]:
    """Report only active, in-date reviewed guidance; pending/intake data never counts."""
    today = today or date.today()
    base = root or INTAKE_ROOT
    crops: dict[str, dict[str, Any]] = {}
    categories: dict[str, set[str]] = {}
    sources: set[str] = set()
    seasons: set[str] = set()
    covered_districts: set[str] = set()
    active_guidance = 0
    for row in list_records(root=base):
        if row["integrity"] != "valid" or row["kind"] != "agronomic_guidance" or row["state"] != "active":
            continue
        _, metadata, _ = _load_record(row["submission_id"], base)
        try:
            if date.fromisoformat(metadata["effective_from"]) > today or date.fromisoformat(metadata["revalidate_by"]) < today:
                continue
        except (KeyError, TypeError, ValueError):
            continue
        active_guidance += 1
        source = metadata["source_organization"]
        sources.add(source)
        seasons.update(metadata["seasons"])
        for category in metadata["guidance_categories"]:
            categories.setdefault(category, set()).add(source)
        districts: set[str] = set()
        if metadata["geography_type"] == "national":
            districts.update(ALL_DISTRICTS)
        elif metadata["geography_type"] == "district":
            normalized = {district.casefold(): district for district in ALL_DISTRICTS}
            districts.update(normalized[name.casefold()] for name in metadata["geographic_scope"] if name.casefold() in normalized)
        covered_districts.update(districts)
        for crop in metadata["crops"]:
            entry = crops.setdefault(crop, {"sources": set(), "categories": set(), "seasons": set(), "districts": set()})
            entry["sources"].add(source)
            entry["categories"].update(metadata["guidance_categories"])
            entry["seasons"].update(metadata["seasons"])
            entry["districts"].update(districts)
            entry.setdefault("varieties", set()).update(metadata["varieties"])
            entry.setdefault("soil_scope", set()).update(metadata["soil_scope"])
            entry.setdefault("production_systems", set()).update(metadata["production_systems"])
            entry.setdefault("conditions", set()).update(json.dumps(item, sort_keys=True, ensure_ascii=False) for item in metadata["conditions"])
            entry.setdefault("geographic_scopes", set()).update(
                f"{metadata['geography_type']}:{scope}" for scope in metadata["geographic_scope"])
    return {
        "as_of": today.isoformat(), "active_current_guidance_packages": active_guidance,
        "districts_total": len(ALL_DISTRICTS), "districts_with_active_guidance": sorted(covered_districts),
        "districts_without_active_guidance": sorted(set(ALL_DISTRICTS) - covered_districts),
        "sources": sorted(sources), "categories": {key: sorted(value) for key, value in sorted(categories.items())},
        "seasons": sorted(seasons),
        "by_crop": {key: {name: sorted(value) for name, value in entry.items()} for key, entry in sorted(crops.items())},
        "note": "Only integrity-valid, active, in-date agronomic guidance packages count. Statistics, weather, unverified submissions, and test fixtures do not count unless deliberately promoted through a real approved lifecycle.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Local operator-only agronomic evidence intake; never publishes farmer guidance.")
    sub = parser.add_subparsers(dest="command", required=True)
    receive_parser = sub.add_parser("receive")
    receive_parser.add_argument("--file", required=True)
    receive_parser.add_argument("--metadata", required=True)
    transition_parser = sub.add_parser("transition")
    transition_parser.add_argument("--id", required=True)
    transition_parser.add_argument("--state", required=True, choices=sorted(STATES))
    transition_parser.add_argument("--actor-id", required=True)
    transition_parser.add_argument("--actor-role", required=True)
    transition_parser.add_argument("--rationale", required=True)
    transition_parser.add_argument("--qualification-verified", action="store_true",
                                   help="Operator attestation only; not an identity or qualification verification service.")
    sub.add_parser("list")
    sub.add_parser("coverage")
    args = parser.parse_args()
    try:
        if args.command == "receive":
            result = receive(args.file, json.loads(Path(args.metadata).read_text(encoding="utf-8")))
        elif args.command == "transition":
            result = transition(args.id, args.state, actor_id=args.actor_id, actor_role=args.actor_role,
                                rationale=args.rationale, qualification_verified=args.qualification_verified)
        elif args.command == "coverage":
            result = coverage_report()
        else:
            result = list_records()
    except (OSError, json.JSONDecodeError, IntakeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
