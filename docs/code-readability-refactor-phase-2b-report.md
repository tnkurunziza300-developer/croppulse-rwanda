# CropPulse Rwanda — Phase 2B Runtime-Security Configuration Refactor

**Date:** 26 October 2026  
**Project root:** `C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda`

## Summary

Moved `_secret()`, `validate_runtime_config()`, and `_cookie_secure()` from `backend/api.py` into `backend/runtime_config.py`. `backend/api.py` imports the same names and retains all existing call sites. The helper implementations were moved without logic changes; AST comparison against the verified pre-change copy confirmed each helper is identical, and confirmed all other non-import API definitions/statements are unchanged.

**Observed behavior change:** None in the focused checks. This is not a production or full-system verification.

## Files changed

- `backend/api.py` — imports the helpers from the new module; removed their former in-file definitions.
- `backend/runtime_config.py` — contains the three moved helpers, unchanged.
- `docs/code-readability-refactor-phase-2b-report.md` — this report.

`tests/test_react_security_api.py` was not changed because its existing startup and cookie tests covered the moved rules and their use through `backend.api`.

## Rollback evidence

Before editing, `backend/api.py` was copied to:

`C:\Users\Student\AppData\Local\Temp\croppulse-phase2b-rollback-52fa2ca5e9864045ba9acd68cb7221a1\api.py`

The original and copied file both had SHA-256:

`0BC7FB1CCDCDB6A700D7F77529DCF9DD1CB1CE05CBBEE731B23F1DAE8536B95C`

The helper ASTs in the new module matched the copies exactly. A comparison of all non-import top-level API definitions and statements found no other changes. To roll back, restore the verified `api.py` copy and remove the newly added `backend/runtime_config.py`; retain this report as the change record.

## Test database isolation

The selected tests use the project virtual environment at `.venv\Scripts\python.exe`. The shared `api_client` fixture in `tests/test_backend_api.py` sets `CROP_PULSE_DATABASE_URL` before clearing the cached SQLAlchemy engine and creating tables. It builds a unique path of the form:

`C:\xampp\htdocs\croppulse-rwanda (4)\croppulse-rwanda\.test-runtime\api-test-databases\records-<uuid>.sqlite3`

This resolves under the project root and is distinct from `data\croppulse_phase1.sqlite3`. The fixture creates schema and test records in that unique test database, disposes the engine, clears the cache, and removes the database and SQLite sidecars during teardown. It does not invoke Alembic. The two startup configuration tests invoke the API lifespan in-process and fail or succeed at configuration validation before any schema creation branch is reached for their asserted invalid configurations. The browser test exercises the test fixture database.

No designated development database was opened, queried, migrated, or modified. The focused tests are stateful against their isolated temporary test database, as expected. No external API service or listening server was contacted or launched.

## Checks executed

1. `.\.venv\Scripts\python.exe -m pytest tests/test_react_security_api.py::test_api_startup_fails_clearly_when_signing_key_is_missing_or_insecure tests/test_react_security_api.py::test_startup_requires_explicit_environment_and_secure_production_configuration tests/test_react_security_api.py::test_browser_auth_cookie_refresh_csrf_and_logout -q`
   - **Result:** exit code 0; 3 passed.
   - **Warning:** pytest could not write its `.pytest_cache` node-id cache due to Windows `WinError 5` access denial. The tests themselves passed.
2. Python AST comparison of the verified pre-change `backend/api.py` copy against the current files.
   - **Result:** moved helper ASTs identical; all non-import API definitions/statements unchanged.

No migrations, full Python suite, frontend checks, browser workflow, production build, or service startup were performed.

## Compatibility and limitations

- Existing calls and names exposed through `backend.api` are retained, including `api_module._cookie_secure()` used by the inspected tests.
- The moved validator resolves `_secret` inside `backend.runtime_config`. No in-repository test or caller found in the inspected references monkeypatches `backend.api._secret` to influence `validate_runtime_config`; such external monkeypatching is not guaranteed compatible.
- The focused tests cover configuration rejection and browser cookie/CSRF behavior, but do not establish every environment combination or deployment behavior.
- No application behavior changes were observed in the selected tests. Full-suite behavior remains unverified.

## Verdict

**REFACTOR COMPLETE — FOCUSED CHECKS PASSED**

This verdict describes only the authorized refactor and focused checks. It does not establish release readiness or production safety.
