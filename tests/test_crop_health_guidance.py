from backend.crop_health_guidance import attach_guidance


def test_maize_disease_candidates_get_identity_links_and_conservative_guidance():
    screening = attach_guidance({
        "status": "candidate_screening", "candidates": [
            {"class_name": "Corn_(maize)___Common_rust_", "label": "Common rust", "model_score": 0.7},
        ],
    })
    guidance = screening["guidance"]
    assert guidance["candidates"][0]["organism"] == "Puccinia sorghi"
    assert guidance["candidates"][0]["url"] == "https://gd.eppo.int/taxon/PUCCSO"
    assert any(source["name"].startswith("FAO:") for source in guidance["sources"])
    assert any("PlantwisePlus" in source["name"] for source in guidance["sources"])
    assert "does not recommend a pesticide" in guidance["treatment_notice"]
    assert not any(word in guidance["treatment_notice"].lower() for word in ("apply", "spray weekly", "dose:"))


def test_healthy_candidate_does_not_claim_symptoms_are_absent():
    guidance = attach_guidance({"status": "candidate_screening", "candidates": [
        {"class_name": "Corn_(maize)___healthy", "label": "healthy", "model_score": 0.8},
    ]})["guidance"]
    assert any("does not rule out a problem" in step for step in guidance["steps"])


def test_unknown_class_does_not_get_a_fabricated_disease_identity():
    guidance = attach_guidance({"status": "candidate_screening", "candidates": [
        {"class_name": "other___unknown", "label": "unknown", "model_score": 0.6},
    ]})["guidance"]
    assert guidance["candidates"] == []
