"""Convert the supplied NISR SAS workbooks into CropPulse's verified CSV schema.

Reads only the named crop-area and crop-production tables. It uses Python's
standard library to read XLSX, so no spreadsheet application is required.
Source workbooks are never modified. Missing/dash cells are omitted, not
converted to zero; explicit zero-area/zero-production crop cells are omitted
because they do not represent a cultivated observation.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from datetime import date
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

from utils import geography

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "nisr_sas"
OUT_DIR = ROOT / "data" / "verified"
OUTPUT_NAME = "nisr_sas_2023_2026.csv"
NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}

# official NISR landing pages for the matching table workbooks
SOURCES = {
    2023: "https://www.statistics.gov.rw/data-sources/surveys/Seasonal-Agricultural-Survey/Seasonal-Agricultural-Survey/seasonal-agricultural-survey-2023",
    2024: "https://www.alpha.statistics.gov.rw/statistical-publications/agriculture-environment/seasonal-agricultural-survey-2024-annual-report-2024",
    2025: "https://www.statistics.gov.rw/data-sources/surveys/Seasonal-Agricultural-Survey/Seasonal-Agricultural-Survey/seasonal-agricultural-survey-2025-",
    2026: "https://www.statistics.gov.rw/statistical-publications/agriculture-environment/seasonal-agricultural-survey-season-b-2026",
}

# year -> (workbook filename, season -> (cultivated-area sheet, crop-production sheet))
WORKBOOKS = {
    2023: ("SAS 2023_Annual Tables (3).xlsx", {"A": (10, 22), "B": (11, 23), "C": (12, 24)}),
    2024: ("SAS 2024_Annual Tables.xlsx", {"A": (10, 21), "B": (11, 22), "C": (12, 23)}),
    2025: ("SAS 2025_Annual Tables.xlsx", {"A": (13, 24), "B": (14, 25), "C": (15, 26)}),
    2026: (None, {}),  # A/B are published as separate workbooks below.
}
SEASONAL_WORKBOOKS = {
    (2026, "A"): ("Tables_2026 Season A.xlsx", 11, 15, "https://statistics.gov.rw/statistical-publications/agriculture-environment/seasonal-agricultural-survey-season-2026"),
    (2026, "B"): ("Tables_2026 Season B.xlsx", 9, 13, "https://statistics.gov.rw/statistical-publications/agriculture-environment/seasonal-agricultural-survey-season-b-2026"),
}

CANONICAL_CROPS = {
    "maize": "Maize",
    "sorghum": "Sorghum",
    "paddy rice": "Paddy rice",
    "cassava": "Cassava",
    "sweet potato": "Sweet potato",
    "sweet potatoes": "Sweet potato",
    "irish potato": "Irish potato",
    "irish potatoes": "Irish potato",
    "bean": "Beans",
    "beans": "Beans",
    "banana": "Banana",
    "bananas": "Banana",
}
CSV_FIELDS = [
    "district", "province", "crop", "season", "year", "area_ha",
    "production_t", "production_unit", "area_unit", "farmer_type",
    "cropping_system", "source_name", "source_url", "source_table",
    "source_period", "retrieved_at",
]


def _shared_strings(archive: ZipFile) -> list[str]:
    try:
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    return ["".join(t.text or "" for t in item.findall(".//m:t", NS)) for item in root.findall("m:si", NS)]


def _workbook_sheets(archive: ZipFile) -> dict[str, str]:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    targets = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels}
    sheets = {}
    for sheet in workbook.findall("m:sheets/m:sheet", NS):
        target = targets[sheet.attrib[f"{{{NS['r']}}}id"]].lstrip("/")
        if not target.startswith("xl/"):
            target = "xl/" + target
        sheets[sheet.attrib["name"]] = target
    return sheets


def _column_number(cell_ref: str) -> int:
    letters = re.match(r"[A-Z]+", cell_ref)
    if not letters:
        raise ValueError(f"Invalid XLSX cell reference: {cell_ref}")
    value = 0
    for letter in letters.group():
        value = value * 26 + ord(letter) - 64
    return value


def _read_sheet(archive: ZipFile, target: str, strings: list[str]) -> list[list[str]]:
    root = ET.fromstring(archive.read(target))
    out: list[list[str]] = []
    for row in root.findall(".//m:sheetData/m:row", NS):
        cells: dict[int, str] = {}
        for cell in row.findall("m:c", NS):
            col = _column_number(cell.attrib["r"]) - 1
            kind = cell.attrib.get("t")
            if kind == "inlineStr":
                value = "".join(t.text or "" for t in cell.findall(".//m:t", NS))
            else:
                node = cell.find("m:v", NS)
                value = "" if node is None else node.text or ""
                if kind == "s" and value:
                    value = strings[int(value)]
            cells[col] = value.strip()
        if cells:
            values = [""] * (max(cells) + 1)
            for col, value in cells.items():
                values[col] = value
            out.append(values)
        else:
            out.append([])
    return out


def _normalize_heading(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _crop_columns(rows: list[list[str]], filename: str, sheet_name: str) -> tuple[int, int, dict[int, str]]:
    """Find the District header; join a preceding row for split production headers."""
    for row_index, row in enumerate(rows):
        district_col = next((i for i, value in enumerate(row) if "district" in _normalize_heading(value)), None)
        if district_col is None:
            continue
        combined = list(row)
        if row_index > 0:
            previous = rows[row_index - 1]
            if len(previous) > len(combined):
                combined.extend([""] * (len(previous) - len(combined)))
            for col, value in enumerate(previous):
                if col < len(combined) and not combined[col].strip() and value.strip():
                    combined[col] = value.strip()
        mapped: dict[int, str] = {}
        for col, value in enumerate(combined):
            if col <= district_col:
                continue
            canonical = CANONICAL_CROPS.get(_normalize_heading(value))
            if canonical:
                if canonical in mapped.values():
                    raise ValueError(f"Ambiguous {canonical} columns in {filename}, {sheet_name}.")
                mapped[col] = canonical
        if mapped:
            return row_index + 1, district_col, mapped  # 1-based worksheet row for data diagnostics
    raise ValueError(f"Could not identify district/crop columns in {filename}, {sheet_name}.")


def _number(raw: str, *, filename: str, sheet: str, row_number: int, crop: str) -> float | None:
    value = raw.strip().replace(",", "")
    if not value or value in {"-", "–", "—", "NA", "N/A", "na", "n/a"}:
        return None
    try:
        number = float(value)
    except ValueError as exc:
        raise ValueError(f"Non-numeric {crop} value {raw!r} in {filename}, {sheet}, row {row_number}.") from exc
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"Invalid negative/non-finite {crop} value {raw!r} in {filename}, {sheet}, row {row_number}.")
    return number


def _extract_table(archive: ZipFile, sheet_number: int, *, filename: str) -> dict[tuple[str, str], float]:
    sheets = _workbook_sheets(archive)
    sheet_name = f"Table {sheet_number}"
    if sheet_name not in sheets:
        raise ValueError(f"Missing expected sheet {sheet_name} in {filename}.")
    rows = _read_sheet(archive, sheets[sheet_name], _shared_strings(archive))
    header_row_number, district_col, columns = _crop_columns(rows, filename, sheet_name)
    values: dict[tuple[str, str], float] = {}
    for row_index in range(header_row_number, len(rows)):
        row = rows[row_index]
        if not row:
            continue
        district_value = row[district_col].strip() if district_col < len(row) else ""
        # Only canonical districts from the reviewed NISR geography list are data
        # rows. This excludes report titles, national/province totals, and metadata
        # such as "Change" without guessing that a label is a district.
        district = geography.normalize_district(district_value)
        if district is None:
            continue
        for col, crop in columns.items():
            raw = row[col] if col < len(row) else ""
            number = _number(raw, filename=filename, sheet=sheet_name, row_number=row_index + 1, crop=crop)
            if number is None:
                continue
            key = (district, crop)
            if key in values:
                raise ValueError(f"Duplicate district/crop value {district}/{crop} in {filename}, {sheet_name}.")
            values[key] = number
    if not values:
        raise ValueError(f"No district observations extracted from {filename}, {sheet_name}.")
    return values


def _source_workbooks():
    for year, (filename, seasons) in WORKBOOKS.items():
        if filename:
            for season, tables in seasons.items():
                yield year, season, filename, *tables, SOURCES[year]
    for (year, season), (filename, area_sheet, production_sheet, source_url) in SEASONAL_WORKBOOKS.items():
        yield year, season, filename, area_sheet, production_sheet, source_url


def import_sas(*, retrieved_at: str | None = None) -> dict:
    """Build the verified aggregate CSV and manifest; fail without replacing prior output."""
    retrieved_at = retrieved_at or date.today().isoformat()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", retrieved_at):
        raise ValueError("retrieved_at must use YYYY-MM-DD format.")
    missing = [filename for _, _, filename, *_ in _source_workbooks() if not (RAW_DIR / filename).is_file()]
    if missing:
        raise FileNotFoundError(f"Missing NISR workbook(s) in {RAW_DIR}: {', '.join(missing)}")

    observations = []
    provenance = []
    omitted_incomplete = 0
    omitted_zero_zero = 0
    inconsistent_area_production = []
    for year, season, filename, area_sheet, production_sheet, source_url in _source_workbooks():
        path = RAW_DIR / filename
        with ZipFile(path) as archive:
            areas = _extract_table(archive, area_sheet, filename=filename)
            production = _extract_table(archive, production_sheet, filename=filename)
        paired_keys = set(areas) & set(production)
        omitted_incomplete += len(set(areas) ^ set(production))
        if not paired_keys:
            raise ValueError(f"No matching crop/district pairs in {filename} Season {season}.")
        for district, crop in sorted(paired_keys):
            area = areas[(district, crop)]
            production_t = production[(district, crop)]
            if area == 0 and production_t == 0:
                omitted_zero_zero += 1
                continue
            if area == 0:
                inconsistent_area_production.append({"file": filename, "season": f"{year} {season}",
                    "district": district, "crop": crop, "area_ha": area, "production_t": production_t,
                    "area_table": area_sheet, "production_table": production_sheet})
                continue
            observations.append({
                "district": district, "crop": crop, "season": season, "year": year,
                "area_ha": area, "production_t": production_t,
                "production_unit": "tonnes", "area_unit": "ha",
                "farmer_type": "", "cropping_system": "",
                "source_name": filename, "source_url": source_url,
                "source_table": f"Table {area_sheet} cultivated area; Table {production_sheet} crop production",
                "source_period": f"{year} Season {season}", "retrieved_at": retrieved_at,
            })
        provenance.append({"file": filename, "title": f"NISR Seasonal Agricultural Survey {year} Season {season} tables",
            "publisher": "National Institute of Statistics of Rwanda (NISR)", "source_url": source_url,
            "reference_period": f"{year} Season {season}", "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "units": "cultivated area in hectares (ha); production in tonnes (MT)",
            "processing_steps": f"Read district-level cultivated-area Table {area_sheet} and crop-production Table {production_sheet}; matched district and selected crop columns; omitted dash/blank/NA cells and explicit 0/0 non-cultivation rows; retained positive-area records with zero production.",
            "limitations": "Aggregate district-season observations. Not farmer-level data, disease prevalence, causal analysis, or a crop recommendation by itself. CropPulse supports only the selected crop categories listed in the import code."})

    observations.sort(key=lambda row: (row["year"], row["season"], row["district"], row["crop"]))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / OUTPUT_NAME
    manifest_path = OUT_DIR / "MANIFEST.json"
    # Prepare in-memory contents first, so a parsing failure never changes active verified data.
    import io
    csv_buffer = io.StringIO(newline="")
    writer = csv.DictWriter(csv_buffer, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(observations)
    csv_bytes = csv_buffer.getvalue().encode("utf-8")
    manifest = {"files": [{"file": OUTPUT_NAME, "title": "NISR SAS district crop area and production, 2023–2026",
        "publisher": "National Institute of Statistics of Rwanda (NISR)",
        "source_url": " | ".join(sorted({item["source_url"] for item in provenance})),
        "reference_period": "2023 Seasons A/B/C; 2024 Seasons A/B/C; 2025 Seasons A/B/C; 2026 Seasons A/B",
        "retrieved_at": retrieved_at, "sha256": hashlib.sha256(csv_bytes).hexdigest(),
        "units": "cultivated area in hectares (ha); production in tonnes (MT)",
        "processing_steps": "Long-format aggregate of matched district/crop/season cultivated area and production tables. See source fields on every row and source_workbooks for workbook hashes and table numbers.",
        "limitations": "NISR source data; structural validation is performed by CropPulse but does not independently verify NISR's survey estimates. 2026 covers Seasons A and B only. Missing/dash cells and explicit 0/0 non-cultivation pairs are not emitted. Area/production pairs with zero area and positive production are excluded and enumerated in quality_report. This dataset does not support image diagnosis or disease-treatment recommendations.",
        "quality_report": {"rows_written": len(observations), "omitted_unpaired_or_unobserved": omitted_incomplete,
            "omitted_explicit_zero_area_and_zero_production": omitted_zero_zero,
            "excluded_zero_area_positive_production": inconsistent_area_production},
        "source_workbooks": provenance}]}
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    csv_path.write_bytes(csv_bytes)
    manifest_path.write_bytes(manifest_bytes)
    return {"csv": str(csv_path), "manifest": str(manifest_path), "rows": len(observations),
        "source_workbooks": len(provenance), "omitted_unpaired_or_unobserved": omitted_incomplete,
        "omitted_zero_area_zero_production": omitted_zero_zero,
        "excluded_zero_area_positive_production": len(inconsistent_area_production),
        "districts": len({row["district"] for row in observations}),
        "crops": sorted({row["crop"] for row in observations}),
        "years": sorted({row["year"] for row in observations}),
        "seasons": sorted({row["season"] for row in observations})}


if __name__ == "__main__":
    print(json.dumps(import_sas(), ensure_ascii=False, indent=2))
