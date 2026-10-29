"""Structured crop-planning prompts derived from the existing, unverified knowledge pack.

These are planning prompts, not agronomic prescriptions. All activity guidance is
provisional until locally reviewed by a qualified Rwanda agronomist.
"""
from datetime import date
import knowledge as K
from utils import geography as geo

EVIDENCE = {
    "source": K.GUIDANCE_SOURCE,
    "verification_status": "Provisional; not locally verified",
    "expert_review_status": "Review required before field use",
    "last_reviewed": None,
    "evidence_status": "Provisional; no locally verified agronomic source is connected",
    "limitations": [
        "No soil test, farm-level weather, variety, pest surveillance, or extension visit is available.",
        "Timing prompts organize a plan; they are not validated local activity dates.",
        "Confirm fertilizer, pesticide, and crop-health decisions with a qualified local advisor.",
    ],
}


def build_plan(crop: str, district: str, season: str, planting_date: date,
               area_ha: float, water: str = "Unknown", irrigation: str = "Unknown",
               soil: str = "Unknown") -> dict:
    if crop not in K.CROPS:
        raise ValueError("Choose a crop from the CropPulse crop guide.")
    canonical = geo.normalize_district(district)
    if not canonical:
        raise ValueError("Choose a recognized Rwanda district.")
    if season not in K.SEASONS:
        raise ValueError("Season must be A, B, or C.")
    if area_ha <= 0:
        raise ValueError("Farm area must be greater than zero.")

    info = K.CROPS[crop]
    zone = K.DISTRICTS[canonical][0]
    seed_lo, seed_hi, seed_unit = info["seed"]
    resource = K.estimate(crop, area_ha)
    seed_range = resource["seed"]
    expected_days = round(sum(info["days"]) / 2)
    harvest_low = planting_date.fromordinal(planting_date.toordinal() + info["days"][0])
    harvest_high = planting_date.fromordinal(planting_date.toordinal() + info["days"][1])
    planting_months = info["plant"].get(season, [])
    window_fit = planting_date.month in planting_months

    # Prompts deliberately avoid inventing fertilizer/pesticide rates or dates.
    activities = [
        {"stage": "Before planting", "activity": "Prepare the field and check drainage, erosion risk, and access to water.",
         "timing": "Before the intended planting date", "reason": "Field conditions affect establishment; the appropriate method depends on the plot.",
         "conditions": f"District zone: {K.ZONES[zone]}. Soil supplied: {soil}.", "resources": "Local field inspection; soil test if available.",
         "warning": "No plot-level soil or slope data is available.", "evidence": "Provisional planning prompt"},
        {"stage": "Before planting", "activity": f"Plan planting material: approximately {seed_range[0]:,.0f}–{seed_range[1]:,.0f} {seed_unit} for {area_ha:g} ha.",
         "timing": "Before sourcing inputs", "reason": "Calculated by scaling the crop guide's indicative per-hectare range.",
         "conditions": "Quantity is an estimate; variety and local recommendations can change requirements.", "resources": "Confirm variety, quality, and availability with an extension officer or trusted supplier.",
         "warning": "CropPulse guidance has not been verified by RAB/NISR.", "evidence": "Calculation from CropPulse-compiled guidance"},
        {"stage": "Planting", "activity": f"Use the selected planting date ({planting_date:%d %b %Y}) as a planning target; check local conditions before sowing.",
         "timing": "Selected date", "reason": f"CropPulse calendar months for Season {season}: {', '.join(K.MONTHS[m-1] for m in planting_months) or 'no listed window'}.",
         "conditions": "Selected month is " + ("within" if window_fit else "outside") + " the pack's indicative months.",
         "resources": "Quality planting material; locally appropriate spacing guidance.", "warning": "This is not a weather-based planting recommendation.",
         "evidence": "Unverified calendar in CropPulse knowledge pack"},
        {"stage": "Soil fertility", "activity": "Use a soil test or local extension recommendation to decide whether and how to amend soil.",
         "timing": "Before planting and as advised locally", "reason": "No verified soil profile or fertilizer recommendation is available in this app.",
         "conditions": f"Known soil information: {soil}.", "resources": "Soil test and qualified local advice.",
         "warning": "CropPulse does not prescribe fertilizer products or rates.", "evidence": "Safe fallback; no crop-specific verified recommendation"},
        {"stage": "Water", "activity": "Check field moisture and the reliability of water access; record any irrigation or water constraints.",
         "timing": "At planting and during crop growth", "reason": f"The crop guide categorizes water need as {info['water']} (unverified relative guidance).",
         "conditions": f"Availability: {water}; irrigation: {irrigation}.", "resources": "Water source and local forecast, if available.",
         "warning": "No farm-level rainfall or soil-moisture data is available.", "evidence": "Provisional crop guidance"},
        {"stage": "Weed management", "activity": "Inspect the field regularly and choose weed control appropriate to the crop and local advice.",
         "timing": "During establishment and crop growth; confirm locally", "reason": "Weeds can compete with crops; CropPulse has no verified crop-specific control schedule.",
         "conditions": "Do not apply herbicides based on this prompt.", "resources": "Local extension advice and safe handling guidance.",
         "warning": "No pesticide or herbicide rates are provided.", "evidence": "General planning prompt"},
        {"stage": "Crop health", "activity": "Scout the crop and record unusual symptoms; seek diagnosis before applying treatments.",
         "timing": "At regular field visits", "reason": "The crop guide includes these crop-specific reminders: " + " ".join(info['tips']),
         "conditions": "No current pest/disease reports or diagnostic service is connected.", "resources": "Extension officer; clear photos and date/location of observation.",
         "warning": "This app cannot diagnose crop disease.", "evidence": "CropPulse-compiled reminders; unverified"},
        {"stage": "Growth and records", "activity": "Record field visits, inputs, weather impacts, and changes to the plan.",
         "timing": "Throughout the crop cycle", "reason": "Farm records support next-season planning and help assess what happened on this farm.",
         "conditions": "Records entered here are farmer-reported, not independently verified.", "resources": "CropPulse Farm Records page.",
         "warning": "Records are farmer-reported. Persistence depends on whether the current signed-in account service is available; confirm the save result in Farm Records.", "evidence": "Record-keeping workflow"},
        {"stage": "Harvest", "activity": "Inspect crop maturity and confirm harvest timing with local crop guidance.",
         "timing": f"Indicative range: {harvest_low:%d %b %Y}–{harvest_high:%d %b %Y} ({info['days'][0]}–{info['days'][1]} days after planting)",
         "reason": f"Range calculated from the knowledge pack's indicative {info['days'][0]}–{info['days'][1]} day duration.",
         "conditions": f"Midpoint estimate: about {expected_days} days; actual maturity depends on variety and conditions.",
         "resources": "Crop-specific maturity signs from an extension officer.", "warning": "Not a yield or harvest guarantee.",
         "evidence": "Date calculation from unverified CropPulse guidance"},
        {"stage": "Post-harvest", "activity": "Dry, sort, and store the harvest using crop-appropriate local guidance; record quantity and losses.",
         "timing": "At and after harvest", "reason": "Safe storage and harvest records help protect food and inform future plans.",
         "conditions": "Storage methods depend on crop, moisture, equipment, and local conditions.", "resources": "Clean storage area and crop-specific extension advice.",
         "warning": "CropPulse has no verified crop-specific storage protocol.", "evidence": "General planning prompt"},
    ]
    return {"crop": crop, "district": canonical, "season": season, "planting_date": planting_date,
            "area_ha": area_ha, "zone": K.ZONES[zone], "province": geo.DISTRICT_TO_PROVINCE[canonical],
            "window_fit": window_fit, "yield_range_kg": resource["harvest_kg"],
            "evidence": dict(EVIDENCE), "activities": activities}
