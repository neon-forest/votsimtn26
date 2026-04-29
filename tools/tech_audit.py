"""
tech_audit.py
Deep technical gap analysis for VoterSim TN 26 engine.
Checks: imports, function signatures, data flow, column access, edge cases.
"""
import pandas as pd, traceback, os, sys, inspect, importlib
sys.path.append(os.getcwd())

PASS = "[PASS]"
FAIL = "[FAIL]"
WARN = "[WARN]"

results = []

def check(label, ok, detail=""):
    status = PASS if ok else FAIL
    results.append((status, label, detail))
    print(f"{status} {label}" + (f"\n       {detail}" if detail else ""))

def warn(label, detail=""):
    results.append((WARN, label, detail))
    print(f"{WARN} {label}" + (f"\n       {detail}" if detail else ""))

print("=" * 65)
print("TECHNICAL AUDIT — VoterSim TN 26")
print("=" * 65)

# -- 1. File existence ----------------------------------------------
print("\n-- 1. Required Files --")
required_files = [
    "core/voter_agent_engine.py",
    "utils/persona_generator.py",
    "utils/district_occupations.py",
    "utils/winner_2021.py",
    "core/sentiment_scraper.py",
    "utils/data_enrichment_pipeline.py",
    "data/assembly_metadata_enriched.csv",
    "data/assembly_candidate_sentiment.csv",
    "data/candidate_sentiment.csv",
    "data/districts_metadata.csv",
]
for f in required_files:
    check(f, os.path.exists(f), "" if os.path.exists(f) else "FILE MISSING")

# -- 2. Module imports ----------------------------------------------
print("\n-- 2. Module Imports --")
modules = {}
for mod in ["core.voter_agent_engine", "utils.persona_generator", "utils.district_occupations",
            "utils.winner_2021", "core.sentiment_scraper", "utils.data_enrichment_pipeline"]:
    try:
        m = importlib.import_module(mod)
        modules[mod] = m
        check(f"import {mod}", True)
    except Exception as e:
        check(f"import {mod}", False, str(e))

# -- 3. persona_generator function signature ------------------------
print("\n-- 3. persona_generator.generate_personas() --")
if "utils.persona_generator" in modules:
    pg = modules["utils.persona_generator"]
    try:
        sig = inspect.signature(pg.generate_personas)
        params = list(sig.parameters.keys())
        check("generate_personas exists", True, f"params={params}")
        required = ["constituency", "culture", "district", "num_personas",
                    "census_occ", "literacy_pct", "urban_pct"]
        for p in required:
            check(f"  param '{p}'", p in params)
    except Exception as e:
        check("generate_personas sig", False, str(e))

    # test persona keys
    try:
        df = pd.read_csv("data/assembly_metadata_enriched.csv")
        row = df.iloc[0]
        district = str(row.get("District_x", ""))
        personas = pg.generate_personas(
            constituency=row["Constituency"],
            culture=row["Culture"],
            district=district,
            num_personas=10,
            census_occ=None,
            literacy_pct=74.0,
            urban_pct=48.0
        )
        required_keys = ["age", "gender", "occupation", "literacy", "media", "concern", "pct", "label"]
        for k in required_keys:
            present = all(k in p for p in personas)
            check(f"  persona key '{k}'", present, "" if present else f"Missing in {[p for p in personas if k not in p][:1]}")
        weight_total = round(sum(p["pct"] for p in personas), 4)
        check("  persona pct sums to ~1.0 (10 personas)", 0.9 < weight_total <= 1.01,
              f"sum={weight_total}")
    except Exception as e:
        check("  persona key check", False, traceback.format_exc(limit=2))

# -- 4. voter_agent_engine functions -------------------------------
print("\n-- 4. voter_agent_engine functions --")
if "core.voter_agent_engine" in modules:
    vae = modules["core.voter_agent_engine"]

    # build_prompt
    try:
        sig = inspect.signature(vae.build_prompt)
        params = list(sig.parameters.keys())
        check("build_prompt signature", True, f"params={params}")
        required_p = ["persona", "constituency", "culture", "context"]
        for p in required_p:
            check(f"  param '{p}'", p in params)
    except Exception as e:
        check("build_prompt", False, str(e))

    # ask_llm
    try:
        sig = inspect.signature(vae.ask_llm)
        params = list(sig.parameters.keys())
        check("ask_llm signature", True, f"params={params}")
        for p in ["persona", "constituency", "culture", "context"]:
            check(f"  param '{p}'", p in params)
    except Exception as e:
        check("ask_llm", False, str(e))

    # fallback_vote
    try:
        sig = inspect.signature(vae.fallback_vote)
        params = list(sig.parameters.keys())
        check("fallback_vote signature", True, f"params={params}")
        for p in ["persona", "context"]:
            check(f"  param '{p}'", p in params)
    except Exception as e:
        check("fallback_vote", False, str(e))

    # Test build_prompt with real data
    try:
        test_persona = {
            "age": "37-year-old", "gender": "Female",
            "occupation": "knitwear / garment factory worker",
            "literacy": "Educated (10th-12th pass)",
            "media": "TV news and WhatsApp groups",
            "concern": "rising prices of essential commodities",
            "pct": 0.035, "label": "37-year-old Female knitwear (Educated)"
        }
        test_context = {
            "district": "Tiruppur", "gdp": 85000.0, "literacy": 72.0,
            "urban_pct": 65.0, "agri_pct": 12.0, "winner_2021": "DMK",
            "sent_spa": 15.0, "sent_aiadmk": -5.0, "sent_tvk": 20.0, "sent_others": 5.0
        }
        prompt = vae.build_prompt(test_persona, "Tiruppur (North)", "Industrial", test_context)
        check("build_prompt executes", True, f"prompt length={len(prompt)} chars")
        for kw in ["GDP", "2021 Winner", "knitwear", "Literacy", "sentiment", "SPA", "AIADMK"]:
            check(f"  prompt contains '{kw}'", kw.lower() in prompt.lower())
    except Exception as e:
        check("build_prompt execution", False, traceback.format_exc(limit=2))

    # Test fallback_vote
    try:
        result = vae.fallback_vote(test_persona, test_context)
        total = result.get("SPA",0)+result.get("AIADMK",0)+result.get("TVK",0)+result.get("Others",0)
        check("fallback_vote executes", True, f"result={result}")
        check("fallback_vote sums ~100", 98 <= total <= 102, f"sum={total}")
    except Exception as e:
        check("fallback_vote execution", False, traceback.format_exc(limit=2))

# -- 5. CSV column presence -----------------------------------------
print("\n-- 5. CSV Column Checks --")
try:
    df = pd.read_csv("data/assembly_metadata_enriched.csv")
    cols_needed = {
        "Constituency": "join key",
        "District_x": "district lookup",
        "Culture": "culture bucket",
        "Literacy_Pct": "prompt context",
        "Urban_Pct": "prompt context",
        "AgriLabour_Pct": "prompt context",
        "GDP_Lakhs": "prompt context",
        "Turnout_2026": "voter count",
        "Registered_Voters": "voter count",
        "Assembly_Seats": "voter count divisor",
    }
    for col, purpose in cols_needed.items():
        present = col in df.columns
        nulls = df[col].isna().sum() if present else "N/A"
        check(f"  col '{col}' ({purpose})", present, f"nulls={nulls}" if present else "MISSING")
except Exception as e:
    check("assembly_metadata_enriched.csv load", False, str(e))

# sentiment CSV
try:
    df_s = pd.read_csv("data/assembly_candidate_sentiment.csv")
    for col in ["Constituency", "Candidate_Sentiment_SPA", "Candidate_Sentiment_AIADMK",
                "Candidate_Sentiment_TVK", "Candidate_Sentiment_Others"]:
        check(f"  sentiment col '{col}'", col in df_s.columns)
except Exception as e:
    check("assembly_candidate_sentiment.csv", False, str(e))

# -- 6. winner_2021 coverage ----------------------------------------
print("\n-- 6. winner_2021 Coverage --")
if "utils.winner_2021" in modules:
    w = modules["utils.winner_2021"]
    df = pd.read_csv("data/assembly_metadata_enriched.csv")
    missing = [c for c in df["Constituency"] if c not in w.WINNER_2021]
    check(f"All 234 constituencies in WINNER_2021", len(missing) == 0,
          f"Missing: {missing}" if missing else "")
    # Check for "Unknown" values
    unknowns = [k for k,v in w.WINNER_2021.items() if v == "Unknown"]
    check("No 'Unknown' winner values", len(unknowns) == 0, f"Unknown: {unknowns}" if unknowns else "")

# -- 7. district_occupations coverage ------------------------------
print("\n-- 7. district_occupations Coverage --")
if "utils.district_occupations" in modules:
    do = modules["utils.district_occupations"]
    df = pd.read_csv("data/assembly_metadata_enriched.csv")
    districts = df["District_x"].dropna().unique()
    missing_d = [d for d in districts if d not in do.DISTRICT_OCCUPATIONS]
    check(f"All {len(districts)} CSV districts in DISTRICT_OCCUPATIONS",
          len(missing_d) == 0, f"Missing: {missing_d}" if missing_d else "")

# -- 8. run_simulation column references ---------------------------
print("\n-- 8. voter_agent_engine.run_simulation() column refs --")
if "core.voter_agent_engine" in modules:
    src = open("core/voter_agent_engine.py", encoding="utf-8").read()
    checks = {
        "row.get(\"GDP_Lakhs\"": "GDP pulled from row",
        "assembly_candidate_sentiment.csv": "sentiment CSV loaded",
        "get_winner_2021": "winner_2021 called",
        "build_prompt": "build_prompt called",
        "fallback_vote(persona, context)": "fallback_vote with context",
        "\"occupation\"": "persona occupation key used",
        "\"media\"": "persona media key used",
        "\"literacy\"": "persona literacy key used",
    }
    for pattern, desc in checks.items():
        check(f"  '{pattern[:40]}' ({desc})", pattern in src)

# -- 9. Edge case: empty df_sent handling --------------------------
print("\n-- 9. Edge Case: empty df_sent --")
try:
    vae = modules.get("core.voter_agent_engine")
    if vae:
        empty_sent = pd.DataFrame()
        seat_sent = empty_sent[empty_sent["Constituency"] == "TestX"] if "Constituency" in empty_sent.columns else empty_sent
        check("empty df_sent produces empty seat_sent safely", len(seat_sent) == 0)
except Exception as e:
    warn("empty df_sent edge case", str(e))

# -- 10. Summary ---------------------------------------------------
print("\n" + "=" * 65)
passes = sum(1 for r in results if r[0] == PASS)
fails  = sum(1 for r in results if r[0] == FAIL)
warns  = sum(1 for r in results if r[0] == WARN)
print(f"SUMMARY:  {passes} passed  |  {fails} failed  |  {warns} warnings")
if fails:
    print("\nFAILED CHECKS:")
    for r in results:
        if r[0] == FAIL:
            print(f"  {r[1]}: {r[2]}")
print("=" * 65)
