"""Reviewed weather-to-agriculture rules approved for automated use.

This registry is deliberately empty. A rule may be added only after its source,
scope, limitations, and local agronomic approval have been recorded and reviewed.
An automated test cannot approve an agricultural rule.
"""

from dataclasses import dataclass
from datetime import date
from hashlib import sha256


@dataclass(frozen=True)
class WeatherAlertRule:
    rule_id: str
    version: str
    alert_type: str
    variables: tuple[str, ...]
    crop_scope: tuple[str, ...]
    activity_scope: tuple[str, ...]
    geographic_scope: str
    source_name: str
    source_url: str
    source_revision_date: date | None
    evidence_status: str
    limitations: str
    reviewer_name: str | None
    reviewer_institution: str | None
    reviewed_at: date | None
    approved_for_automated_alerts: bool


# No weather-to-agriculture rule is approved for automated alerts in this release.
WEATHER_ALERT_RULES: tuple[WeatherAlertRule, ...] = ()


def weather_alert_dedupe_key(*, recipient_id: str, farm_id: str, field_id: str,
                            alert_type: str, rule_id: str, rule_version: str,
                            valid_from: date, valid_to: date) -> str:
    """Stable key per recipient/location/rule/forecast period, excluding retrieval time."""
    parts = (recipient_id, farm_id, field_id, alert_type, rule_id, rule_version,
             valid_from.isoformat(), valid_to.isoformat())
    return sha256("\0".join(parts).encode("utf-8")).hexdigest()


def active_weather_rules() -> list[dict[str, str]]:
    """Expose only reviewed rules that include source and reviewer provenance."""
    return [
        {"rule_id": rule.rule_id, "version": rule.version, "alert_type": rule.alert_type,
         "evidence_status": rule.evidence_status}
        for rule in WEATHER_ALERT_RULES
        if rule.approved_for_automated_alerts
        and rule.source_name.strip() and rule.source_url.strip()
        and rule.reviewer_name and rule.reviewer_institution and rule.reviewed_at
    ]
