from io import BytesIO
from zipfile import ZipFile

import pytest

from utils import nisr_sas_import as importer


def test_number_preserves_zero_and_omits_missing():
    assert importer._number("0", filename="x.xlsx", sheet="Table 1", row_number=2, crop="Maize") == 0
    assert importer._number(" - ", filename="x.xlsx", sheet="Table 1", row_number=2, crop="Maize") is None
    with pytest.raises(ValueError, match="Invalid negative"):
        importer._number("-1", filename="x.xlsx", sheet="Table 1", row_number=2, crop="Maize")


def test_table_extraction_only_accepts_known_district_rows(monkeypatch):
    rows = [
        ["", "District/Crop", "Maize", "Beans"],
        ["", "Huye", "10", "-"],
        ["", "Change", "-0.14", "2"],
        ["", "National total", "20", "30"],
        ["", "Nyagatare", "0", "5"],
    ]
    monkeypatch.setattr(importer, "_workbook_sheets", lambda _archive: {"Table 1": "sheet.xml"})
    monkeypatch.setattr(importer, "_shared_strings", lambda _archive: [])
    monkeypatch.setattr(importer, "_read_sheet", lambda *_args: rows)

    with ZipFile(BytesIO(), "w") as archive:
        result = importer._extract_table(archive, 1, filename="fixture.xlsx")

    assert result == {("Huye", "Maize"): 10.0, ("Nyagatare", "Maize"): 0.0, ("Nyagatare", "Beans"): 5.0}


def test_crop_aliases_are_explicit_and_supported():
    assert importer.CANONICAL_CROPS["irish potatoes"] == "Irish potato"
    assert importer.CANONICAL_CROPS["beans"] == "Beans"
    assert "wheat" not in importer.CANONICAL_CROPS
