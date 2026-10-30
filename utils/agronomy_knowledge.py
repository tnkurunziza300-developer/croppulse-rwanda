"""Validate and report the version-controlled CropPulse agronomic knowledge pack.

This registry intentionally does not convert NISR statistics or source descriptions
into recommendations. It uses only Python's standard library plus existing project
modules; it never connects to the application database.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from knowledge import CROPS
from utils.geography import ALL_DISTRICTS

ROOT = Path(__file__).resolve().parents[1]
PACK_DIR = ROOT / "data" / "agronomy"
DATASET_VERSION = "0.1.0"
SOURCES_PATH = PACK_DIR / "sources.json"
STATEMENTS_PATH = PACK_DIR / "statements.json"
RULES_PATH = PACK_DIR / "rules.json"
DECISIONS_PATH = PACK_DIR / "review_decisions.json"
ISSUES_PATH = PACK_DIR / "quality_issues.json"
SCHEMA_PATH = PACK_DIR / "schema.json"
STATES = {"draft", "evidence_collected", "technical_review", "local_specialist_review",
          "approved", "rejected", "expired", "withdrawn", "superseded", "quarantined"}
REVIEW_STATES = {"not_reviewed", "technical_review_pending", "local_specialist_review_pending",
                 "approved_for_scope", "rejected", "expired", "withdrawn", "superseded"}
CATEGORIES = {"crop_suitability", "planting", "soil", "fertilizer", "water",
              "crop_management", "pest_disease", "other"}
# No authenticated qualification/approval trust anchor exists in this local
# registry. Operator-entered JSON attestations are not sufficient to activate
# guidance. Keep this disabled until an authenticated decision mechanism exists.
APPROVAL_TRUST_ANCHOR_CONFIGURED = False
SUPPORTED_THRESHOLD_UNITS = {"%", "mm", "cm", "m", "m2", "ha", "kg", "g",
                             "kg/ha", "g/ha", "t/ha", "L", "mL", "L/ha",
                             "mL/L", "°C", "pH", "days", "days_after_planting"}


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema_version") != "1.0":
        raise ValueError(f"{path.relative_to(ROOT)} must be a schema_version 1.0 object")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _valid_iso_date(value: Any, *, nullable: bool = False) -> bool:
    if value is None:
        return nullable
    if not isinstance(value, str):
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _condition_is_valid(condition: Any) -> bool:
    if not isinstance(condition, dict):
        return False
    parameter, operator = condition.get("parameter"), condition.get("operator")
    if not isinstance(parameter, str) or not parameter.strip():
        return False
    if not isinstance(operator, str) or operator not in {"eq", "ne", "in", "not_in", "gt", "gte", "lt", "lte"}:
        return False
    unit = condition.get("unit")
    unit_ok = isinstance(unit, str) and unit in SUPPORTED_THRESHOLD_UNITS
    if set(condition) - {"parameter", "operator", "value", "unit"} or "value" not in condition:
        return False
    value = condition["value"]
    if operator in {"gt", "gte", "lt", "lte"}:
        return (isinstance(value, (int, float)) and not isinstance(value, bool)
                and math.isfinite(value) and unit_ok)
    if operator in {"in", "not_in"}:
        if not isinstance(value, list) or not value:
            return False
        if not all(type(item) in {str, int, float, bool} for item in value):
            return False
        if any(isinstance(item, float) and not math.isfinite(item) for item in value):
            return False
        if any(isinstance(item, (int, float)) and not isinstance(item, bool) for item in value):
            return unit_ok
        return "unit" not in condition or unit_ok
    if not (value is None or type(value) in {str, int, float, bool}):
        return False
    if isinstance(value, float) and not math.isfinite(value):
        return False
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return unit_ok
    return "unit" not in condition or unit_ok


def _source_content_matches(source: dict[str, Any], *, root: Path = ROOT) -> bool:
    """Verify an optional repository-relative source artifact without following escapes."""
    content_path, expected_hash = source.get("content_path"), source.get("content_sha256")
    if not isinstance(content_path, str) or not content_path.strip() or not isinstance(expected_hash, str):
        return False
    root = root.resolve()
    unresolved = root / content_path
    if unresolved.is_symlink():
        return False
    candidate = unresolved.resolve()
    try:
        candidate.relative_to(root)
        return candidate.is_file() and _sha256(candidate) == expected_hash
    except (OSError, ValueError):
        return False


def _schema_errors(value: Any, schema: dict[str, Any], root_schema: dict[str, Any], path: str = "$root") -> list[str]:
    """Validate the JSON Schema subset used by schema.json without a new dependency."""
    reference = schema.get("$ref")
    if reference:
        if not isinstance(reference, str) or not reference.startswith("#/definitions/"):
            return [f"{path}: unsupported schema reference"]
        target: Any = root_schema
        for part in reference[2:].split("/"):
            target = target.get(part) if isinstance(target, dict) else None
        if not isinstance(target, dict):
            return [f"{path}: unresolved schema reference"]
        return _schema_errors(value, target, root_schema, path)

    errors: list[str] = []
    expected = schema.get("type")
    if expected:
        expected_types = expected if isinstance(expected, list) else [expected]
        matches = False
        for kind in expected_types:
            matches |= {
                "object": isinstance(value, dict),
                "array": isinstance(value, list),
                "string": isinstance(value, str),
                "boolean": type(value) is bool,
                "null": value is None,
                "integer": isinstance(value, int) and type(value) is not bool,
                "number": isinstance(value, (int, float)) and type(value) is not bool
                          and (not isinstance(value, float) or math.isfinite(value)),
            }.get(kind, False)
        if not matches:
            return [f"{path}: expected {expected}"]
    if "const" in schema and (type(value) is not type(schema["const"]) or value != schema["const"]):
        errors.append(f"{path}: value does not match the required constant")
    if "enum" in schema and not any(type(value) is type(item) and value == item for item in schema["enum"]):
        errors.append(f"{path}: value is outside the permitted set")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{path}: string is shorter than permitted")
        if "pattern" in schema and re.fullmatch(schema["pattern"], value) is None:
            errors.append(f"{path}: string does not match the required format")
        if schema.get("format") == "date" and not _valid_iso_date(value):
            errors.append(f"{path}: invalid ISO date")
    if isinstance(value, dict):
        missing = set(schema.get("required", [])) - value.keys()
        errors.extend(f"{path}: required field {key} is missing" for key in sorted(missing))
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            errors.extend(f"{path}: unsupported field {key}" for key in sorted(value.keys() - properties.keys()))
        for key, child in properties.items():
            if key in value and isinstance(child, dict):
                errors.extend(_schema_errors(value[key], child, root_schema, f"{path}.{key}"))
    if isinstance(value, list) and isinstance(schema.get("items"), dict):
        for index, item in enumerate(value):
            errors.extend(_schema_errors(item, schema["items"], root_schema, f"{path}[{index}]"))
    return errors


def _dataset_integrity(findings: list[dict[str, str]]) -> dict[str, Any]:
    manifest_path = ROOT / "data" / "verified" / "MANIFEST.json"
    csv_path = ROOT / "data" / "verified" / "nisr_sas_2023_2026.csv"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        item = next(item for item in manifest["files"] if item.get("file") == csv_path.name)
        actual_hash = _sha256(csv_path)
        with csv_path.open(encoding="utf-8-sig", newline="") as stream:
            row_count = sum(1 for _ in csv.DictReader(stream))
        if actual_hash != item.get("sha256"):
            findings.append({"severity": "error", "code": "nisr_checksum_mismatch",
                             "message": "The NISR CSV checksum does not match its existing manifest."})
        if row_count != item.get("quality_report", {}).get("rows_written"):
            findings.append({"severity": "error", "code": "nisr_row_count_mismatch",
                             "message": "The NISR CSV row count does not match its existing manifest."})
        return {"dataset": csv_path.relative_to(ROOT).as_posix(), "publisher": item.get("publisher"),
                "row_count": row_count, "sha256": actual_hash,
                "integrity": "valid" if actual_hash == item.get("sha256") and row_count == item.get("quality_report", {}).get("rows_written") else "invalid",
                "use_boundary": "historical statistics only; not an agronomic guidance source"}
    except (OSError, KeyError, StopIteration, ValueError, TypeError, json.JSONDecodeError) as exc:
        findings.append({"severity": "error", "code": "nisr_manifest_validation_failed",
                         "message": f"Could not verify the existing NISR dataset against its manifest ({type(exc).__name__})."})
        return {"dataset": csv_path.relative_to(ROOT).as_posix(), "integrity": "invalid"}


def validate_pack(*, today: date | None = None) -> dict[str, Any]:
    """Validate IDs, source links, citations, approval gates, scope, and dataset hashes."""
    today = today or date.today()
    findings: list[dict[str, str]] = []
    try:
        sources_doc = _read(SOURCES_PATH)
        statements_doc = _read(STATEMENTS_PATH)
        rules_doc = _read(RULES_PATH)
        decisions_doc = _read(DECISIONS_PATH)
        issues_doc = _read(ISSUES_PATH)
        schema_doc = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        if not isinstance(schema_doc, dict) or not schema_doc.get("$schema", "").endswith("/2020-12/schema"):
            raise ValueError("schema.json must declare JSON Schema 2020-12")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return {"dataset_version": DATASET_VERSION, "valid": False,
                "findings": [{"severity": "error", "code": "registry_load_failed",
                              "message": f"Knowledge registry could not be loaded ({type(exc).__name__})."}]}

    sources = sources_doc.get("sources")
    statements = statements_doc.get("statements")
    rules = rules_doc.get("rules")
    decisions = decisions_doc.get("decisions")
    issues = issues_doc.get("issues")
    for name, rows in (("sources", sources), ("statements", statements), ("rules", rules), ("decisions", decisions), ("issues", issues)):
        if not isinstance(rows, list):
            findings.append({"severity": "error", "code": "invalid_collection", "message": f"{name} must be an array."})
    if any(not isinstance(rows, list) for rows in (sources, statements, rules, decisions, issues)):
        return {"dataset_version": DATASET_VERSION, "valid": False, "findings": findings}

    registry_document = {"schema_version": "1.0", "sources": sources, "statements": statements,
                         "rules": rules, "decisions": decisions, "issues": issues}
    schema_errors = _schema_errors(registry_document, schema_doc, schema_doc)
    for problem in schema_errors[:25]:
        findings.append({"severity": "error", "code": "strict_schema_validation_failed", "message": problem})
    if len(schema_errors) > 25:
        findings.append({"severity": "error", "code": "strict_schema_validation_failed",
                         "message": f"Additional schema errors omitted: {len(schema_errors) - 25}."})

    source_ids: set[str] = set()
    source_by_id: dict[str, dict[str, Any]] = {}
    source_required = {"source_id", "organization", "title", "source_type", "url", "language",
                       "reference", "geographic_scope", "intended_use", "reuse_status", "verification_status"}
    for source in sources:
        if not isinstance(source, dict) or not source_required.issubset(source):
            findings.append({"severity": "error", "code": "source_missing_fields", "message": "A source record is malformed or missing required provenance fields."})
            continue
        source_id = source["source_id"]
        if not isinstance(source_id, str) or not source_id.strip():
            findings.append({"severity": "error", "code": "invalid_source_id", "message": "Source IDs must be non-empty strings."})
            continue
        source_fields = {"source_id", "organization", "title", "source_type", "url", "publication_date",
                         "version", "accessed_date", "language", "reference", "geographic_scope", "crops",
                         "varieties", "seasons", "source_authority", "intended_use", "reuse_status",
                         "verification_status", "content_sha256", "reviewer_notes", "content_path"}
        if set(source) - source_fields:
            findings.append({"severity": "error", "code": "unknown_source_fields", "message": f"Source {source_id} contains unsupported fields."})
        if source_id in source_ids:
            findings.append({"severity": "error", "code": "duplicate_source_id", "message": f"Duplicate source ID: {source_id}."})
        source_ids.add(source_id)
        source_by_id[source_id] = source
        if not all(isinstance(source.get(key), str) and source[key].strip()
                   for key in ("organization", "title", "source_type", "url", "language",
                               "reference", "geographic_scope", "intended_use", "reuse_status",
                               "verification_status")):
            findings.append({"severity": "error", "code": "invalid_source_fields", "message": f"Source {source_id} contains an empty or malformed provenance field."})
            continue
        parsed = urlparse(source["url"])
        if parsed.scheme not in {"https", "http"} or not parsed.netloc:
            findings.append({"severity": "error", "code": "invalid_source_url", "message": f"Source {source_id} has an invalid URL."})
        content_hash = source.get("content_sha256")
        if content_hash is not None and (not isinstance(content_hash, str) or len(content_hash) != 64
                                         or any(c not in "0123456789abcdef" for c in content_hash)):
            findings.append({"severity": "error", "code": "invalid_source_checksum", "message": f"Source {source_id} has an invalid SHA-256 value."})
        if source.get("publication_date") is not None and not _valid_iso_date(source["publication_date"]):
            findings.append({"severity": "error", "code": "invalid_source_publication_date", "message": f"Source {source_id} has an invalid publication date."})
        if source.get("accessed_date") is not None and not _valid_iso_date(source["accessed_date"]):
            findings.append({"severity": "error", "code": "invalid_source_access_date", "message": f"Source {source_id} has an invalid access date."})
        content_path = source.get("content_path")
        if content_path is not None:
            if not _source_content_matches(source):
                findings.append({"severity": "error", "code": "source_file_provenance_incomplete", "message": f"Source {source_id} local content requires a relative path and SHA-256."})
            if content_hash is not None and not _source_content_matches(source):
                findings.append({"severity": "error", "code": "source_file_integrity_failed", "message": f"Source {source_id} local content is missing, outside the repository, or has changed."})

    statement_ids: set[str] = set()
    for statement in statements:
        if not isinstance(statement, dict) or not {"statement_id", "source_id", "reference", "paraphrase", "scope", "limitations"}.issubset(statement):
            findings.append({"severity": "error", "code": "statement_missing_fields", "message": "A source statement is malformed or missing its citation/scope."})
            continue
        if set(statement) - {"statement_id", "source_id", "statement_type", "reference", "paraphrase", "scope", "limitations"}:
            findings.append({"severity": "error", "code": "unknown_statement_fields", "message": "A source statement contains unsupported fields."})
        if not all(isinstance(statement.get(key), str) and statement[key].strip()
                   for key in ("statement_id", "source_id", "reference", "paraphrase", "scope", "limitations")):
            findings.append({"severity": "error", "code": "invalid_statement_fields", "message": "Statement IDs, source IDs, references, and paraphrases must be non-empty strings."})
            continue
        if statement["statement_id"] in statement_ids:
            findings.append({"severity": "error", "code": "duplicate_statement_id", "message": f"Duplicate statement ID: {statement['statement_id']}."})
        statement_ids.add(statement["statement_id"])
        if statement["source_id"] not in source_ids:
            findings.append({"severity": "error", "code": "unknown_statement_source", "message": f"Statement {statement['statement_id']} references an unknown source."})
        if not statement["reference"].strip() or not statement["paraphrase"].strip():
            findings.append({"severity": "error", "code": "empty_statement_citation", "message": f"Statement {statement['statement_id']} needs a locator and faithful paraphrase."})

    decision_index: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for decision in decisions:
        if not isinstance(decision, dict) or not {"rule_id", "rule_version", "decision", "reviewer_id", "reviewer_role", "decision_date", "rationale"}.issubset(decision):
            findings.append({"severity": "error", "code": "invalid_review_decision", "message": "A review decision is missing its identity, role, date, or rationale."})
            continue
        if set(decision) - {"rule_id", "rule_version", "decision", "reviewer_id", "reviewer_role",
                            "qualification_verified", "decision_date", "rationale", "supersedes_decision_id"}:
            findings.append({"severity": "error", "code": "unknown_review_fields", "message": "A review decision contains unsupported fields."})
        if not _valid_iso_date(decision["decision_date"]):
            findings.append({"severity": "error", "code": "invalid_review_date", "message": f"Review decision for {decision['rule_id']} has an invalid date."})
        if (not isinstance(decision["rule_id"], str) or not decision["rule_id"].strip()
                or not isinstance(decision["rule_version"], str) or not decision["rule_version"].strip()
                or not isinstance(decision["reviewer_id"], str) or not decision["reviewer_id"].strip()
                or not isinstance(decision["reviewer_role"], str) or not decision["reviewer_role"].strip()
                or not isinstance(decision["rationale"], str) or not decision["rationale"].strip()
                or type(decision.get("qualification_verified", False)) is not bool):
            findings.append({"severity": "error", "code": "invalid_review_identity", "message": "Review rule IDs and versions must be strings."})
            continue
        if not isinstance(decision["decision"], str) or decision["decision"] not in {
                "evidence_collected", "technical_review", "local_specialist_review", "approved",
                "rejected", "expired", "withdrawn", "superseded", "quarantined"}:
            findings.append({"severity": "error", "code": "invalid_review_state", "message": f"Review decision for {decision['rule_id']} has an unsupported state."})
        if decision.get("decision") == "approved" and not APPROVAL_TRUST_ANCHOR_CONFIGURED:
            findings.append({"severity": "error", "code": "approval_identity_unverifiable",
                             "message": "Local review JSON cannot authenticate the reviewer identity or verify agricultural qualifications."})
        decision_index.setdefault((decision["rule_id"], decision["rule_version"]), []).append(decision)

    for identity in decision_index:
        if not any(isinstance(rule, dict) and (rule.get("rule_id"), rule.get("version")) == identity for rule in rules):
            findings.append({"severity": "error", "code": "review_references_missing_rule",
                             "message": f"A review decision references missing rule version {identity[0]} {identity[1]}."})

    issue_ids: set[str] = set()
    for issue in issues:
        if not isinstance(issue, dict) or not {"issue_id", "category", "severity", "status", "description", "required_action", "recorded_at"}.issubset(issue):
            findings.append({"severity": "error", "code": "invalid_quality_issue", "message": "A quality issue is missing its identity, category, status, description, or action."})
            continue
        if not isinstance(issue["issue_id"], str) or not issue["issue_id"].strip():
            findings.append({"severity": "error", "code": "invalid_quality_issue_id", "message": "Quality issue IDs must be non-empty strings."})
            continue
        if issue["issue_id"] in issue_ids:
            findings.append({"severity": "error", "code": "duplicate_quality_issue_id", "message": f"Duplicate quality issue ID: {issue['issue_id']}."})
        issue_ids.add(issue["issue_id"])
        if not isinstance(issue["status"], str) or issue["status"] not in {"open", "in_progress", "resolved", "quarantined"}:
            findings.append({"severity": "error", "code": "invalid_quality_issue_status", "message": f"Issue {issue['issue_id']} has an unsupported status."})
        if set(issue) - {"issue_id", "category", "severity", "status", "related_source_ids", "related_rule_ids",
                         "description", "required_action", "recorded_at", "resolution", "resolved_at"}:
            findings.append({"severity": "error", "code": "unknown_quality_issue_fields", "message": f"Issue {issue['issue_id']} contains unsupported fields."})
        if not all(isinstance(issue.get(key, []), list) and all(isinstance(value, str) for value in issue.get(key, []))
                   for key in ("related_source_ids", "related_rule_ids")):
            findings.append({"severity": "error", "code": "invalid_quality_issue_references", "message": f"Issue {issue['issue_id']} references must be string arrays."})
        elif set(issue.get("related_source_ids", [])) - source_ids:
            findings.append({"severity": "error", "code": "unknown_issue_source", "message": f"Issue {issue['issue_id']} references an unknown source."})
        if not _valid_iso_date(issue.get("recorded_at")):
            findings.append({"severity": "error", "code": "invalid_quality_issue_date", "message": f"Issue {issue['issue_id']} has an invalid recorded date."})
        if issue["status"] == "resolved":
            if not isinstance(issue.get("resolution"), str) or not issue["resolution"].strip():
                findings.append({"severity": "error", "code": "resolved_issue_missing_evidence", "message": f"Resolved issue {issue['issue_id']} needs documented resolution and verification evidence."})
            if not _valid_iso_date(issue.get("resolved_at")):
                findings.append({"severity": "error", "code": "resolved_issue_missing_date", "message": f"Resolved issue {issue['issue_id']} needs a valid resolution date."})

    rule_ids: set[tuple[str, str]] = set()
    approved_scope_keys: set[tuple[Any, ...]] = set()
    rule_versions: dict[str, set[str]] = {}
    required_rule_fields = {"rule_id", "version", "category", "status", "crop", "geography", "season_scope",
                            "variety", "production_system", "recommendation", "conditions", "source_references",
                            "limitations", "review_status", "effective_from", "revalidate_by", "change_history"}
    for rule in rules:
        if not isinstance(rule, dict) or not required_rule_fields.issubset(rule):
            findings.append({"severity": "error", "code": "rule_missing_fields", "message": "An agronomic rule is malformed or missing required scope/review fields."})
            continue
        if not isinstance(rule["rule_id"], str) or not rule["rule_id"].strip() or not isinstance(rule["version"], str) or not rule["version"].strip():
            findings.append({"severity": "error", "code": "invalid_rule_identity", "message": "Rule IDs and versions must be non-empty strings."})
            continue
        identity = (rule["rule_id"], rule["version"])
        allowed_rule_fields = required_rule_fields | {"parameters", "product_registration", "confidence_method", "supersedes"}
        if set(rule) - allowed_rule_fields:
            findings.append({"severity": "error", "code": "unknown_rule_fields", "message": f"Rule {identity[0]} contains unsupported fields."})
        if identity in rule_ids:
            findings.append({"severity": "error", "code": "duplicate_rule_version", "message": f"Duplicate rule/version: {identity[0]} {identity[1]}."})
        rule_ids.add(identity)
        rule_versions.setdefault(identity[0], set()).add(identity[1])
        if not isinstance(rule["status"], str) or rule["status"] not in STATES or not isinstance(rule["category"], str) or rule["category"] not in CATEGORIES:
            findings.append({"severity": "error", "code": "invalid_rule_state", "message": f"Rule {identity[0]} has an unknown status or category."})
        for field in ("crop", "variety", "production_system", "recommendation"):
            if rule[field] is not None and not isinstance(rule[field], str):
                findings.append({"severity": "error", "code": "invalid_rule_text_field", "message": f"Rule {identity[0]} has a malformed {field} field."})
        if not isinstance(rule["review_status"], str) or rule["review_status"] not in REVIEW_STATES:
            findings.append({"severity": "error", "code": "invalid_rule_review_status", "message": f"Rule {identity[0]} has an unsupported review status."})
        geography = rule["geography"]
        if not isinstance(geography, dict) or geography.get("type") not in {"national", "province", "district", "sector", "site", "unknown"}:
            findings.append({"severity": "error", "code": "invalid_rule_geography", "message": f"Rule {identity[0]} must state a supported geography type."})
            geography = {"type": "unknown", "scope": []}
        if not isinstance(geography.get("scope", []), list) or not all(isinstance(s, str) for s in geography.get("scope", [])):
            findings.append({"severity": "error", "code": "invalid_geographic_scope", "message": f"Rule {identity[0]} geographic scope must be an array of names."})
            geography["scope"] = []
        if geography.get("type") == "district":
            invalid = set(geography.get("scope", [])) - set(ALL_DISTRICTS)
            if invalid:
                findings.append({"severity": "error", "code": "unknown_district_scope", "message": f"Rule {identity[0]} contains an unrecognized district."})
        if not isinstance(rule["season_scope"], list) or not all(isinstance(s, str) for s in rule["season_scope"]):
            findings.append({"severity": "error", "code": "invalid_season_scope", "message": f"Rule {identity[0]} season_scope must be an array."})
            rule["season_scope"] = []
        if set(rule["season_scope"]) - {"A", "B", "C"}:
            findings.append({"severity": "error", "code": "invalid_season_scope", "message": f"Rule {identity[0]} contains an unrecognized season."})
        if not isinstance(rule["conditions"], list) or not isinstance(rule["limitations"], list):
            findings.append({"severity": "error", "code": "invalid_rule_conditions", "message": f"Rule {identity[0]} conditions and limitations must be arrays."})
            rule["conditions"] = rule["conditions"] if isinstance(rule["conditions"], list) else []
            rule["limitations"] = rule["limitations"] if isinstance(rule["limitations"], list) else []
        for condition in rule["conditions"]:
            if not _condition_is_valid(condition):
                findings.append({"severity": "error", "code": "invalid_rule_condition",
                                 "message": f"Rule {identity[0]} contains a malformed threshold, unsupported unit, or condition that cannot be evaluated safely."})
        parameters = rule.get("parameters", [])
        if not isinstance(parameters, list):
            findings.append({"severity": "error", "code": "invalid_rule_parameters", "message": f"Rule {identity[0]} parameters must be an array."})
            parameters = []
        for parameter in parameters:
            if (not isinstance(parameter, dict) or not isinstance(parameter.get("name"), str)
                    or not parameter["name"].strip() or "value" not in parameter
                    or not isinstance(parameter.get("unit"), str) or not parameter["unit"].strip()):
                findings.append({"severity": "error", "code": "invalid_rule_parameters", "message": f"Rule {identity[0]} has an ambiguous parameter or missing unit."})
        for field in ("effective_from", "revalidate_by"):
            if rule[field] is not None and not _valid_iso_date(rule[field]):
                findings.append({"severity": "error", "code": "invalid_rule_date", "message": f"Rule {identity[0]} has an invalid {field} date."})
        if (rule["effective_from"] is not None and rule["revalidate_by"] is not None
                and _valid_iso_date(rule["effective_from"]) and _valid_iso_date(rule["revalidate_by"])
                and date.fromisoformat(rule["effective_from"]) > date.fromisoformat(rule["revalidate_by"])):
            findings.append({"severity": "error", "code": "inconsistent_rule_dates", "message": f"Rule {identity[0]} expires before it becomes effective."})
        refs = rule["source_references"]
        if not isinstance(refs, list):
            findings.append({"severity": "error", "code": "invalid_rule_references", "message": f"Rule {identity[0]} source_references must be an array."})
            refs = []
        for ref in refs:
            if (not isinstance(ref, dict) or not {"source_id", "locator", "paraphrase"}.issubset(ref)
                    or set(ref) - {"source_id", "locator", "paraphrase"}):
                findings.append({"severity": "error", "code": "incomplete_rule_citation", "message": f"Rule {identity[0]} has an incomplete source citation."})
                continue
            cited_source = source_by_id.get(ref["source_id"]) if isinstance(ref["source_id"], str) else None
            if cited_source is None:
                findings.append({"severity": "error", "code": "unknown_rule_source", "message": f"Rule {identity[0]} references an unknown source."})
            elif cited_source["source_type"] == "verified_statistical_dataset":
                findings.append({"severity": "error", "code": "statistics_used_as_agronomy", "message": f"Rule {identity[0]} cannot use a statistical dataset as crop-management evidence."})
            if (not isinstance(ref["source_id"], str) or not ref["source_id"].strip()
                    or not isinstance(ref["locator"], str) or not ref["locator"].strip()
                    or not isinstance(ref["paraphrase"], str) or not ref["paraphrase"].strip()):
                findings.append({"severity": "error", "code": "empty_rule_locator", "message": f"Rule {identity[0]} requires a precise source locator and paraphrase."})
        if rule["status"] == "approved":
            findings.append({"severity": "error", "code": "approval_identity_unverifiable",
                             "message": f"Rule {identity[0]} cannot be activated from local JSON attestations; authenticated reviewer and qualification verification are not configured."})
            if (rule["review_status"] != "approved_for_scope" or not refs or not rule["limitations"]
                    or not rule.get("crop") or not rule.get("season_scope") or geography.get("type") == "unknown"):
                findings.append({"severity": "error", "code": "approval_gate_failed", "message": f"Approved rule {identity[0]} lacks scope review, citations, or limitations."})
            for ref in refs:
                if not isinstance(ref, dict):
                    continue
                cited_source = source_by_id.get(ref.get("source_id"))
                if cited_source and "not_accessible" in cited_source.get("verification_status", ""):
                    findings.append({"severity": "error", "code": "approved_rule_uses_unavailable_source", "message": f"Approved rule {identity[0]} cites source content that was not accessible."})
            if rule["category"] in {"soil", "fertilizer"}:
                condition_names = {str(c.get("parameter", "")).casefold() for c in rule.get("conditions", []) if isinstance(c, dict)}
                if not condition_names & {"soil", "soil_test", "soil_type", "soil_property", "pH", "upi"}:
                    findings.append({"severity": "error", "code": "soil_context_missing", "message": f"Approved {rule['category']} rule {identity[0]} must state applicable soil context."})
                if rule["category"] == "fertilizer":
                    for parameter in rule.get("parameters", []):
                        if not isinstance(parameter, dict) or not parameter.get("unit"):
                            findings.append({"severity": "error", "code": "fertilizer_unit_missing", "message": f"Fertilizer rule {identity[0]} has a parameter without units."})
                        elif parameter.get("rate_basis") in {None, ""}:
                            findings.append({"severity": "error", "code": "fertilizer_rate_basis_missing", "message": f"Fertilizer parameter in {identity[0]} must identify its rate basis."})
            if rule["category"] == "pest_disease":
                treatment_words = ("pesticide", "insecticide", "fungicide", "herbicide", "chemical", "dosage", "dose")
                advice = (rule.get("recommendation") or "").casefold()
                if any(word in advice for word in treatment_words) and not rule.get("product_registration"):
                    findings.append({"severity": "error", "code": "plant_protection_registration_missing", "message": f"Plant-protection rule {identity[0]} needs current product/legal-use evidence before approval."})
            reviewer_decisions = decision_index.get(identity, [])
            if not reviewer_decisions:
                findings.append({"severity": "error", "code": "local_review_missing", "message": f"Approved rule {identity[0]} lacks a separately recorded local review decision."})
            elif not any(d.get("decision") == "approved" and d.get("reviewer_role") == "qualified_local_agronomist"
                         and d.get("qualification_verified") is True for d in reviewer_decisions):
                findings.append({"severity": "error", "code": "local_review_missing", "message": f"Approved rule {identity[0]} lacks the required local reviewer attestation; this attestation alone cannot verify identity or qualifications."})
            else:
                dated = [(date.fromisoformat(d["decision_date"]), index, d)
                         for index, d in enumerate(reviewer_decisions) if _valid_iso_date(d.get("decision_date"))]
                if dated and max(dated, key=lambda item: (item[0], item[1]))[2].get("decision") != "approved":
                    findings.append({"severity": "error", "code": "approval_revoked_by_later_decision",
                                     "message": f"Rule {identity[0]} has a later non-approval review decision."})
                technical = [d for d in reviewer_decisions if d.get("decision") == "technical_review"]
                specialist = [d for d in reviewer_decisions if d.get("decision") == "local_specialist_review"
                              and d.get("reviewer_role") in {"qualified_local_agronomist", "authorized_specialist"}
                              and d.get("qualification_verified") is True]
                approval = next((d for d in reversed(reviewer_decisions)
                                 if d.get("decision") == "approved"), None)
                if (not technical or not specialist or not approval
                        or len({technical[-1].get("reviewer_id"), specialist[-1].get("reviewer_id"),
                                approval.get("reviewer_id")}) != 3):
                    findings.append({"severity": "error", "code": "review_sequence_or_separation_failed",
                                     "message": f"Rule {identity[0]} lacks a distinct technical reviewer, specialist reviewer, and approver in sequence."})
            try:
                revalidate = date.fromisoformat(rule["revalidate_by"])
                effective = date.fromisoformat(rule["effective_from"])
                if revalidate < today or effective > today:
                    findings.append({"severity": "error", "code": "approved_rule_out_of_date", "message": f"Approved rule {identity[0]} is expired or not yet effective."})
            except (TypeError, ValueError):
                findings.append({"severity": "error", "code": "approved_rule_missing_dates", "message": f"Approved rule {identity[0]} needs valid effective/revalidation dates."})
            key = (rule["category"], rule["crop"], tuple(rule["season_scope"]), geography.get("type"), tuple(geography.get("scope", [])), rule["production_system"])
            if key in approved_scope_keys:
                findings.append({"severity": "warning", "code": "overlapping_approved_scope", "message": f"Multiple approved rules may overlap for {identity[0]} scope; manual conflict review is required."})
            approved_scope_keys.add(key)

    for rule_id, versions in rule_versions.items():
        active_versions = [rule for rule in rules if isinstance(rule, dict) and rule.get("rule_id") == rule_id
                           and rule.get("version") in versions and rule.get("status") == "approved"]
        if len(active_versions) > 1:
            findings.append({"severity": "error", "code": "conflicting_active_rule_versions",
                             "message": f"Rule {rule_id} has multiple versions marked approved."})

    nisr = _dataset_integrity(findings)
    nisr_source = source_by_id.get("nisr.sas-2023-2026")
    if nisr_source and nisr_source.get("content_sha256") != nisr.get("sha256"):
        findings.append({"severity": "error", "code": "nisr_source_registry_checksum_mismatch",
                         "message": "The NISR source registry checksum differs from the verified dataset manifest."})
    existing_manifest_path = PACK_DIR / "MANIFEST.json"
    manifest_status = "not_created"
    if existing_manifest_path.exists():
        try:
            existing_manifest = json.loads(existing_manifest_path.read_text(encoding="utf-8"))
            manifest_status = "current" if existing_manifest == build_manifest() else "stale"
            if manifest_status == "stale":
                findings.append({"severity": "error", "code": "agronomy_manifest_stale", "message": "Registry inputs changed; active guidance is unavailable until the reviewed manifest is refreshed."})
        except (OSError, ValueError, json.JSONDecodeError):
            manifest_status = "invalid"
            findings.append({"severity": "error", "code": "agronomy_manifest_invalid", "message": "The existing knowledge manifest is malformed."})
    severities = {item["severity"] for item in findings}
    existing_crops = sorted(CROPS)
    declared_approved_rules = [r for r in rules if isinstance(r, dict) and r.get("status") == "approved"]
    # A local editable review file is not an authenticated approval trust anchor.
    # Keep the safe empty state until identity and qualifications can be verified.
    approved_rules = declared_approved_rules if APPROVAL_TRUST_ANCHOR_CONFIGURED else []
    crop_coverage = []
    for crop in existing_crops:
        scoped = [r for r in approved_rules if r.get("crop") is None or r.get("crop") == crop]
        covered_districts = set()
        for rule in scoped:
            geography = rule.get("geography", {})
            if not isinstance(geography, dict):
                continue
            if geography.get("type") == "national":
                covered_districts.update(ALL_DISTRICTS)
            elif geography.get("type") == "district":
                covered_districts.update(set(geography.get("scope", [])) & set(ALL_DISTRICTS))
        crop_coverage.append({"crop": crop, "legacy_provisional_guide_entry": True,
                              "approved_categories": sorted({r["category"] for r in scoped}),
                              "approved_seasons": sorted({s for r in scoped for s in r.get("season_scope", [])}),
                              "approved_geographic_scopes": [r["geography"] for r in scoped],
                              "districts_without_directly_scoped_rule": sorted(set(ALL_DISTRICTS) - covered_districts)})
    covered_any_district = set()
    for rule in approved_rules:
        geography = rule.get("geography", {})
        if not isinstance(geography, dict):
            continue
        if geography.get("type") == "national":
            covered_any_district.update(ALL_DISTRICTS)
        elif geography.get("type") == "district":
            covered_any_district.update(set(geography.get("scope", [])) & set(ALL_DISTRICTS))
    return {
        "dataset_version": DATASET_VERSION,
        "schema_version": "1.0",
        "valid": "error" not in severities,
        "counts": {"sources": len(source_ids), "source_statements": len(statement_ids), "agronomic_rules": len(rules),
                   "approved_rules": len(approved_rules),
                   "declared_approved_rules": len(declared_approved_rules),
                   "review_decisions": len(decisions), "open_quality_issues": sum(i.get("status") == "open" for i in issues if isinstance(i, dict)),
                   "quality_issues": len(issue_ids), "existing_provisional_crop_entries": len(existing_crops),
                   "nisr_rows": nisr.get("row_count")},
        "nisr_dataset": nisr,
        "manifest_status": manifest_status,
        "coverage": {"districts_total": len(ALL_DISTRICTS), "districts_with_approved_rules": sorted(covered_any_district),
                     "crops_in_existing_provisional_guide": existing_crops,
                     "crops_with_approved_rules": sorted({r.get("crop") for r in approved_rules if r.get("crop")}),
                     "categories_with_approved_rules": sorted({r.get("category") for r in approved_rules}),
                     "seasons_with_approved_rules": sorted({s for r in approved_rules for s in r.get("season_scope", [])}),
                     "by_crop": crop_coverage,
                     "note": "No approved scoped agronomic rules are loaded. Provisional legacy CropPulse guide entries are not evidence coverage."},
        "findings": findings,
    }


def build_manifest() -> dict[str, Any]:
    """Create a deterministic manifest for validated pack inputs (no timestamp)."""
    files = {}
    pack_root = Path(PACK_DIR).resolve(strict=True)
    project_root = Path(ROOT).resolve(strict=True)
    for path in (SCHEMA_PATH, SOURCES_PATH, STATEMENTS_PATH, RULES_PATH, DECISIONS_PATH, ISSUES_PATH):
        resolved_path = Path(path).resolve(strict=True)
        try:
            pack_relative = resolved_path.relative_to(pack_root)
        except ValueError as exc:
            raise ValueError("Agronomy manifest inputs must remain inside the configured pack directory.") from exc

        # Production paths retain their established repository-relative keys. An isolated
        # fixture pack outside the repository uses only its local relative names, never an
        # absolute temp path. In both cases the resolved input must be inside PACK_DIR.
        try:
            manifest_path = resolved_path.relative_to(project_root)
        except ValueError:
            manifest_path = pack_relative
        files[manifest_path.as_posix()] = _sha256(resolved_path)
    canonical = json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")
    rules = _read(RULES_PATH).get("rules", [])
    return {"dataset_version": DATASET_VERSION, "schema_version": "1.0",
            "dataset_sha256": hashlib.sha256(canonical).hexdigest(), "files": files,
            "declared_approved_rule_count": sum(r.get("status") == "approved" for r in rules)}


def approved_rules_for(crop: str, district: str, season: str, *, today: date | None = None,
                       province: str | None = None, sector: str | None = None,
                       site: str | None = None, variety: str | None = None,
                       condition_context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Return only in-date approved rules whose crop, variety, geography, season and conditions match."""
    today = today or date.today()
    report = validate_pack(today=today)
    if (not report["valid"] or report.get("manifest_status") != "current"
            or not APPROVAL_TRUST_ANCHOR_CONFIGURED):
        return []
    normalized_district = next((name for name in ALL_DISTRICTS if name.casefold() == district.casefold()), None)
    normalized_crop = next((name for name in CROPS if name.casefold() == crop.casefold()), crop)
    matching: list[dict[str, Any]] = []
    for rule in _read(RULES_PATH).get("rules", []):
        if _rule_matches_scope(rule, normalized_crop, normalized_district, season, today=today,
                               province=province, sector=sector, site=site, variety=variety,
                               condition_context=condition_context):
            matching.append(rule)
    return matching


def _rule_matches_scope(rule: dict[str, Any], crop: str, district: str | None, season: str,
                        *, today: date, province: str | None = None, sector: str | None = None,
                        site: str | None = None, variety: str | None = None,
                        condition_context: dict[str, Any] | None = None) -> bool:
    """Check applicability only; this helper does not establish rule approval."""
    if (rule.get("status") != "approved" or rule.get("review_status") != "approved_for_scope"
            or rule.get("crop") not in {None, crop} or season not in rule.get("season_scope", [])):
        return False
    rule_variety = rule.get("variety")
    if rule_variety is not None and (variety is None or rule_variety.strip().casefold() != variety.strip().casefold()):
        return False
    if rule.get("conditions") and not _conditions_match(rule["conditions"], condition_context):
        return False
    try:
        if date.fromisoformat(rule["effective_from"]) > today or date.fromisoformat(rule["revalidate_by"]) < today:
            return False
    except (KeyError, TypeError, ValueError):
        return False
    geography = rule.get("geography", {})
    kind, scope = geography.get("type"), geography.get("scope", [])
    if kind == "national":
        return True
    if kind == "district":
        return district in scope
    if kind == "province":
        return province in scope
    if kind == "sector":
        return sector in scope
    if kind == "site":
        return site in scope
    return False


def _conditions_match(conditions: list[dict[str, Any]], context: dict[str, Any] | None) -> bool:
    """Fail closed when a condition has no supplied value or uses an unsafe comparison."""
    if not conditions:
        return True
    if not isinstance(context, dict):
        return False
    for condition in conditions:
        parameter = condition.get("parameter")
        operator = condition.get("operator")
        expected = condition.get("value")
        if parameter not in context:
            return False
        actual = context[parameter]
        if operator in {"gt", "gte", "lt", "lte"}:
            if (isinstance(actual, bool) or not isinstance(actual, (int, float))
                    or isinstance(expected, bool) or not isinstance(expected, (int, float))):
                return False
            matched = {"gt": actual > expected, "gte": actual >= expected,
                       "lt": actual < expected, "lte": actual <= expected}[operator]
        elif operator == "eq":
            matched = type(actual) is type(expected) and actual == expected
        elif operator == "ne":
            matched = type(actual) is type(expected) and actual != expected
        elif operator == "in":
            matched = isinstance(expected, list) and type(actual) in {str, int, float} and actual in expected
        elif operator == "not_in":
            matched = isinstance(expected, list) and type(actual) in {str, int, float} and actual not in expected
        else:
            return False
        if not matched:
            return False
    return True


def farmer_facing_guidance_for(crop: str, district: str, season: str, *, today: date | None = None,
                               variety: str | None = None,
                               condition_context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Return approved, scoped rules with source metadata, omitting reviewer identities."""
    rules = approved_rules_for(crop, district, season, today=today, variety=variety,
                               condition_context=condition_context)
    if not rules:
        return []
    sources = _read(SOURCES_PATH)["sources"]
    by_id = {source["source_id"]: source for source in sources}
    result = []
    for rule in rules:
        references = []
        for ref in rule["source_references"]:
            source = by_id.get(ref["source_id"], {})
            references.append({"organization": source.get("organization"), "title": source.get("title"),
                               "url": source.get("url"), "locator": ref["locator"],
                               "paraphrase": ref["paraphrase"]})
        result.append({"rule_id": rule["rule_id"], "version": rule["version"],
                       "category": rule["category"], "recommendation": rule["recommendation"],
                       "geography": rule["geography"], "season_scope": rule["season_scope"],
                       "conditions": rule["conditions"], "parameters": rule.get("parameters", []),
                       "source_references": references, "limitations": rule["limitations"],
                       "effective_from": rule["effective_from"], "revalidate_by": rule["revalidate_by"],
                       "status": "approved_for_defined_scope"})
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the CropPulse agronomic knowledge pack without accessing the application database.")
    parser.add_argument("--write-manifest", action="store_true", help="write a new manifest only when all validations pass")
    parser.add_argument("--write-report", action="store_true", help="write the validation report JSON")
    args = parser.parse_args()
    result = validate_pack()
    blocking_findings = [item for item in result.get("findings", [])
                         if item.get("severity") == "error" and item.get("code") != "agronomy_manifest_stale"]
    if not result["valid"] and (not args.write_manifest or blocking_findings):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1
    if args.write_manifest:
        (PACK_DIR / "MANIFEST.json").write_text(json.dumps(build_manifest(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result = validate_pack()
    if not result["valid"]:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1
    if args.write_report:
        (PACK_DIR / "validation_report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
