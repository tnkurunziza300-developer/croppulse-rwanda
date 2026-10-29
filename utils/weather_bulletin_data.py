"""Curated numeric rainfall outlook statements transcribed from bulletin text."""
from __future__ import annotations

import json
import math
from datetime import date, timezone, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import WeatherBulletin, WeatherBulletinRecord

RECORDS_PATH = Path(__file__).with_name("weather_bulletin_records.json")
REQUIRED = {
    "document_key", "record_key", "record_type", "geography_type", "geography_label",
    "period_label", "valid_from", "valid_to", "value_min", "value_max", "unit",
    "source_page", "source_text",
}


def load_records(path: Path = RECORDS_PATH) -> list[dict]:
    records = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("Weather bulletin records must be a JSON list.")
    keys: set[tuple[str, str]] = set()
    for row in records:
        if not isinstance(row, dict) or REQUIRED - row.keys():
            raise ValueError("A weather bulletin record is missing required source or value fields.")
        if row["record_type"] not in {"monthly_outlook", "seasonal_outlook"}:
            raise ValueError("Unsupported weather bulletin record type.")
        if row["geography_type"] not in {"national", "named_area"}:
            raise ValueError("Unsupported weather bulletin geography type.")
        if not row["source_text"].strip() or not row["geography_label"].strip():
            raise ValueError("Every weather bulletin value needs its source text and geographic scope.")
        if int(row["source_page"]) < 1:
            raise ValueError("Weather bulletin page numbers must be positive.")
        start, end = date.fromisoformat(row["valid_from"]), date.fromisoformat(row["valid_to"])
        if start > end:
            raise ValueError("Weather bulletin valid period is reversed.")
        for field in ("value_min", "value_max", "normal_min", "normal_max"):
            value = row.get(field)
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)):
                raise ValueError(f"Weather bulletin {field} must be a finite number.")
        if row["value_min"] > row["value_max"]:
            raise ValueError("Weather bulletin value range is reversed.")
        if row.get("normal_min") is not None and row.get("normal_max") is not None and row["normal_min"] > row["normal_max"]:
            raise ValueError("Weather bulletin normal range is reversed.")
        key = (row["document_key"], row["record_key"])
        if key in keys:
            raise ValueError("Weather bulletin record keys must be unique per source document.")
        keys.add(key)
    return records


def import_records(db: Session, path: Path = RECORDS_PATH) -> int:
    """Idempotently upsert curated source-linked outlook values.

    A missing bulletin is an error; records are never detached from original PDFs.
    """
    records = load_records(path)
    prepared = []
    for values in records:
        bulletin = db.scalar(select(WeatherBulletin).where(
            WeatherBulletin.document_key == values["document_key"]))
        if bulletin is None:
            raise FileNotFoundError(f"Import the original weather bulletin first: {values['document_key']}")
        prepared.append((bulletin, values))
    for bulletin, values in prepared:
        record = db.scalar(select(WeatherBulletinRecord).where(
            WeatherBulletinRecord.bulletin_id == bulletin.id,
            WeatherBulletinRecord.record_key == values["record_key"],
        ))
        if record is None:
            record = WeatherBulletinRecord(
                bulletin_id=bulletin.id, record_key=values["record_key"],
                created_at=datetime.now(timezone.utc),
            )
            db.add(record)
        record.record_type = values["record_type"]
        record.variable = "rainfall_total"
        record.geography_type = values["geography_type"]
        record.geography_label = values["geography_label"]
        record.valid_from = date.fromisoformat(values["valid_from"])
        record.valid_to = date.fromisoformat(values["valid_to"])
        record.period_label = values["period_label"]
        record.value_min = float(values["value_min"])
        record.value_max = float(values["value_max"])
        record.unit = values["unit"]
        record.normal_min = values.get("normal_min")
        record.normal_max = values.get("normal_max")
        record.anomaly_label = values.get("anomaly_label")
        record.source_page = int(values["source_page"])
        record.source_text = values["source_text"].strip()
        record.transcription_status = "numeric-range-transcribed"
    db.commit()
    return len(prepared)
