"""Read-only staging migration preflight; never applies a migration."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.diagnostics import inspect_database
from backend.runtime_config import validate_runtime_config


def check_target(expected_prior_revision: str, configured_url: str | None = None) -> dict[str, Any]:
    """Check connection, expected prior revision, and integrity without writing."""
    try:
        result = inspect_database(configured_url)
    except Exception:
        # URL parsing and diagnostics can fail before a structured result exists.
        # Keep the helper fail-closed and never echo URLs or driver details.
        result = {
            "backend": "unknown",
            "connection": "failed; details omitted",
            "revision": "unknown",
            "revision_check": "failed; details omitted",
            "integrity": "not checked",
            "foreign_key_violations": "not checked",
        }
    revision_matches = result.get("revision") == expected_prior_revision
    integrity_ok = result.get("integrity") in {"ok", "not applicable"}
    foreign_keys_ok = result.get("foreign_key_violations") in {0, "not applicable"}
    result["expected_prior_revision"] = expected_prior_revision
    result["preflight_passed"] = (
        result.get("connection") == "ok" and revision_matches and integrity_ok and foreign_keys_ok
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only staging target preflight; does not run migrations.")
    parser.add_argument("--expected-prior-revision", required=True,
                        help="Exact Alembic revision expected before the planned migration.")
    args = parser.parse_args(argv)
    try:
        validate_runtime_config()
        result = check_target(args.expected_prior_revision)
    except Exception:
        print("Preflight failed: runtime configuration or database check failed; details omitted.", file=sys.stderr)
        return 2

    print(f"Backend: {result.get('backend', 'unknown')}")
    print(f"Connection: {result.get('connection', 'not checked')}")
    print(f"Expected prior revision: {args.expected_prior_revision}")
    print(f"Current revision: {result.get('revision', 'unknown')}")
    print(f"Integrity: {result.get('integrity', 'not checked')}")
    print(f"Foreign-key violations: {result.get('foreign_key_violations', 'not checked')}")
    if not result["preflight_passed"]:
        print("Preflight failed. No migration was run.", file=sys.stderr)
        return 3
    print("Preflight passed. This command made no database changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
