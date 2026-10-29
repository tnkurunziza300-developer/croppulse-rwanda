"""Runtime security configuration shared by the CropPulse API."""

import os
from urllib.parse import urlsplit


def _secret() -> str:
    secret = os.environ.get("CROP_PULSE_SECRET_KEY", "")
    environment = os.environ.get("CROP_PULSE_ENVIRONMENT", "development").strip().lower()
    weak_values = {
        "change-me", "changeme", "secret", "replace-with-a-random-secret-at-least-32-characters",
        "your-secret-key", "test-secret", "development-secret",
    }
    if (len(secret.encode("utf-8")) < 32 or len(set(secret)) < 12 or secret != secret.strip()
            or secret.lower() in weak_values
            or environment in {"staging", "production", "prod"} and secret.lower().startswith(("test-", "dev-"))):
        raise RuntimeError(
            "CROP_PULSE_SECRET_KEY must be a securely generated, non-placeholder secret of at least 32 bytes."
        )
    return secret


def validate_runtime_config() -> None:
    """Fail closed when runtime security settings are missing or unsafe."""
    environment = os.environ.get("CROP_PULSE_ENVIRONMENT", "").strip().lower()
    if environment not in {"development", "test", "staging", "production"}:
        raise RuntimeError("Set CROP_PULSE_ENVIRONMENT to development, test, staging, or production.")
    _secret()
    if environment in {"staging", "production"}:
        configured_origins = os.environ.get("CROP_PULSE_CORS_ORIGINS", "")
        origins = [origin.strip() for origin in configured_origins.split(",") if origin.strip()]
        if not origins or "*" in origins:
            raise RuntimeError("Staging and production require an explicit CROP_PULSE_CORS_ORIGINS allowlist.")
        for origin in origins:
            parsed = urlsplit(origin)
            if (parsed.scheme != "https" or not parsed.netloc or "*" in parsed.netloc or parsed.username or parsed.password
                    or parsed.path not in {"", "/"} or parsed.query or parsed.fragment):
                raise RuntimeError("Staging and production CORS entries must be HTTPS origins without paths or credentials.")
        cookie_setting = os.environ.get("CROP_PULSE_COOKIE_SECURE")
        if cookie_setting is not None and cookie_setting.strip().lower() not in {"1", "true", "yes"}:
            raise RuntimeError("Secure session cookies cannot be disabled in staging or production.")
        if os.environ.get("CROP_PULSE_AUTO_CREATE_SCHEMA", "0").strip() == "1":
            raise RuntimeError("Automatic schema creation is disabled in staging and production; use reviewed migrations.")


def _cookie_secure() -> bool:
    configured = os.environ.get("CROP_PULSE_COOKIE_SECURE")
    environment = os.environ.get("CROP_PULSE_ENVIRONMENT", "development").strip().lower()
    if environment in {"staging", "production"}:
        return True
    if configured is not None:
        return configured.lower() in {"1", "true", "yes"}
    return False
