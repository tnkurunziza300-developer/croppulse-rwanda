from backend import crop_disease_model as screening


def test_unsupported_crop_has_no_prediction_or_report_blocking_status():
    result = screening.screen_crop_image("Beans", b"not decoded because unsupported")
    assert result["status"] == "unsupported_crop"
    assert result["candidates"] == []
    assert "report remains available" in result["message"]


def test_model_load_failure_degrades_to_clear_unavailable_state(monkeypatch):
    def fail_to_load():
        raise RuntimeError("runtime not installed")

    monkeypatch.setattr(screening, "_load_model_bundle", fail_to_load)
    result = screening.screen_crop_image("Maize", b"private image bytes")
    assert result["status"] == "unavailable"
    assert result["candidates"] == []
    assert "still saved" in result["message"]
