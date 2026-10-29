"""Rwanda crop-planning knowledge pack. GENERAL GUIDANCE ONLY: approximate, compiled for planning support, not official
statistics or agronomic prescriptions. Add other countries later as knowledge packs with the same shape."""
from utils.geography import DISTRICT_TO_PROVINCE

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
SEASONS = {"A": "Sep–Feb (main rains)", "B": "Mar–Jun", "C": "Jul–Aug (marshland / irrigated)"}
ZONES = {"H": "Northern Highlands", "W": "Western Highlands & Lake Kivu", "C": "Central Plateau", "E": "Eastern Lowlands"}
ZONE_NOTE = {"H": "Cool, high rainfall, fertile volcanic soils; steep slopes need erosion control.",
             "W": "Hilly, high rainfall, Congo-Nile crest and Lake Kivu shore; good for tree and perennial crops.",
             "C": "Mid-altitude hills and marshland valleys; the most varied farming zone.",
             "E": "Warm, lower and less reliable rainfall; drought risk is highest here."}
# district: (zone, lat, lon). Zones are broad CropPulse groupings (not an official classification); centres are approximate.
_D = {"Musanze": "H -1.50 29.63", "Burera": "H -1.47 29.85", "Gakenke": "H -1.70 29.78", "Rulindo": "H -1.75 29.97", "Nyabihu": "H -1.65 29.50",
      "Gicumbi": "H -1.58 30.07", "Rubavu": "W -1.68 29.30", "Rutsiro": "W -1.95 29.35", "Karongi": "W -2.15 29.35", "Ngororero": "W -1.87 29.62",
      "Nyamasheke": "W -2.35 29.10", "Rusizi": "W -2.50 28.95", "Nyamagabe": "W -2.47 29.57", "Nyaruguru": "W -2.72 29.52",
      "Muhanga": "C -2.08 29.75", "Kamonyi": "C -2.00 29.90", "Ruhango": "C -2.22 29.78", "Nyanza": "C -2.35 29.75", "Huye": "C -2.60 29.74",
      "Gisagara": "C -2.62 29.83", "Gasabo": "C -1.90 30.10", "Kicukiro": "C -1.99 30.10", "Nyarugenge": "C -1.95 30.05", "Rwamagana": "C -1.95 30.43",
      "Nyagatare": "E -1.30 30.33", "Gatsibo": "E -1.60 30.40", "Kayonza": "E -1.85 30.65", "Kirehe": "E -2.20 30.70", "Ngoma": "E -2.15 30.50",
      "Bugesera": "E -2.15 30.15"}
DISTRICTS = {k: (v.split()[0], float(v.split()[1]), float(v.split()[2])) for k, v in _D.items()}


def C(rw, days, plant, alt, water, seed, ys, yg, suit, tips, perennial=False):
    return dict(rw=rw, days=days, plant=plant, alt=alt, water=water, seed=seed, ys=ys, yg=yg, suit=dict(zip("HWCE", map(int, suit))), tips=tips, perennial=perennial)


AB = {"A": [9, 10], "B": [3, 4]}
CROPS = {
 "Maize": C("ibigori", (100, 150), {**AB, "C": [7]}, (1000, 2200), "Medium", (20, 25, "kg seed"), (1.5, 3), (4, 6), "2233", ["Plant at the onset of rains, in rows.", "Scout weekly for fall armyworm."]),
 "Beans": C("ibishyimbo", (70, 120), {"A": [9, 10], "B": [2, 3], "C": [7]}, (1000, 2300), "Medium", (60, 100, "kg seed"), (0.8, 1.5), (2, 2.5), "3332", ["Climbing beans yield more per area but need stakes.", "Rotate with a cereal to reduce disease."]),
 "Irish potato": C("ibirayi", (90, 120), {"A": [9, 10], "B": [2, 3]}, (1700, 2800), "Medium", (1500, 2500, "kg seed tubers"), (8, 15), (20, 30), "3211", ["Use clean, certified seed tubers.", "Late blight spreads in cool, wet weather: scout often."]),
 "Cassava": C("imyumbati", (270, 365), AB, (900, 1700), "Low", (8000, 12000, "cuttings"), (8, 15), (20, 30), "1233", ["Use disease-free cuttings.", "Mosaic and brown streak are the main risks."]),
 "Sorghum": C("amasaka", (100, 140), {"A": [9, 10], "B": [3]}, (900, 1800), "Low", (8, 10, "kg seed"), (1, 2), (2.5, 4), "1123", ["A good fit for drier eastern areas.", "Protect the crop from birds near harvest."]),
 "Rice": C("umuceri", (120, 150), {**AB, "C": [7]}, (900, 1800), "High", (40, 60, "kg seed"), (3, 5), (6, 8), "1222", ["Needs reliable water: marshland or irrigation.", "Follow the cooperative's water schedule."]),
 "Sweet potato": C("ibijumba", (90, 150), {**AB, "C": [7]}, (900, 2200), "Low", (30000, 40000, "vine cuttings"), (6, 10), (15, 25), "3332", ["Orange-fleshed types add vitamin A.", "Vines can be cut from an existing field."]),
 "Soybean": C("soya", (90, 120), AB, (1000, 1800), "Medium", (60, 80, "kg seed"), (0.8, 1.2), (2, 2.5), "1233", ["Fixes nitrogen: good before a cereal.", "Check local inoculant availability."]),
 "Wheat": C("ingano", (110, 150), {"A": [9, 10], "B": [3]}, (1800, 2800), "Medium", (120, 150, "kg seed"), (1, 2), (3, 4), "3111", ["Cool highlands only.", "Watch for rust diseases."]),
 "Banana": C("ibitoki", (365, 450), AB, (1000, 2000), "High", (1100, 1600, "suckers"), (8, 15), (20, 30), "1332", ["Mulch and manage suckers.", "Use clean material: wilt and weevils spread on tools and suckers."], True),
 "Coffee": C("ikawa", (900, 1100), AB, (1400, 2000), "Medium", (1600, 2500, "seedlings"), None, None, "2331", ["A long-term investment: join a cooperative.", "Shade and mulch protect the trees. First harvest after ~2.5–3 years."], True),
 "Tea": C("icyayi", (900, 1100), AB, (1500, 2500), "High", (11000, 15000, "plants"), None, None, "2311", ["Needs steady rain and a nearby processing factory.", "Long-term crop; first plucking after ~3 years."], True),
}


def season_for(month: int) -> str:
    return "A" if month in (9, 10, 11, 12, 1, 2) else ("B" if month in (3, 4, 5, 6) else "C")


def months_until(month: int, targets) -> int:
    return min((m - month) % 12 for m in targets)


def window_status(crop: str, season: str, month: int) -> str:
    ms = CROPS[crop]["plant"].get(season)
    if not ms:
        return "No month entry in the provisional CropPulse guide for this season"
    d = months_until(month, ms)
    if month in ms:
        return "Provisional CropPulse calendar includes the current month"
    listed_month = MONTHS[(month + d - 1) % 12]
    return f"Provisional CropPulse calendar lists {listed_month} in about {d} month(s)"


def harvest_text(crop: str, season: str, month: int) -> str:
    c = CROPS[crop]; ms = c["plant"].get(season)
    if not ms:
        return "n/a"
    if c["perennial"]:
        return "after ~1–3 years"
    start = month if month in ms else (month + months_until(month, ms) - 1) % 12 + 1
    return MONTHS[(start - 1 + round(sum(c["days"]) / 2 / 30)) % 12]


def calendar_matrix(keys=None):
    """crop x 12 months: 0 none, 1 plant, 2 growing, 3 harvest (approximate)."""
    out = {}
    for k in keys or CROPS:
        c = CROPS[k]; row = [0] * 12; dur = max(1, round(sum(c["days"]) / 2 / 30))
        for ms in c["plant"].values():
            for m in ms:
                for i in range(1, dur):
                    row[(m - 1 + i) % 12] = max(row[(m - 1 + i) % 12], 2)
                if not c["perennial"]:
                    row[(m - 1 + dur) % 12] = 3
        for ms in c["plant"].values():
            for m in ms:
                row[m - 1] = 1
        out[k] = row
    return out


def to_ha(value: float, unit: str) -> float:
    return {"hectares (ha)": value, "are (100 m²)": value / 100, "square metres": value / 10000}[unit]


def estimate(crop: str, area_ha: float, level: str = "smallholder"):
    c = CROPS[crop]; y = c["ys" if level == "smallholder" else "yg"]
    s = c["seed"]
    return {"seed": (s[0] * area_ha, s[1] * area_ha, s[2]), "harvest_kg": None if y is None else (y[0] * area_ha * 1000, y[1] * area_ha * 1000)}

GUIDANCE_SOURCE = "CropPulse provisional legacy guide (not locally reviewed by RAB or a qualified Rwanda agronomist; NISR statistics are kept separate and do not validate this guidance)"
