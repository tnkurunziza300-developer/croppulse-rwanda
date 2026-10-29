from datetime import date

from utils.seasonal_plan import EVIDENCE, build_plan


def test_streamlit_crop_plan_exposes_provisional_source_and_limitations():
    plan = build_plan("Maize", "Huye", "A", date(2026, 10, 20), 0.5)

    assert plan["evidence"] == EVIDENCE
    assert plan["evidence"]["verification_status"] == "Provisional; not locally verified"
    assert plan["evidence"]["last_reviewed"] is None
    assert plan["activities"]
    assert all(item["evidence"] and item["warning"] for item in plan["activities"])
    assert any("cannot diagnose crop disease" in item["warning"].lower() for item in plan["activities"])
    assert any("no pesticide or herbicide rates" in item["warning"].lower() for item in plan["activities"])
