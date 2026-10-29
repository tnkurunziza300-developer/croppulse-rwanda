"""Small, deterministic and source-linked crop-health guidance library.

This content supplements experimental image screening; it is not a diagnosis
or a locally approved treatment recommendation.
"""

GUIDANCE_VERSION = "2026-10-21.1"

SOURCES = {
    "fao_ipm": {
        "name": "FAO: How to practice Integrated Pest Management?",
        "url": "https://www.fao.org/agriculture/crops/thematic-sitemap/theme/spi/scpi-home/managing-ecosystems/integrated-pest-management/ipm-how/en/",
        "scope": "General IPM principles; FAO says actions must be adapted to local conditions.",
    },
    "plantwise_rwanda": {
        "name": "CABI PlantwisePlus Knowledge Bank",
        "url": "https://plantwiseplusknowledgebank.org/",
        "scope": "Open CABI's Rwanda factsheets for locally authored crop-health material. CropPulse links to it and does not reproduce its factsheet text.",
    },
    "rab": {
        "name": "Rwanda Agriculture and Animal Resources Development Board (RAB)",
        "url": "https://www.rab.gov.rw/",
        "scope": "Local extension and research referral. No disease-specific RAB advice was verified for this library.",
    },
}

_CLASS_INFO = {
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot": {
        "name": "Grey leaf spot (model candidate only)", "organism": "Cercospora zeae-maydis",
        "code": "CERCZM", "url": "https://gd.eppo.int/taxon/CERCZM",
    },
    "Corn_(maize)___Common_rust_": {
        "name": "Common rust (model candidate only)", "organism": "Puccinia sorghi",
        "code": "PUCCSO", "url": "https://gd.eppo.int/taxon/PUCCSO",
    },
    "Corn_(maize)___Northern_Leaf_Blight": {
        "name": "Northern leaf blight (model candidate only)", "organism": "Exserohilum turcicum",
        "code": "SETOTU", "url": "https://gd.eppo.int/taxon/SETOTU",
    },
    "Corn_(maize)___healthy": {
        "name": "Healthy (model candidate only)", "organism": None, "code": None, "url": None,
    },
}


def guidance_for_screening(screening: dict) -> dict:
    """Attach conservative field follow-up and links without inferring a cure."""
    candidates = []
    for candidate in screening.get("candidates", []):
        info = _CLASS_INFO.get(candidate.get("class_name"))
        if info:
            candidates.append(dict(info))

    is_healthy_candidate = any(item.get("code") is None for item in candidates)
    steps = [
        "Treat these image labels as possibilities only. Compare them with the whole plant, the reported symptoms, and how the problem is changing; a photo score alone cannot confirm the cause.",
        "Record the date, farm or field, affected plant parts, and whether new plants are becoming affected. Keep a few clear follow-up photos for your CropPulse report; seek a qualified local extension worker for agronomic assessment.",
        "Ask local extension staff about prevention options suited to your district and season. FAO notes that crop protection choices, including rotation and varieties, must fit local conditions.",
    ]
    if is_healthy_candidate:
        steps.insert(0, "A healthy-looking model candidate does not rule out a problem. If symptoms continue or worsen, keep the report open for human review.")

    source_list = [dict(SOURCES["fao_ipm"]), dict(SOURCES["plantwise_rwanda"]), dict(SOURCES["rab"])]
    for item in candidates:
        if item.get("url"):
            source_list.append({
                "name": f"EPPO Global Database: {item['organism']} ({item['code']})",
                "url": item["url"],
                "scope": "Pest identity and common name reference only; not a Rwanda diagnosis or treatment guide.",
            })

    return {
        "version": GUIDANCE_VERSION,
        "title": "Safe next steps",
        "steps": steps,
        "treatment_notice": "CropPulse does not recommend a pesticide, medicine, active ingredient, dose, or spray schedule from this image. Do not treat from a model label. Ask a qualified local crop-protection professional to confirm the problem and check current Rwanda registration and the product label before any pesticide use.",
        "candidates": candidates,
        "sources": source_list,
    }


def attach_guidance(screening: dict) -> dict:
    """Return a copy so callers and tests cannot mutate the model result."""
    result = dict(screening)
    result["guidance"] = guidance_for_screening(result)
    return result
