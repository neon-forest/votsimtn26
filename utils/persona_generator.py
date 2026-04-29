"""
persona_generator.py
====================
Generates 50 unique, statistically grounded voter personas per constituency.

DETERMINISTIC: No randomness. Each persona is derived from the exact Census
cross-product of age × gender × occupation × literacy, ranked by population
weight, and the top 50 taken. Same constituency = same 50 personas every time.

Each persona is a unique combination of:
  - Age group (5 groups, ECI 2026 proportions)
  - Gender (Male/Female, ECI 2026: 48.9% / 51.1%)
  - Occupation (Census 2011 B-series district data)
  - Literacy level (Census 2011 per district, urban/rural split)
  - Primary political concern (first tag from occupation's concern list)

Census sources:
  - Age: ECI SIR 2026 electoral roll breakdown
  - Occupation: Census 2011 Primary Census Abstract B-29
  - Literacy: Census 2011 per district
"""

from itertools import product
from .data_enrichment_pipeline import CENSUS_2011_OCCUPATION, ECI_STATEWIDE
from .district_occupations import DISTRICT_OCCUPATIONS

# ──────────────────────────────────────────────────────────────────────────────
# DIMENSION DEFINITIONS
# ──────────────────────────────────────────────────────────────────────────────

AGE_GROUPS = [
    {"label": "18-22", "desc": "18-year-old",  "weight_eci": 0.07,  "type": "youth"},
    {"label": "23-29", "desc": "26-year-old",  "weight_eci": 0.14,  "type": "young_adult"},
    {"label": "30-44", "desc": "37-year-old",  "weight_eci": 0.30,  "type": "working"},
    {"label": "45-59", "desc": "52-year-old",  "weight_eci": 0.28,  "type": "middle_aged"},
    {"label": "60+",   "desc": "65-year-old",  "weight_eci": 0.21,  "type": "senior"},
]

GENDERS = [
    {"label": "Male",   "weight": 0.489},
    {"label": "Female", "weight": 0.511},
]



CONCERN_DESCRIPTIONS = {
    "electricity_tariff":  "rising electricity tariffs and power cuts affecting daily life",
    "inflation":           "rising prices of essential commodities, vegetables, and cooking oil",
    "infrastructure":      "poor roads, drainage, and urban infrastructure",
    "tax":                 "income tax burden and GST on middle class",
    "stability":           "law and order, stability, and strong governance",
    "da_hike":             "DA (Dearness Allowance) hike for government employees",
    "job_security":        "employment stability and fear of layoffs",
    "admin":               "administrative efficiency and transparency",
    "gst":                 "GST burden on small traders and businesses",
    "local_mla":           "local MLA's constituency development performance",
    "fuel_price":          "rising petrol/diesel prices affecting livelihoods",
    "gig_rights":          "lack of social security for gig and contract workers",
    "wages":               "low wages and delayed salary payments",
    "neet":                "NEET exam opposition and Tamil Nadu's fight for state-controlled medical admissions",
    "youth_unemployment":  "lack of jobs for educated youth and college graduates",
    "tvk":                 "TVK and Vijay's fresh alternative to traditional Dravidian politics",
    "magalir_scheme":      "Magalir Urimai Thogai (Rs.1000/month) and SPA's women's welfare schemes",
    "free_bus":            "free bus travel for women introduced by the SPA government",
    "family_welfare":      "family health, education costs, and household welfare",
    "union_rights":        "trade union rights and factory worker protections",
    "aiadmk_legacy":       "AIADMK's history of welfare for industrial workers",
    "aiadmk_loyalty":      "deep-rooted loyalty to AIADMK and its legacy",
    "factory_safety":      "workplace safety and compensation in factories",
    "female_safety":       "women's safety in industrial workplaces",
    "electricity_cost":    "electricity costs for factory operations affecting employment",
    "union_politics":      "trade union politics and factory-level power dynamics",
    "anti_incumbency":     "anger against the incumbent SPA government's performance",
    "cauvery_water":       "Cauvery River water sharing dispute with Karnataka for farming",
    "loan_waiver":         "agricultural loan waiver and debt relief for farmers",
    "msp":                 "minimum support price for paddy and agri produce",
    "crop_insurance":      "crop insurance and flood relief for farmers",
    "flood_relief":        "flood damage compensation and disaster management",
    "mgnrega":             "MGNREGA wage rates and 100-day work guarantee",
    "ration_shop":         "PDS ration shop quality and free rice scheme continuation",
    "free_rice":           "free rice scheme (10kg/month) continuation",
    "subsidy":             "agricultural subsidies (fertilizer, seed, irrigation)",
    "education_access":    "access to quality higher education in rural areas",
    "education":           "quality of public education and teacher availability",
    "free_laptop":         "AIADMK's free laptop scheme for students",
    "welfare_delivery":    "efficient delivery of welfare schemes without corruption",
    "corruption":          "corruption in government scheme delivery",
    "fishermen_welfare":   "fishermen welfare, boat subsidies, and sea access rights",
    "community_rep":       "political representation for their caste/community",
    "caste_alliance":      "caste-based political alliances and community voting blocs",
    "agri_subsidy":        "subsidies for farmers and agricultural inputs",
    "water_supply":        "drinking water and irrigation water supply",
    "social_justice":      "Dalit rights, social justice, and reservation policies",
    "housing":             "affordable housing and slum development",
    "pension":             "pension for elderly and retirement benefits",
    "party_loyalty":       "lifetime loyalty to their traditional Dravidian party",
    "state_autonomy":      "Tamil Nadu's autonomy from central government policies",
    "market":              "local market stability and trader protection",
    "womens_safety":       "women's safety and gender-based violence",
    "tvk_factor":          "TVK's promise of a clean break from corrupt Dravidian politics",
    "welfare":             "government welfare scheme coverage and quality",
    "family":              "family wellbeing and household economic stability",
    "overtime":            "overtime pay and working hours in factories",
    "aiadmk_history":      "AIADMK's historical connection to this community",
    "community_politics":  "community-level political representation and power",
    "caste_loyalty":       "deep caste-based loyalty to a political party",
    "electricity":         "electricity supply reliability and pricing",
    "borewell_subsidy":    "borewell and irrigation well subsidies for dryland farmers",
    "cattle_insurance":    "livestock insurance and cattle healthcare",
    "aavin_price":         "Aavin milk procurement price and dairy farmer welfare",
    "fishing_rights":      "fishing rights and maritime border security with Sri Lanka",
    "diesel_subsidy":      "diesel subsidies for mechanized fishing boats",
    "weather_relief":      "compensation for days lost due to extreme weather warnings",
    "emi_burden":          "rising EMI burden on middle-class families",
    "jobs":                "local job creation and employment opportunities",
    "yarn_price":          "yarn price volatility impacting garment units",
    "exports":             "export incentives and global market stability",
    "health_safety":       "occupational health and workplace safety measures",
    "toll_charges":        "high toll plaza charges affecting logistics and transport",
    "road_conditions":     "poor road maintenance and highways infrastructure",
    "forest_rights":       "tribal forest rights and land ownership",
    "wildlife_conflict":   "human-wildlife conflict and crop damage compensation",
    "feed_prices":         "poultry feed prices and agricultural commodity costs",
    "tax_burden":          "increasing tax burden and professional taxes",
    "local_economy":       "revival of local trade and small-scale industries",
}

LITERACY_LEVELS = [
    {"level": "Highly educated (graduate+)", "w_urban": 0.40, "w_rural": 0.10, "media": "social media and online news"},
    {"level": "Educated (10th-12th pass)",   "w_urban": 0.35, "w_rural": 0.30, "media": "TV news and WhatsApp groups"},
    {"level": "Primary school literate",     "w_urban": 0.15, "w_rural": 0.35, "media": "TV and word of mouth"},
    {"level": "Functionally illiterate",     "w_urban": 0.10, "w_rural": 0.25, "media": "word of mouth and local leaders"},
]


def _build_adjusted_occ_pool(district, census_occ):
    """
    Build and return a *copy* of the occupation pool for a given district,
    with weights adjusted by real Census data if provided.
    Returns a new list (never mutates the module-level data).
    """
    base_pool = DISTRICT_OCCUPATIONS.get(district, DISTRICT_OCCUPATIONS["_default"])
    # Deep copy so we never mutate module-level data
    occ_pool = [dict(o) for o in base_pool]

    if census_occ:
        cultivators_pct, agri_pct, industry_pct, services_pct, _, _ = census_occ
        for occ in occ_pool:
            if "farmer" in occ["occ"] or "cultivat" in occ["occ"]:
                occ["w"] = max(0.01, occ["w"] * (cultivators_pct / 12.9))
            elif "labour" in occ["occ"] or "agricultural" in occ["occ"]:
                occ["w"] = max(0.01, occ["w"] * (agri_pct / 29.2))
            elif "factory" in occ["occ"] or "mill" in occ["occ"] or "garment" in occ["occ"]:
                occ["w"] = max(0.01, occ["w"] * (industry_pct / 4.2))

        # Normalize
        total_w = sum(o["w"] for o in occ_pool)
        for occ in occ_pool:
            occ["w"] = occ["w"] / total_w

    return occ_pool


def generate_personas(constituency, culture, district, num_personas=50,
                      census_occ=None, literacy_pct=74, urban_pct=48):
    """
    Generate `num_personas` deterministic voter personas for a given constituency.

    Method:
      1. Build the full cross-product of age × gender × occupation × literacy.
      2. Compute population weight for each cell = product of dimension weights.
      3. Sort descending by weight.
      4. Take the top `num_personas` cells.
      5. Normalize weights so they sum to 1.0.

    Same inputs → same output. No randomness.

    Returns list of dicts, each with:
      - label, age, gender, occupation, literacy, media, concern, concern_tag,
        age_type, raw_weight, pct
    """
    is_urban = urban_pct > 50
    # 1. Build adjusted occupation pool using DISTRICT data
    occ_pool = _build_adjusted_occ_pool(district, census_occ)

    # Select literacy weights based on urban/rural
    literacy_weights = []
    for lit in LITERACY_LEVELS:
        w = lit["w_urban"] if is_urban else lit["w_rural"]
        literacy_weights.append(w)

    # ── Build full cross-product with population weights ──────────────
    cells = []
    for age, gender, occ, (lit_idx, lit) in product(
        AGE_GROUPS, GENDERS, occ_pool,
        enumerate(LITERACY_LEVELS)
    ):
        weight = (
            age["weight_eci"]
            * gender["weight"]
            * occ["w"]
            * literacy_weights[lit_idx]
        )
        cells.append((weight, age, gender, occ, lit))

    # ── Sort descending by weight (deterministic: weight is unique enough,
    #    but we add a tiebreaker on label components for total ordering) ──
    cells.sort(key=lambda c: (
        -c[0],                       # primary: highest weight first
        c[1]["label"],               # tiebreak: age label (alphabetical)
        c[2]["label"],               # tiebreak: gender
        c[3]["occ"],                 # tiebreak: occupation name
        c[4]["level"],               # tiebreak: literacy level
    ))

    # ── Take top N ────────────────────────────────────────────────────
    top_cells = cells[:num_personas]

    # ── Build persona dicts ───────────────────────────────────────────
    personas = []
    for weight, age, gender, occ, lit in top_cells:
        # Deterministic concern: always the first tag in the occupation's list
        concern_tag = occ["concern_tags"][0]
        concern_desc = CONCERN_DESCRIPTIONS.get(concern_tag, concern_tag.replace("_", " "))

        label = (f"{age['desc']} {gender['label']} {occ['occ']} "
                 f"({lit['level']})")

        personas.append({
            "label":        label,
            "age":          age["desc"],
            "gender":       gender["label"],
            "occupation":   occ["occ"],
            "literacy":     lit["level"],
            "media":        lit["media"],
            "concern":      concern_desc,
            "concern_tag":  concern_tag,
            "age_type":     age["type"],
            "raw_weight":   weight,
        })

    # ── Normalize weights so they sum to 1.0 ──────────────────────────
    total_w = sum(p["raw_weight"] for p in personas)
    for p in personas:
        p["pct"] = p["raw_weight"] / total_w if total_w > 0 else 1.0 / len(personas)

    return personas



if __name__ == "__main__":
    # Test: Generate 50 personas for Chennai Urban constituency
    from data_enrichment_pipeline import CENSUS_2011_OCCUPATION
    census = CENSUS_2011_OCCUPATION.get("Chennai")

    personas = generate_personas(
        constituency="Anna Nagar",
        culture="Urban",
        district="Chennai",
        num_personas=50,
        census_occ=census,
        literacy_pct=90.2,
        urban_pct=100.0
    )

    print(f"Generated {len(personas)} personas for Anna Nagar (Chennai Urban)")
    print(f"{'#':3} {'Label':70} {'Pct':6} {'Concern'}")
    print("-" * 130)
    for i, p in enumerate(personas, 1):
        print(f"{i:3} {p['label'][:70]:70} {p['pct']*100:5.1f}%  {p['concern'][:50]}")
    print(f"\nTotal weight: {sum(p['pct'] for p in personas):.3f}")

    # Verify determinism: run twice, confirm identical
    personas2 = generate_personas(
        constituency="Anna Nagar",
        culture="Urban",
        district="Chennai",
        num_personas=50,
        census_occ=census,
        literacy_pct=90.2,
        urban_pct=100.0
    )
    assert [p["label"] for p in personas] == [p["label"] for p in personas2], "DETERMINISM VIOLATED!"
    assert [p["pct"]   for p in personas] == [p["pct"]   for p in personas2], "DETERMINISM VIOLATED!"
    print("\n[OK] Determinism verified: two runs produce identical personas.")
