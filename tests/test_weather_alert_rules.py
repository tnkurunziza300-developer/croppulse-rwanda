from datetime import date

from utils.weather_alert_rules import WEATHER_ALERT_RULES, active_weather_rules, weather_alert_dedupe_key


def test_weather_alert_rule_registry_stays_inactive_without_reviewed_evidence():
    assert WEATHER_ALERT_RULES == ()
    assert active_weather_rules() == []


def test_weather_alert_deduplication_key_is_stable_for_field_rule_period():
    common = {"recipient_id": "farmer", "farm_id": "farm", "field_id": "field",
              "alert_type": "rain_information", "rule_id": "rule-1", "rule_version": "1",
              "valid_from": date(2026, 10, 22), "valid_to": date(2026, 10, 23)}
    first = weather_alert_dedupe_key(**common)
    assert first == weather_alert_dedupe_key(**common)
    assert len(first) == 64
    assert first != weather_alert_dedupe_key(**{**common, "field_id": "another-field"})
    assert first != weather_alert_dedupe_key(**{**common, "valid_to": date(2026, 10, 24)})
