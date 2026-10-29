"""Private crop-health reporting, photo authorization, and case lifecycle checks."""
from io import BytesIO

from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db import get_engine
from backend.models import Farmer, ReviewerDistrict
from test_backend_api import api_client, auth, register


def photo_bytes(image_format="PNG"):
    image = Image.new("RGB", (80, 60), color=(45, 110, 62))
    output = BytesIO()
    image.save(output, format=image_format)
    return output.getvalue()


def submit_case(client, token, farm_id, *, crop="Maize", symptoms="Yellow patches on lower leaves",
                observed_date=None, plant_parts_affected=None, spreading=None):
    data = {"farm_id": farm_id, "crop": crop, "symptoms": symptoms}
    if observed_date is not None: data["observed_date"] = observed_date
    if plant_parts_affected is not None: data["plant_parts_affected"] = plant_parts_affected
    if spreading is not None: data["spreading"] = str(spreading).lower()
    return client.post("/v1/crop-health/cases", headers=auth(token), data=data,
                       files={"photo": ("field.jpg", photo_bytes(), "image/png")})


def test_crop_health_report_private_photo_and_review_lifecycle(api_client):
    farmer = register(api_client, "crop-health-owner@example.com")
    farm = api_client.post("/v1/farms", headers=auth(farmer), json={"name": "Home plot", "district": "Huye"}).json()
    created = submit_case(api_client, farmer, farm["id"], observed_date="2026-10-20",
                          plant_parts_affected="lower leaves", spreading=False)
    assert created.status_code == 201, created.text
    case = created.json()
    assert case["status"] == "submitted" and case["diagnosis_status"] == "unresolved"
    assert case["observed_date"] == "2026-10-20"
    assert case["plant_parts_affected"] == "lower leaves" and case["spreading"] is False
    assert case["ai_screening"]["status"] in {"unavailable", "candidate_screening"}
    assert "diagnosis" in case["ai_screening"]["message"].lower() or case["ai_screening"]["status"] == "unavailable"
    assert case["updates"] == [] and "prediction" not in case
    assert api_client.get("/v1/crop-health/cases", headers=auth(farmer)).json()[0]["id"] == case["id"]

    photo = api_client.get(case["photo_url"], headers=auth(farmer))
    assert photo.status_code == 200 and photo.headers["content-type"] == "image/jpeg"
    assert photo.headers["cache-control"] == "no-store"
    normalized = Image.open(BytesIO(photo.content))
    assert normalized.format == "JPEG" and normalized.getexif() == {}

    other_farmer = register(api_client, "crop-health-other@example.com")
    assert api_client.get(f"/v1/crop-health/cases/{case['id']}", headers=auth(other_farmer)).status_code == 404
    assert api_client.get(case["photo_url"], headers=auth(other_farmer)).status_code == 404


    reviewer_token = register(api_client, "crop-health-reviewer@example.com")
    with Session(get_engine()) as db:
        reviewer = db.scalar(select(Farmer).where(Farmer.email == "crop-health-reviewer@example.com"))
        reviewer.role = "reviewer"
        reviewer_id = reviewer.id
        db.add(ReviewerDistrict(reviewer_id=reviewer.id, district="Huye"))
        db.commit()
    queue = api_client.get("/v1/reviewer/crop-health/cases", headers=auth(reviewer_token))
    assert [item["id"] for item in queue.json()] == [case["id"]]
    assert api_client.get(case["photo_url"], headers=auth(reviewer_token)).status_code == 200

    started = api_client.post(f"/v1/reviewer/crop-health/cases/{case['id']}/updates", headers=auth(reviewer_token), json={
        "action": "start_review", "message": "I am reviewing the symptoms you reported.",
    })
    assert started.status_code == 201 and started.json()["status"] == "under_review"
    requested = api_client.post(f"/v1/reviewer/crop-health/cases/{case['id']}/updates", headers=auth(reviewer_token), json={
        "action": "request_information", "message": "Please describe whether nearby plants show the same change.",
    })
    assert requested.status_code == 201 and requested.json()["status"] == "awaiting_farmer"
    reply = api_client.post(f"/v1/crop-health/cases/{case['id']}/reply", headers=auth(farmer), json={
        "message": "Several plants in the same row show this.",
    })
    assert reply.status_code == 201 and reply.json()["status"] == "under_review"
    resolved = api_client.post(f"/v1/reviewer/crop-health/cases/{case['id']}/updates", headers=auth(reviewer_token), json={
        "action": "resolve", "assessment": "provisional_observation",
        "message": "This remains a provisional observation; confirm locally before taking action.",
    })
    assert resolved.status_code == 201 and resolved.json()["status"] == "resolved"
    assert resolved.json()["diagnosis_status"] == "provisional_observation"
    assert len(resolved.json()["updates"]) == 4
    assert api_client.post(f"/v1/crop-health/cases/{case['id']}/reply", headers=auth(farmer), json={"message": "Reopen"}).status_code == 409
    assert api_client.post(f"/v1/reviewer/crop-health/cases/{case['id']}/updates", headers=auth(reviewer_token), json={
        "action": "resolve", "message": "Duplicate close.",
    }).status_code == 409

    with Session(get_engine()) as db:
        db.query(ReviewerDistrict).filter_by(reviewer_id=reviewer_id, district="Huye").delete()
        db.commit()
    assert api_client.get(f"/v1/reviewer/crop-health/cases/{case['id']}", headers=auth(reviewer_token)).status_code == 404
    assert api_client.get(case["photo_url"], headers=auth(reviewer_token)).status_code == 404

def test_crop_health_screening_result_is_persisted_and_non_maize_is_not_supported(api_client, monkeypatch):
    import backend.api as api_module

    result = {
        "status": "candidate_screening", "model_name": "test model", "model_version": "abc123",
        "generated_at": None, "score_description": "uncalibrated", "candidates": [
            {"class_name": "Corn_(maize)___healthy", "label": "healthy", "model_score": 0.8},
        ], "message": "Experimental screening; not a diagnosis.",
    }
    monkeypatch.setattr(api_module, "screen_crop_image", lambda crop, image: result.copy())
    farmer = register(api_client, "crop-health-model-owner@example.com")
    farm = api_client.post("/v1/farms", headers=auth(farmer), json={"name": "Model plot", "district": "Huye"}).json()
    created = submit_case(api_client, farmer, farm["id"]).json()
    assert created["ai_screening"]["status"] == "candidate_screening"
    assert created["ai_screening"]["candidates"][0]["label"] == "healthy"
    assert created["ai_screening"]["guidance"]["version"]
    assert any("does not rule out a problem" in step for step in created["ai_screening"]["guidance"]["steps"])
    reopened = api_client.get(f"/v1/crop-health/cases/{created['id']}", headers=auth(farmer)).json()
    assert reopened["ai_screening"] == created["ai_screening"]

    monkeypatch.setattr(api_module, "screen_crop_image", lambda crop, image: {
        "status": "unsupported_crop", "model_name": "model", "model_version": None,
        "generated_at": None, "candidates": [], "message": "No supported model classes for this crop.",
    })
    unsupported = submit_case(api_client, farmer, farm["id"], crop="Beans").json()
    assert unsupported["ai_screening"]["status"] == "unsupported_crop"
    assert unsupported["ai_screening"]["guidance"]["sources"]
    assert unsupported["status"] == "submitted"



def test_crop_health_rejects_foreign_farm_field_and_plan_references(api_client):
    owner = register(api_client, "crop-health-refs-owner@example.com")
    other = register(api_client, "crop-health-refs-other@example.com")
    own_farm = api_client.post("/v1/farms", headers=auth(owner), json={"name": "Own", "district": "Huye"}).json()
    other_farm = api_client.post("/v1/farms", headers=auth(other), json={"name": "Other", "district": "Huye"}).json()
    field = api_client.post(f"/v1/farms/{other_farm['id']}/fields", headers=auth(other), json={
        "name": "Other field", "area_ha": None, "latitude": None, "longitude": None,
    }).json()
    wrong_farm = submit_case(api_client, owner, other_farm["id"])
    wrong_field = api_client.post("/v1/crop-health/cases", headers=auth(owner), data={
        "farm_id": own_farm["id"], "field_id": field["id"], "crop": "Maize", "symptoms": "Spots on leaves",
    }, files={"photo": ("photo.png", photo_bytes(), "image/png")})
    bad_crop = submit_case(api_client, owner, own_farm["id"], crop="Unknown crop")
    assert wrong_farm.status_code == 404
    assert wrong_field.status_code == 404
    assert bad_crop.status_code == 422


def test_crop_health_validates_photo_bytes_size_and_mime(api_client):
    farmer = register(api_client, "crop-health-photo-validation@example.com")
    farm = api_client.post("/v1/farms", headers=auth(farmer), json={"name": "Photo plot", "district": "Huye"}).json()
    invalid = api_client.post("/v1/crop-health/cases", headers=auth(farmer), data={
        "farm_id": farm["id"], "crop": "Maize", "symptoms": "Spots on leaves",
    }, files={"photo": ("photo.jpg", b"not really a photo", "image/jpeg")})
    mismatched = api_client.post("/v1/crop-health/cases", headers=auth(farmer), data={
        "farm_id": farm["id"], "crop": "Maize", "symptoms": "Spots on leaves",
    }, files={"photo": ("photo.jpg", photo_bytes("PNG"), "image/jpeg")})
    oversized = api_client.post("/v1/crop-health/cases", headers=auth(farmer), data={
        "farm_id": farm["id"], "crop": "Maize", "symptoms": "Spots on leaves",
    }, files={"photo": ("photo.jpg", b"x" * (5 * 1024 * 1024 + 1), "image/jpeg")})
    assert invalid.status_code == 422
    assert mismatched.status_code == 422
    assert oversized.status_code == 413


def test_crop_health_reviewer_district_scope_is_required(api_client):
    farmer = register(api_client, "crop-health-scope-owner@example.com")
    farm = api_client.post("/v1/farms", headers=auth(farmer), json={"name": "Scope plot", "district": "Huye"}).json()
    case = submit_case(api_client, farmer, farm["id"]).json()
    reviewer_token = register(api_client, "crop-health-scope-reviewer@example.com")
    with Session(get_engine()) as db:
        reviewer = db.scalar(select(Farmer).where(Farmer.email == "crop-health-scope-reviewer@example.com"))
        reviewer.role = "reviewer"
        db.add(ReviewerDistrict(reviewer_id=reviewer.id, district="Karongi"))
        db.commit()
    assert api_client.get("/v1/reviewer/crop-health/cases", headers=auth(reviewer_token)).json() == []
    assert api_client.get(f"/v1/reviewer/crop-health/cases/{case['id']}", headers=auth(reviewer_token)).status_code == 404
    assert api_client.post(f"/v1/reviewer/crop-health/cases/{case['id']}/updates", headers=auth(reviewer_token), json={
        "action": "start_review", "message": "Outside district.",
    }).status_code == 404
