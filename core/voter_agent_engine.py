"""
voter_agent_engine.py
=====================
Constituency-level Voter Simulation Engine

For each of the 234 assembly constituencies:
  1. Computes the exact number of polled voters from real Registered_Voters & Turnout data.
  2. Distributes those voters across Culture-specific Demographic Persona Buckets.
  3. [DEBATE MODE] 3 specialist analyst agents independently vote on the persona (Round 1),
     then each revises after seeing the others' reasoning (Round 2),
     then a neutral Moderator synthesizes the final consensus vote (Round 3).
  4. Multiplies bucket sizes × vote-split percentages to produce EXACT vote counts.
  5. Saves per-seat exact results + per-persona logs (including per-round debate transcripts).
"""

import asyncio
import pandas as pd
import numpy as np
import requests
import json
import random
import os
import threading
import signal
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from .ollama_async_client import get_llm_client

CHECKPOINT_FILE = "simulation_checkpoint.json"
_stop_requested = False

def _load_checkpoint():
    """Return set of constituency names already completed."""
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return set(data.get("completed", []))
    return set()

def _save_checkpoint(completed_set):
    """Atomically persist completed constituency names."""
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump({"completed": list(completed_set)}, f, indent=2)

def _handle_signal(sig, frame):
    global _stop_requested
    print("\n[STOP] Ctrl+C received — finishing in-flight constituencies then saving checkpoint...")
    _stop_requested = True
from utils.persona_generator import generate_personas
from utils.data_enrichment_pipeline import CENSUS_2011_OCCUPATION
from utils.winner_2021 import get_winner_2021

NUM_PERSONAS = 50  # personas per constituency

OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_IS_RUNNING    = True
GOOGLE_IS_AVAILABLE = True

# ── Engine config ─────────────────────────────────────────────────────────────
USE_DEBATE_MODE      = True
BATCH_SIZE           = 50   # Fast mode: One API call per Round per Seat
STAR_SEATS = {
    # --- SPA (DMK Alliance) ---
    "Kolathur": {"SPA": 30},              # M.K. Stalin
    "Chepauk-Thiruvallikeni": {"SPA": 25}, # Udhayanidhi Stalin
    "Bodinayakanur": {"SPA": 20},         # O. Panneerselvam (Aligned with SPA)
    "Coimbatore (South)": {"SPA": 15},    # Senthil Balaji
    "Tiruchirappalli (West)": {"SPA": 15}, # K.N. Nehru
    "Katpadi": {"SPA": 15},               # Durai Murugan
    "Harbour": {"SPA": 15},               # P.K. Sekar Babu

    # --- AIADMK ---
    "Edappadi": {"AIADMK": 30},           # Edappadi K. Palaniswami

    # --- TVK (Vijay) ---
    "Perambur": {"TVK": 30},              # Vijay (Seat 1)
    "Tiruchirappalli (East)": {"TVK": 25}, # Vijay (Seat 2)

    # --- Others (NTK/AMMK) ---
    "Thiruvotriyur": {"Others": 25},      # Seeman (NTK)
    "Kovilpatti": {"Others": 20},         # TTV Dhinakaran
}
DEBATE_PARALLEL_WORKERS = 3

# Google Gemini 2.0 Flash: process 4 constituencies at once.
CONSTITUENCY_WORKERS = 4

# ──────────────────────────────────────────────────────────────────────────────
# CULTURE -> DEMOGRAPHIC BUCKET DEFINITIONS
# Based on REAL data:
#   - ECI Tamil Nadu 2026 SIR Electoral Roll:
#       Total Electorate: 5.73 crore | Female: 51.1% | Male: 48.9%
#       Youth (18-29): 21.2% of electorate | First-time (18-19): 2.5%
#       Working-age (30-49): ~42% | Senior (50-60+): ~36.8%
#   - Census 2011 Occupation (statewide workers):
#       Cultivators: 12.9% | Agricultural Labourers: 29.2%
#       Household Industry: 4.2% | Other Workers (services/IT/trade): 53.7%
#   - TN Urbanization 2011: 48.45% urban overall
#       Chennai: ~90% urban | Coimbatore/Tiruppur: ~65% urban (industrial/textile)
#       Delta districts (Thanjavur, Tiruvarur, Nagapattinam): ~80% rural/agrarian
#       Southern (Madurai, Virudhunagar, Tirunelveli): ~55% urban mix
# ──────────────────────────────────────────────────────────────────────────────


ELECTION_CONTEXT = """
In the highly contested 2026 Tamil Nadu Assembly Elections, here is the political landscape:

PARTIES:
- SPA (Secular Progressive Alliance, led by DMK): The incumbent ruling party.
  Key welfare delivered: Magalir Urimai Thogai (Rs.1000/month for women), Free bus travel for women, Puthumai Penn (Rs.1000/month for college girls), Free school breakfast scheme.
  Negatives: Middle-class anger over inflation, rising electricity tariffs, drug and law-and-order issues, flood mismanagement.

- AIADMK+ (Main Opposition): The primary traditional Dravidian opposition.
  Key past welfare: Free laptops for students, Amma Canteens (subsidized food), Free mixies/grinders/fans, Gold for brides scheme, Free scooters for working women.
  They rely on a strong traditional rural base and deep organizational roots in the Western and Southern belts.

- TVK (Tamilaga Vettri Kazhagam): A new disruptive party led by actor Vijay. Very popular with first-time voters, youth, and those disillusioned with the Dravidian majors.

- Others (NTK/PMK/DMDK/Small parties): NTK is Tamil-nationalist and rural-farmer focused. PMK holds sway in specific OBC communities. Others split rural and caste-specific votes.

KEY STATE ISSUES: State autonomy vs central policies, NEET exam opposition, youth unemployment, rising inflation, local infrastructure gaps.
"""

def build_prompt(persona, constituency, culture, context):
    # Margin note
    margin = context.get("margin_2021", "COMFORTABLE")
    margin_note = {
        "LANDSLIDE":   "2021 win was a landslide (>25k margin). Incumbent has deep community roots.",
        "COMFORTABLE": "2021 win was comfortable (10-25k margin). Seat leans incumbent.",
        "CLOSE":       "2021 win was close (3-10k margin). This is a genuinely competitive seat.",
        "RAZOR_THIN":  "2021 win was razor-thin (<3k margin). Any swing could flip this seat.",
    }.get(margin, "")

    # Incumbent re-contesting note
    rcon = context.get("incumbent_recontesting", "UNKNOWN")
    rcon_note = {
        "YES":          "Incumbent MLA confirmed re-contesting — personal vote and name recognition in play.",
        "LIKELY_YES":   "Incumbent MLA likely re-contesting — party loyalty and local record matters.",
        "UNCERTAIN":    "Incumbent status UNCERTAIN — AIADMK internal pressures, alliance shifting.",
        "NO":           "Incumbent MLA NOT re-contesting — party fielding fresh face, wave vote dominates.",
        "UNKNOWN":      "",
    }.get(rcon, "")

    # SC/ST population note
    sc_pct = context.get("sc_st_pct", 16.0)
    sc_pop_note = f"Dalit/tribal population: {sc_pct:.0f}% (TN avg 20%). VCK-SPA Dalit bloc is significant here." if sc_pct > 19 else ""

    tvk_note = {
        "HIGH":        "TVK has very strong youth/urban traction here — 3-way split likely.",
        "MEDIUM_HIGH": "TVK is a serious spoiler in this seat.",
        "MEDIUM":      "TVK has moderate presence, mainly among youth.",
        "LOW":         "TVK has minimal influence here — caste or SPA loyalty dominates.",
    }.get(context.get("tvk_zone", "MEDIUM"), "")

    inc_note = {
        "SAFE_INCUMBENT":       "SPA incumbent has strong local support; anti-incumbency is low.",
        "HIGH_ANTI_INCUMBENCY": "Strong anti-incumbency against 2021 winner; voters want change.",
        "ANTI_INCUMBENCY":      "Moderate anti-incumbency; close contest expected.",
        "COMPETITIVE":          "Evenly contested; no strong incumbency advantage.",
    }.get(context.get("incumbency_factor", "COMPETITIVE"), "")

    sc_note = "This is a SC/ST reserved constituency. VCK and SPA have a guaranteed Dalit base here." if context.get("sc_boost") else ""
    surge_note = "HIGH turnout surge signals strong BASE MOBILISATION for SPA welfare beneficiaries." \
        if context.get("surge_type") == "BASE_MOBILISATION" \
        else "HIGH turnout surge signals ANTI-INCUMBENCY mobilisation against current MLA."

    return f"""System: You are simulating the voting decision of an individual voter in Tamil Nadu.
{ELECTION_CONTEXT}

CONSTITUENCY CONTEXT:
  Constituency: {constituency} ({culture} region, {context['district']} district)
  Seat Type: {context.get('seat_type', 'COMPETITIVE')} | 2021 Winner: {context['winner_2021']}
  District GDP: Rs.{context['gdp']} lakh crore. Literacy: {context['literacy']:.0f}%. Urban: {context['urban_pct']:.0f}%.
  2021 Victory Margin: {context.get('margin_2021', 'COMFORTABLE')} — {margin_note}
  Incumbent Re-contesting: {context.get('incumbent_recontesting', 'UNKNOWN')} — {rcon_note}
  Anti-Incumbency Score: {context.get('anti_inc_score', 0)} (scale -10 to +10; negative = challenger advantage)
  {inc_note}
  {tvk_note}
  {sc_note}
  {sc_pop_note}
  Turnout surge (+{context.get('turnout_delta', 0):.1f}%): {surge_note}

  Candidate Local Popularity (sentiment score, -100 to +100):
    SPA: {context['sent_spa']:.0f}, AIADMK: {context['sent_aiadmk']:.0f},
    TVK: {context['sent_tvk']:.0f}, Others: {context['sent_others']:.0f}

VOTER PROFILE:
  {context.get('voter_profile', '')}

VOTER PERSONA:
  {persona.get('age', '')} {persona.get('gender', '')}, works as: {persona.get('occupation', '')}.
  Education: {persona.get('literacy', '')}. Gets news from: {persona.get('media', '')}.
  Primary concern: {persona.get('concern', '')}.

Task: Given all the above, how does this specific voter split their vote?
Respond ONLY with a valid JSON object with exactly these five keys:
  {{"SPA": N, "AIADMK": N, "TVK": N, "Others": N, "Reason": "One sentence explaining this voter's decision."}}
Rules:
- The four numbers must sum to EXACTLY 100.
- Reason MUST be a non-empty sentence (at least 8 words) specific to this voter's profile and constituency.
"""


def synthesize_reason(vote_split, persona, context):
    """Generate a readable reason when the LLM returns an empty Reason field."""
    parties   = ["SPA", "AIADMK", "TVK", "Others"]
    labels    = {"SPA": "SPA (DMK)", "AIADMK": "AIADMK+", "TVK": "TVK", "Others": "Others"}
    ranked    = sorted(parties, key=lambda p: vote_split.get(p, 0), reverse=True)
    top, sec  = ranked[0], ranked[1]
    top_pct   = vote_split.get(top, 0)
    sec_pct   = vote_split.get(sec, 0)

    occ     = persona.get("occupation", "voter").lower()
    concern = persona.get("concern", "").lower()
    gender  = persona.get("gender", "voter").lower()
    age     = persona.get("age", "")
    district = context.get("district", "the constituency")
    winner21 = context.get("winner_2021", "")

    # Build a context-aware sentence
    concern_phrase = f"concerns about {concern}" if concern else "local development priorities"
    occ_phrase     = f"as a {occ}" if occ else ""

    if top_pct >= 60:
        strength = "strongly leans"
    elif top_pct >= 45:
        strength = "leans"
    else:
        strength = "slightly favours"

    if top == "SPA":
        rationale = "welfare schemes and incumbent governance track record"
    elif top == "AIADMK":
        rationale = "traditional opposition support and past governance record"
    elif top == "TVK":
        rationale = "Vijay's youth-centric agenda and anti-establishment appeal"
    else:
        rationale = "caste/community alignment and local candidate factors"

    reason = (
        f"This {age} {gender} {occ_phrase} in {district} {strength} {labels[top]} "
        f"({top_pct}% vs {labels[sec]} {sec_pct}%) driven by {rationale} "
        f"and {concern_phrase}."
    )
    return reason.strip()


def ask_llm(persona, constituency, culture, context):
    """Query LLM. Returns dict with SPA/AIADMK/TVK/Others adding to ~100."""
    client = get_llm_client("GEMINI" if GOOGLE_IS_AVAILABLE else "OLLAMA")
    prompt = build_prompt(persona, constituency, culture, context)
    data = client.call(prompt)
    
    if not data:
        return fallback_vote(persona, context)

    # Normalize so votes sum to exactly 100
    total = data.get("SPA", 0) + data.get("AIADMK", 0) + data.get("TVK", 0) + data.get("Others", 0)
    if total <= 0:
        return fallback_vote(persona, context)
    
    factor = 100.0 / total
    vote_split = {
        "SPA":    round(data.get("SPA", 0)    * factor),
        "AIADMK": round(data.get("AIADMK", 0) * factor),
        "TVK":    round(data.get("TVK", 0)    * factor),
        "Others": round(data.get("Others", 0) * factor),
        "Source": "LLM",
    }
    # Use LLM reason if non-empty, otherwise synthesize one
    raw_reason = data.get("Reason", "").strip()
    vote_split["Reason"] = raw_reason if len(raw_reason) > 10 else synthesize_reason(vote_split, persona, context)
    return vote_split

def fallback_vote(persona, context):
    """Heuristic fallback when Ollama is unavailable."""
    concern = persona.get("concern", "").lower()
    occ     = persona.get("occupation", "").lower()
    gender  = persona.get("gender", "").lower()

    spa, admk, tvk, others = 30, 25, 25, 20

    # ── Welfare voters lean SPA ───────────────────────────────────
    if "welfare" in concern or "magalir" in concern or "free bus" in concern or "ration" in concern:
        spa += 20; admk -= 8; tvk -= 8; others -= 4
    # ── Anti-inflation leans AIADMK (Softened) ────────────────────
    if "inflation" in concern or "electricity" in concern or "tariff" in concern:
        spa -= 4; admk += 4; tvk += 2; others += 1
    # ── Small business split ──────────────────────────────────────
    if "business" in occ or "small trad" in occ:
        admk += 4; tvk += 4; spa -= 6; others += 2
    # ── TVK youth factor ─────────────────────────────────────────
    if "tvk" in concern or "student" in occ or "youth" in concern:
        tvk += 20; spa -= 8; admk -= 8; others -= 4
    # ── Farmer/agri leans SPA + Others (NTK) ────────────────────
    if "farmer" in occ or "agricultur" in occ or "rice" in occ:
        spa += 8; others += 8; admk += 2; tvk -= 10
    # ── Factory/union leans AIADMK ───────────────────────────────
    if "factory" in occ or "knitwear" in occ or "mill" in occ:
        admk += 15; spa -= 5; tvk -= 5; others -= 5
    # ── Fisherman leans SPA/Others ───────────────────────────────
    if "fisherman" in occ or "coastal" in occ:
        spa += 10; others += 10; admk -= 10; tvk -= 5
    # ── Homemaker leans SPA (Magalir scheme) ─────────────────────
    if "homemaker" in occ:
        spa += 15; admk -= 5; tvk -= 5; others -= 5
    # ── Elderly/retired leans AIADMK/SPA ─────────────────────────
    if "retired" in gender or "elderly" in persona.get("label", ""):
        admk += 8; spa += 5; tvk -= 13

    # ── Structural factors from context ──────────────────────────
    # SC seat: VCK-SPA bloc guaranteed
    if context.get("sc_boost"):
        spa += 12; admk -= 8; tvk -= 3; others -= 1
    # Anti-incumbency score
    anti = context.get("anti_inc_score", 0)
    if anti <= -4:   # High anti-incumbency (challenger advantage)
        admk += 5; spa -= 6; tvk += 3; others += 1
    elif anti >= 4:  # Safe SPA incumbent (SPA advantage)
        spa += 6; admk -= 4; tvk -= 2; others -= 1
    # TVK zone
    tvk_zone = context.get("tvk_zone", "MEDIUM")
    if tvk_zone == "HIGH":        tvk += 10; spa -= 5; admk -= 5
    elif tvk_zone == "MEDIUM_HIGH": tvk += 5; spa -= 3; admk -= 2
    elif tvk_zone == "LOW":       tvk -= 10; spa += 5; admk += 5
    # Seat type
    seat_t = context.get("seat_type", "COMPETITIVE")
    if seat_t == "SAFE" and context["winner_2021"] == "DMK":
        spa += 8; admk -= 5; tvk -= 3
    elif seat_t == "MARGINAL":
        tvk += 3  # spoiler effect stronger in close seats
    # ── Sentiment boosts (Dynamic Sensitivity) ───────────────────
    # Star seats and Marginal seats are 3x more sensitive to leader popularity
    is_star = context.get("constituency") in STAR_SEATS or context.get("seat_type") == "MARGINAL"
    divisor = 4 if is_star else 12
    
    spa   += int(context.get("sent_spa", 0) / divisor)
    admk  += int(context.get("sent_aiadmk", 0) / divisor)
    tvk   += int(context.get("sent_tvk", 0) / divisor)
    others += int(context.get("sent_others", 0) / divisor)

    # ── Normalise ─────────────────────────────────────────────────
    vals = {"SPA": max(1, spa), "AIADMK": max(1, admk),
            "TVK": max(1, tvk), "Others": max(1, others)}
    total = sum(vals.values())
    vote_split = {k: round(v * 100 / total) for k, v in vals.items()}
    vote_split["Reason"] = synthesize_reason(vote_split, persona, context)
    return vote_split


# ══════════════════════════════════════════════════════════════════════════════
# GOOGLE BATCH ENGINE
# 50 personas → batches of BATCH_SIZE → one API call per batch
# ══════════════════════════════════════════════════════════════════════════════

def _batch_personas(personas: list, batch_size: int = BATCH_SIZE) -> list[list]:
    """
    Split personas into batches, interleaving age-types to minimise
    homogenisation bias (youth next to senior next to working, etc.).
    """
    pools = {
        "youth":       [],
        "young_adult": [],
        "working":     [],
        "middle_aged": [],
        "senior":      [],
    }
    for p in personas:
        pools.get(p.get("age_type", "working"), pools["working"]).append(p)

    interleaved = []
    pool_list   = [pools[k] for k in ["youth", "young_adult", "working", "middle_aged", "senior"]]
    while any(pool_list):
        for pool in pool_list:
            if pool:
                interleaved.append(pool.pop(0))

    return [interleaved[i:i + batch_size] for i in range(0, len(interleaved), batch_size)]


def _build_batch_prompt(batch: list[dict], constituency: str,
                        culture: str, context: dict) -> str:
    """Compact batch prompt — stays well within the 8,192-token context window."""
    margin_note = {
        "LANDSLIDE":   ">25k margin, incumbent deeply rooted.",
        "COMFORTABLE": "10-25k margin, seat leans incumbent.",
        "CLOSE":       "3-10k margin, genuinely competitive.",
        "RAZOR_THIN":  "<3k margin, any swing flips this seat.",
    }.get(context.get("margin_2021", "COMFORTABLE"), "")

    ctx = (
        f"Constituency: {constituency} ({culture}, {context['district']})\n"
        f"2021 Winner: {context['winner_2021']} | "
        f"Margin: {context.get('margin_2021','?')} — {margin_note}\n"
        f"Anti-incumbency: {context.get('anti_inc_score',0)} | "
        f"TVK zone: {context.get('tvk_zone','MEDIUM')} | "
        f"SC boost: {context.get('sc_boost',0)}\n"
        f"Candidate sentiment SPA/AIADMK/TVK/Others: "
        f"{context['sent_spa']:.0f}/{context['sent_aiadmk']:.0f}/"
        f"{context['sent_tvk']:.0f}/{context['sent_others']:.0f}"
    )

    voters_block = ""
    for i, p in enumerate(batch, 1):
        voters_block += (
            f"VOTER_{i}: {p['age']} {p['gender']}, {p['occupation']}, "
            f"{p['literacy']}, media={p['media']}, concern={p['concern']}\n"
        )

    n = len(batch)
    json_template = (
        "[\n"
        + ",\n".join(
            f'  {{"voter": {i}, "SPA": N, "AIADMK": N, "TVK": N, "Others": N, "Reason": "one sentence for voter {i}"}}'  # noqa
            for i in range(1, n + 1)
        )
        + "\n]"
    )

    return f"""Political context (2026 Tamil Nadu election):
{ELECTION_CONTEXT.strip()}

Constituency data:
{ctx}

Voters to analyse (treat each voter INDEPENDENTLY):
{voters_block}
Rules:
- SPA + AIADMK + TVK + Others = EXACTLY 100 for every voter.
- Each Reason must reference only that voter's own occupation/age/concern.
- Do NOT let one voter influence another.

Respond ONLY with a JSON array of exactly {n} objects (no markdown):
{json_template}"""


def _ask_llm_batch(batch: list[dict], constituency: str,
                   culture: str, context: dict) -> list[dict]:
    """
    One LLM call for a batch of personas.
    Falls back to heuristic per-persona if the call fails.
    """
    client = get_llm_client("GEMINI")
    prompt = _build_batch_prompt(batch, constituency, culture, context)
    raw    = client.call_batch(prompt, expected_count=len(batch))

    if raw is None:
        print(f"    [FALLBACK] Batch of {len(batch)} failed → heuristic for all")
        return [fallback_vote(p, context) for p in batch]

    results = []
    for i, item in enumerate(raw):
        try:
            vote   = _normalise_vote(item)
            reason = str(item.get("Reason", "")).strip()
            vote["Reason"] = _valid_reason(reason, vote, batch[i], context)
            vote["Source"] = "LLM_BATCH"
        except Exception:
            vote = fallback_vote(batch[i], context)
        results.append(vote)
    return results


# ══════════════════════════════════════════════════════════════════════════════
# 3-ROUND MULTI-AGENT DEBATE ENGINE
# ══════════════════════════════════════════════════════════════════════════════

DEBATE_AGENTS = [
    {
        "name": "Welfare & Governance Analyst",
        "system": (
            "You are a political analyst who focuses exclusively on welfare delivery, "
            "women empowerment, and the SPA incumbent government's track record in Tamil Nadu. "
            "You believe Magalir Urimai Thogai (Rs.1000/month), free bus travel, Puthumai Penn, "
            "and free school breakfast have created a durable vote bloc among women, students, "
            "and low-income families. Frame all analysis through this welfare lens."
        ),
        "bias": {"SPA": +8, "AIADMK": -4, "TVK": -2, "Others": -2},
    },
    {
        "name": "Anti-Incumbency & Economy Analyst",
        "system": (
            "You are a sharp political critic focused on economic grievances: rising electricity "
            "tariffs, inflation, unemployment, drug menace, law-and-order failures, and "
            "middle-class anger. You believe economic pain and anti-incumbency sentiment strongly "
            "benefit the AIADMK+ opposition. Frame all analysis through economic pain and "
            "opposition consolidation."
        ),
        "bias": {"SPA": -6, "AIADMK": +8, "TVK": 0, "Others": -2},
    },
    {
        "name": "Youth & Disruption Analyst",
        "system": (
            "You are a progressive analyst tracking Tamil Nadu's new political dynamics: "
            "TVK's Vijay factor among youth and first-time voters, the role of social media "
            "in bypassing traditional media, and voters disillusioned with both Dravidian majors. "
            "You believe TVK, NTK, and PMK can outperform traditional polling among youth and "
            "specific OBC/community blocs. Frame all analysis through youth mobilisation and disruption."
        ),
        "bias": {"SPA": -3, "AIADMK": -5, "TVK": +8, "Others": 0},
    },
]


def _raw_llm_call(prompt: str, timeout: int = 90) -> dict | None:
    """Single raw LLM call. Returns parsed JSON dict or None on failure."""
    client = get_llm_client("GEMINI" if GOOGLE_IS_AVAILABLE else "OLLAMA")
    return client.call(prompt)


def _safe_int(v) -> int:
    """Robustly convert any LLM output value to int.
    Handles: None → 0, '41' (string) → 41, 41.0 (float) → 41, int → int."""
    try:
        return int(float(v or 0))
    except (TypeError, ValueError):
        return 0


def _normalise_vote(data: dict) -> dict:
    """Normalise SPA/AIADMK/TVK/Others so they sum to 100.
    Clamps negatives to 0 and coerces None/string/float via _safe_int."""
    spa    = max(0, _safe_int(data.get("SPA")))
    admk   = max(0, _safe_int(data.get("AIADMK")))
    tvk    = max(0, _safe_int(data.get("TVK")))
    others = max(0, _safe_int(data.get("Others")))
    
    # If LLM completely forgot 'Others', check if there was sentiment for it
    # This prevents accidental 0% if the LLM is lazy.
    if "Others" not in data and others == 0:
        others = 1 # give a small floor if omitted
        
    total  = spa + admk + tvk + others
    if total <= 0:
        return {"SPA": 25, "AIADMK": 25, "TVK": 25, "Others": 25}
    f = 100.0 / total
    return {
        "SPA":    round(spa    * f),
        "AIADMK": round(admk   * f),
        "TVK":    round(tvk    * f),
        "Others": round(others * f),
    }


def _debate_fallback(agent: dict, persona: dict, context: dict) -> dict:
    """Lens-biased fallback vote for a debate agent when Ollama is offline."""
    base = fallback_vote(persona, context)   # heuristic base
    bias = agent["bias"]
    biased = {
        k: max(1, base.get(k, 25) + bias.get(k, 0))
        for k in ["SPA", "AIADMK", "TVK", "Others"]
    }
    vote = _normalise_vote(biased)
    vote["Reason"] = synthesize_reason(vote, persona, context)
    return vote


def _build_r1_prompt(agent: dict, persona: dict, constituency: str,
                     culture: str, context: dict) -> str:
    """Round 1: agent votes independently on the persona."""
    return f"""System: {agent['system']}

CONSTITUENCY: {constituency} ({culture} belt, {context['district']} district)
2021 Winner: {context['winner_2021']} | Turnout surge: +{context.get('turnout_delta',0):.1f}%
Sentiment scores: SPA={context['sent_spa']:.0f}, AIADMK={context['sent_aiadmk']:.0f}, TVK={context['sent_tvk']:.0f}

VOTER: {persona.get('age','')} {persona.get('gender','')}, {persona.get('occupation','')}
Education: {persona.get('literacy','')} | Concern: {persona.get('concern','')} | Media: {persona.get('media','')}

From YOUR analytical lens, predict how this voter splits their vote.
Respond ONLY with this exact JSON (no other text):
{{"SPA": N, "AIADMK": N, "TVK": N, "Others": N, "Reason": "One sentence."}}
CRITICAL: Each number must be 0-100 (NO negatives). All four must sum to exactly 100.
"""


def _build_r2_prompt(agent: dict, persona: dict, constituency: str,
                     culture: str, context: dict,
                     my_r1: dict, others_r1: list) -> str:
    """Round 2: agent sees the other two analysts' Round 1 positions and may revise."""
    others_block = "\n".join(
        f"  [{o['agent']}]: SPA={o['SPA']}% AIADMK={o['AIADMK']}% TVK={o['TVK']}% Others={o['Others']}%"
        f" — {o.get('Reason','')}"
        for o in others_r1
    )
    return f"""System: {agent['system']}

CONSTITUENCY: {constituency} | VOTER: {persona.get('age','')} {persona.get('gender','')}, {persona.get('occupation','')}
Concern: {persona.get('concern','')} | Media: {persona.get('media','')}

YOUR ROUND 1 VOTE: SPA={my_r1['SPA']}% AIADMK={my_r1['AIADMK']}% TVK={my_r1['TVK']}% Others={my_r1['Others']}%
Your Reason: {my_r1.get('Reason','')}

OTHER ANALYSTS:
{others_block}

Revise or confirm your vote. Respond ONLY with this JSON (no other text):
{{"SPA": N, "AIADMK": N, "TVK": N, "Others": N, "Reason": "One sentence."}}
CRITICAL: Each number must be 0-100 (NO negatives). All four must sum to exactly 100.
"""


def _build_moderator_prompt(persona: dict, constituency: str,
                            culture: str, context: dict,
                            round2: list) -> str:
    """Round 3: neutral moderator synthesizes the three Round 2 positions."""
    positions_block = "\n".join(
        f"  [{r['agent']}]: SPA={r['SPA']}% AIADMK={r['AIADMK']}% TVK={r['TVK']}% Others={r['Others']}%"
        f" — {r.get('Reason','')}"
        for r in round2
    )
    return f"""System: You are a neutral election moderator. Synthesize three analysts' positions into one realistic vote.

VOTER: {persona.get('age','')} {persona.get('gender','')}, {persona.get('occupation','')} in {constituency}
Concern: {persona.get('concern','')} | Media: {persona.get('media','')}

ANALYST POSITIONS:
{positions_block}

Choose the most credible vote for this voter based on their profile — do NOT simply average.
Respond ONLY with this JSON (no other text):
{{"SPA": N, "AIADMK": N, "TVK": N, "Others": N, "Reason": "One sentence synthesis."}}
CRITICAL: Each number must be 0-100 (NO negatives). All four must sum to exactly 100.
"""


# Maps winning party key → keywords that should appear in an honest reason
_PARTY_KEYWORDS = {
    "SPA":    ["spa", "dmk", "welfare", "magalir", "incumbent"],
    "AIADMK": ["aiadmk", "opposition", "inflation", "economy", "anti-incumbency", "edappadi"],
    "TVK":    ["tvk", "vijay", "youth", "disruptor", "new party"],
    "Others": ["ntk", "pmk", "others", "caste", "community", "farmer"],
}


def _valid_reason(reason: str, vote: dict, persona: dict, context: dict) -> str:
    """Return reason if it's meaningful and roughly matches the top party;
    otherwise fall back to synthesize_reason."""
    if len(reason) < 10:
        return synthesize_reason(vote, persona, context)
    # Find winning party
    top = max(["SPA", "AIADMK", "TVK", "Others"], key=lambda p: vote.get(p, 0))
    keywords = _PARTY_KEYWORDS.get(top, [])
    reason_lower = reason.lower()
    # If reason mentions no relevant keyword for the winner, it contradicts the vote
    if keywords and not any(kw in reason_lower for kw in keywords):
        return synthesize_reason(vote, persona, context)
    return reason


def _run_r1_agent(agent, persona, constituency, culture, context):
    """Single R1 call — designed to run in a thread pool."""
    prompt = _build_r1_prompt(agent, persona, constituency, culture, context)
    raw    = _raw_llm_call(prompt)
    if raw and (_safe_int(raw.get("SPA")) + _safe_int(raw.get("AIADMK")) +
                _safe_int(raw.get("TVK")) + _safe_int(raw.get("Others"))) > 0:
        vote   = _normalise_vote(raw)
        reason = raw.get("Reason", "").strip()
        vote["Reason"] = _valid_reason(reason, vote, persona, context)
    else:
        vote = _debate_fallback(agent, persona, context)
    vote["agent"] = agent["name"]
    return vote


def _run_r2_agent(agent, persona, constituency, culture, context, my_r1, others_r1):
    """Single R2 call — designed to run in a thread pool."""
    prompt = _build_r2_prompt(agent, persona, constituency, culture, context, my_r1, others_r1)
    raw    = _raw_llm_call(prompt)
    if raw and (_safe_int(raw.get("SPA")) + _safe_int(raw.get("AIADMK")) +
                _safe_int(raw.get("TVK")) + _safe_int(raw.get("Others"))) > 0:
        vote   = _normalise_vote(raw)
        reason = raw.get("Reason", "").strip()
        vote["Reason"] = _valid_reason(reason, vote, persona, context)
    else:
        vote = my_r1   # keep Round 1 if revision fails
    vote["agent"] = agent["name"]
    return vote


def debate_vote(persona: dict, constituency: str, culture: str, context: dict) -> dict:
    """
    3-Round Multi-Agent Debate:
      Round 1 — 3 specialist analysts vote in PARALLEL
      Round 2 — each analyst revises in PARALLEL after seeing the others' R1 positions
      Round 3 — neutral Moderator synthesizes (sequential — needs all R2 results)
    Falls back to lens-biased heuristics if Ollama is offline.
    """
    log_lines = []
    log_lines.append(f"    [{constituency[:10]}] [DEBATE] {persona.get('occupation','?')} | {persona.get('age','')} {persona.get('gender','')}")

    # ── Round 1: Parallel independent votes ───────────────────────────────────
    round1_map = {}   # agent_name -> vote
    with ThreadPoolExecutor(max_workers=DEBATE_PARALLEL_WORKERS) as pool:
        future_to_agent = {
            pool.submit(_run_r1_agent, agent, persona, constituency, culture, context): agent
            for agent in DEBATE_AGENTS
        }
        for future in as_completed(future_to_agent):
            vote = future.result()
            round1_map[vote["agent"]] = vote

    # Preserve original agent order for round2 indexing
    round1 = [round1_map[a["name"]] for a in DEBATE_AGENTS]
    for vote in round1:
        log_lines.append(f"      R1 [{vote['agent'][:25]}]: SPA={vote['SPA']}% AIADMK={vote['AIADMK']}%"
                         f" TVK={vote['TVK']}% Others={vote['Others']}%")
        log_lines.append(f"         → {vote['Reason']}")

    # ── Round 2: Parallel revisions ────────────────────────────────────────────
    log_lines.append(f"    [{constituency[:10]}] Round 2 — Parallel revisions...")
    round2_map = {}
    with ThreadPoolExecutor(max_workers=DEBATE_PARALLEL_WORKERS) as pool:
        future_to_agent = {
            pool.submit(
                _run_r2_agent, agent, persona, constituency, culture, context,
                round1[i],
                [r for j, r in enumerate(round1) if j != i]
            ): agent
            for i, agent in enumerate(DEBATE_AGENTS)
        }
        for future in as_completed(future_to_agent):
            vote = future.result()
            round2_map[vote["agent"]] = vote

    round2 = [round2_map[a["name"]] for a in DEBATE_AGENTS]
    for vote in round2:
        log_lines.append(f"      R2 [{vote['agent'][:25]}]: SPA={vote['SPA']}% AIADMK={vote['AIADMK']}%"
                         f" TVK={vote['TVK']}% Others={vote['Others']}%")
        log_lines.append(f"         → {vote['Reason']}")

    # ── Round 3: Moderator synthesizes (sequential) ────────────────────────────
    log_lines.append(f"    [{constituency[:10]}] Round 3 — Moderator synthesis...")
    prompt  = _build_moderator_prompt(persona, constituency, culture, context, round2)
    raw     = _raw_llm_call(prompt)
    if raw and (_safe_int(raw.get("SPA")) + _safe_int(raw.get("AIADMK")) +
                _safe_int(raw.get("TVK")) + _safe_int(raw.get("Others"))) > 0:
        final  = _normalise_vote(raw)
        reason = raw.get("Reason", "").strip()
        final["Reason"] = _valid_reason(reason, final, persona, context)
        final["Source"] = "DEBATE"
    else:
        avg   = {k: sum(r[k] for r in round2) / len(round2) for k in ["SPA", "AIADMK", "TVK", "Others"]}
        final = _normalise_vote(avg)
        final["Reason"] = synthesize_reason(final, persona, context)
        final["Source"] = "DEBATE_AVG"

    final["_round1"] = round1
    final["_round2"] = round2
    final["_log_lines"] = log_lines
    return final


# ── Global lock for thread-safe CSV writes ────────────────────────────────────
_csv_lock = threading.Lock()
_print_lock = threading.Lock()

def _simulate_constituency(idx, total_seats, row, df_sent):
    """Worker function to simulate a single constituency."""
    constituency = row["Constituency"]
    culture      = row["Culture"] if pd.notna(row["Culture"]) else "Mixed"
    polled       = int(row["Seat_Polled"]) if "Seat_Polled" in row else int(
                     row["Registered_Voters"] / row["Assembly_Seats"] * row["Turnout_2026"] / 100)
    district     = str(row.get("District_x", row.get("District", "")))

    print(f"\n[{idx+1}/{total_seats}] Starting {constituency} ({polled:,} voters)...")

    # Real Census stats for this district
    literacy  = float(row.get("Literacy_Pct", 74))
    urban_p   = float(row.get("Urban_Pct", 48))
    agri_lab  = float(row.get("AgriLabour_Pct", 29))
    gdp       = float(row.get("GDP_Lakhs", 0))
    census_occ = CENSUS_2011_OCCUPATION.get(district)

    # Get sentiment
    if not df_sent.empty and "Constituency" in df_sent.columns:
        seat_sent = df_sent[df_sent["Constituency"] == constituency]
    else:
        seat_sent = pd.DataFrame()
    if not seat_sent.empty:
        s_spa    = float(seat_sent.iloc[0]["Candidate_Sentiment_SPA"])
        s_aiadmk = float(seat_sent.iloc[0]["Candidate_Sentiment_AIADMK"])
        s_tvk    = float(seat_sent.iloc[0]["Candidate_Sentiment_TVK"])
        s_others = float(seat_sent.iloc[0]["Candidate_Sentiment_Others"])
    else:
        s_spa = s_aiadmk = s_tvk = s_others = 0.0
        
    winner = get_winner_2021(constituency)
    
    context = {
        "district":          district,
        "gdp":               gdp,
        "literacy":          literacy,
        "urban_pct":         urban_p,
        "agri_pct":          agri_lab,
        "winner_2021":       winner,
        "sent_spa":          s_spa,
        "sent_aiadmk":       s_aiadmk,
        "sent_tvk":          s_tvk,
        "sent_others":       s_others,
        # Prediction factors from enrich_prediction_factors.py
        "seat_type":             str(row.get("Seat_Type", "COMPETITIVE")),
        "tvk_zone":              str(row.get("TVK_Zone", "MEDIUM")),
        "incumbency_factor":     str(row.get("Incumbency_Factor", "COMPETITIVE")),
        "sc_boost":              int(row.get("SC_Boost", 0)),
        "anti_inc_score":        float(row.get("Anti_Incumbency_Score", 0)),
        "surge_type":            str(row.get("Turnout_Surge_Type", "ANTI_INCUMBENCY")),
        "turnout_delta":         float(row.get("Turnout_Delta", 0)),
        "voter_profile":         str(row.get("Voter_Profile_Extended", row.get("Voter_Profile", ""))),
        # New: margins, SC/ST population, re-contesting
        "sc_st_pct":             float(row.get("SC_ST_Pop_Pct", 16.0)),
        "margin_2021":           str(row.get("Margin_2021_Category", "COMFORTABLE")),
        "incumbent_recontesting":str(row.get("Incumbent_Recontesting", "UNKNOWN")),
    }

    # Generate 50 unique personas for this constituency
    buckets = generate_personas(
        constituency=constituency,
        culture=culture,
        district=district,
        num_personas=NUM_PERSONAS,
        census_occ=census_occ,
        literacy_pct=literacy,
        urban_pct=urban_p
    )

    spa_votes = admk_votes = tvk_votes = others_votes = 0
    persona_logs = []

    # ── Batch all personas → ceil(50/7) = 8 API calls ──────────────────────────
    all_batches     = _batch_personas(buckets, BATCH_SIZE)
    ordered_buckets = [p for batch in all_batches for p in batch]  # interleaved order
    all_vote_splits = []

    for b_idx, batch in enumerate(all_batches):
        with _print_lock:
            print(f"    [{constituency[:12]}] Batch {b_idx+1}/{len(all_batches)} "
                  f"({len(batch)} personas) …")
        if GOOGLE_IS_AVAILABLE:
            results = _ask_llm_batch(batch, constituency, culture, context)
        else:
            results = [fallback_vote(p, context) for p in batch]
        all_vote_splits.extend(results)

    # ── Accumulate votes & build persona logs ────────────────────────────────
    for bucket, vote_split in zip(ordered_buckets, all_vote_splits):
        bucket_size = int(polled * bucket["pct"])
        src         = vote_split.get("Source", "fallback")

        with _print_lock:
            print(
                f"    [{constituency[:10]}] [{src}] "
                f"{bucket.get('occupation','?')[:30]} | "
                f"{bucket.get('age','')} {bucket.get('gender','')} "
                f"({bucket_size:,} voters) | "
                f"SPA={vote_split['SPA']}% AIADMK={vote_split['AIADMK']}% "
                f"TVK={vote_split['TVK']}% Others={vote_split['Others']}%"
            )

        b_spa    = int(bucket_size * vote_split["SPA"]    / 100)
        b_admk   = int(bucket_size * vote_split["AIADMK"] / 100)
        b_tvk    = int(bucket_size * vote_split["TVK"]    / 100)
        b_others = int(bucket_size * vote_split["Others"] / 100)

        spa_votes    += b_spa
        admk_votes   += b_admk
        tvk_votes    += b_tvk
        others_votes += b_others

        persona_logs.append({
            "Constituency":  constituency,
            "Culture":       culture,
            "Persona":       bucket.get("label", ""),
            "Occupation":    bucket.get("occupation", ""),
            "Age":           bucket.get("age", ""),
            "Gender":        bucket.get("gender", ""),
            "Literacy":      bucket.get("literacy", ""),
            "Media":         bucket.get("media", ""),
            "Concern":       bucket.get("concern", ""),
            "Bucket_Voters": bucket_size,
            "Decision_Mode": src,
            "SPA_Pct":       vote_split["SPA"],
            "AIADMK_Pct":    vote_split["AIADMK"],
            "TVK_Pct":       vote_split["TVK"],
            "Others_Pct":    vote_split["Others"],
            "SPA_Votes":     b_spa,
            "AIADMK_Votes":  b_admk,
            "TVK_Votes":     b_tvk,
            "Others_Votes":  b_others,
            "Reason":        vote_split.get("Reason", ""),
            "Raw_Response":  "",
            # Debate columns — empty in batch mode
            "R1_Welfare_SPA": "", "R1_Welfare_ADMK": "",
            "R1_Welfare_TVK": "", "R1_Welfare_Reason": "",
            "R1_Economy_SPA": "", "R1_Economy_ADMK": "",
            "R1_Economy_TVK": "", "R1_Economy_Reason": "",
            "R1_Youth_SPA":   "", "R1_Youth_ADMK": "",
            "R1_Youth_TVK":   "", "R1_Youth_Reason": "",
            "R2_Welfare_SPA": "", "R2_Welfare_ADMK": "",
            "R2_Welfare_TVK": "", "R2_Welfare_Reason": "",
            "R2_Economy_SPA": "", "R2_Economy_ADMK": "",
            "R2_Economy_TVK": "", "R2_Economy_Reason": "",
            "R2_Youth_SPA":   "", "R2_Youth_ADMK": "",
            "R2_Youth_TVK":   "", "R2_Youth_Reason": "",
        })

    total_cast = spa_votes + admk_votes + tvk_votes + others_votes
    if total_cast == 0:
        total_cast = 1  # guard

    winner_votes = max(spa_votes, admk_votes, tvk_votes, others_votes)
    winner = ["SPA", "AIADMK+", "TVK", "Others"][[spa_votes, admk_votes, tvk_votes, others_votes].index(winner_votes)]
    second  = sorted([spa_votes, admk_votes, tvk_votes, others_votes], reverse=True)[1]
    margin  = winner_votes - second

    seat_result = {
        "Constituency":      constituency,
        "District":          row.get("District_x", row.get("District", "")),
        "Culture":           culture,
        "Seat_Polled":       total_cast,
        "SPA_Votes":         spa_votes,
        "AIADMK_Votes":      admk_votes,
        "TVK_Votes":         tvk_votes,
        "Others_Votes":      others_votes,
        "SPA_Pct":           round(spa_votes    / total_cast * 100, 2),
        "AIADMK_Pct":        round(admk_votes   / total_cast * 100, 2),
        "TVK_Pct":           round(tvk_votes    / total_cast * 100, 2),
        "Others_Pct":        round(others_votes / total_cast * 100, 2),
        "Winner":            winner,
        "Winning_Votes":     winner_votes,
        "Margin_Votes":      margin,
        "Margin_Pct":        round(margin / total_cast * 100, 2),
    }
    
    print(f"[{idx+1}/{total_seats}] {constituency:30s} => {winner} wins by {margin:,} votes")
    
    return seat_result, persona_logs


def run_simulation(limit=None):
    global OLLAMA_IS_RUNNING, _stop_requested

    # ── Register Ctrl+C handler ─────────────────────────────────
    signal.signal(signal.SIGINT, _handle_signal)

    # ── Load Constituency Data ──────────────────────────────────
    enriched_path = "data/assembly_metadata_enriched.csv"
    base_path = "data/assembly_metadata.csv"
    if os.path.exists(enriched_path):
        df = pd.read_csv(enriched_path)
        print("[OK] Loaded assembly_metadata_enriched.csv (Census 2011 + ECI 2026 real data)")
    else:
        df = pd.read_csv(base_path)
        print("[WARN] assembly_metadata_enriched.csv not found, using base metadata.")
        print("  Run: python data_enrichment_pipeline.py  to generate enriched data.")

    if "Constituency_Registered_Voters" in df.columns:
        df["Seat_Registered"] = df["Constituency_Registered_Voters"].astype(int)
        print("[OK] Using real per-constituency 2026 SIR registered voter counts.")
    else:
        df["Seat_Registered"] = (df["Registered_Voters"] / df["Assembly_Seats"]).astype(int)
        print("[WARN] Constituency_Registered_Voters not found -- using district average (less accurate).")
    df["Seat_Polled"] = (df["Seat_Registered"] * df["Turnout_2026"] / 100).astype(int)

    # ── Check Google Gemini ───────────────────────────────────────
    global GOOGLE_IS_AVAILABLE
    try:
        google_client = get_llm_client("GEMINI")
        if google_client.ping():
            GOOGLE_IS_AVAILABLE = True
            print(f"[OK] Google Gemini API: SUCCESS — "
                  f"batch_size={BATCH_SIZE} workers={CONSTITUENCY_WORKERS}")
        else:
            GOOGLE_IS_AVAILABLE = False
            print("[WARN] Google Gemini ping failed — using heuristic fallback")
    except Exception as e:
        GOOGLE_IS_AVAILABLE = False
        print(f"[WARN] Google Gemini unavailable ({e}) — using heuristic fallback")
    # Also probe Ollama (kept as secondary fallback)
    try:
        requests.get("http://localhost:11434/", timeout=3)
        OLLAMA_IS_RUNNING = True
        print("[INFO] Ollama also online (secondary fallback available)")
    except:
        OLLAMA_IS_RUNNING = False

    # ── Load sentiment data ──────────────────────────────────────
    if os.path.exists("data/assembly_candidate_sentiment.csv"):
        df_sent = pd.read_csv("data/assembly_candidate_sentiment.csv")
    else:
        df_sent = pd.DataFrame()

    total_seats = len(df)

    # ── Checkpoint: find already-completed constituencies ────────
    completed = _load_checkpoint()
    if completed:
        print(f"[RESUME] Checkpoint found: {len(completed)}/{total_seats} constituencies already done. Skipping them.")
    else:
        # Fresh run — initialize with correct high-fidelity headers
        headers = [
            "Constituency", "District", "Culture", "Seat_Polled", 
            "SPA_Votes", "AIADMK_Votes", "TVK_Votes", "Others_Votes", 
            "SPA_Pct", "AIADMK_Pct", "TVK_Pct", "Others_Pct", 
            "Winner", "Winning_Votes", "Margin_Votes", "Margin_Pct"
        ]
        pd.DataFrame(columns=headers).to_csv("data/simulation_results.csv", index=False)
        pd.DataFrame([]).to_csv("data/voter_agent_logs.csv",   index=False)
        print("[FRESH] Starting new simulation run with correct headers.")

    # Filter out already-completed constituencies
    pending_df = df[~df["Constituency"].isin(completed)].reset_index(drop=True)
    if limit:
        pending_df = pending_df.head(limit)
    print(f"\nStarting parallel simulation: {CONSTITUENCY_WORKERS} workers | {len(pending_df)} constituencies remaining...")

    # ── Run parallel simulation ──────────────────────────────────
    final_seat_results = []
    completed_lock = threading.Lock()

    with ThreadPoolExecutor(max_workers=CONSTITUENCY_WORKERS) as pool:
        futures = {
            pool.submit(_simulate_constituency, int(completed.__len__()) + i, total_seats, row, df_sent): row["Constituency"]
            for i, row in pending_df.iterrows()
        }

        for future in as_completed(futures):
            if _stop_requested:
                # Cancel remaining futures gracefully
                for f in futures:
                    f.cancel()
                break

            try:
                seat_result, persona_logs = future.result()
            except Exception as e:
                print(f"[ERROR] Constituency failed: {e}")
                continue

            final_seat_results.append(seat_result)
            constituency_name = seat_result["Constituency"]

            # Thread-safe CSV write + checkpoint update
            with _csv_lock:
                seat_df = pd.DataFrame([seat_result])
                seat_df.to_csv(
                    "data/simulation_results.csv", mode='a',
                    header=not os.path.exists("data/simulation_results.csv") or os.path.getsize("data/simulation_results.csv") == 0,
                    index=False
                )

                plogs_df = pd.DataFrame(persona_logs)
                plogs_df.to_csv(
                    "data/voter_agent_logs.csv", mode='a',
                    header=not os.path.exists("data/voter_agent_logs.csv") or os.path.getsize("data/voter_agent_logs.csv") == 0,
                    index=False
                )

            with completed_lock:
                completed.add(constituency_name)
                _save_checkpoint(completed)

    done = len(completed)
    remaining = total_seats - done
    print(f"\n{'='*60}")
    if _stop_requested and remaining > 0:
        print(f"[PAUSED] Simulation stopped after {done}/{total_seats} constituencies.")
        print(f"  Re-run the script to resume from where it stopped (checkpoint saved).")
    else:
        # All done — remove checkpoint so next run starts fresh
        if os.path.exists(CHECKPOINT_FILE):
            os.remove(CHECKPOINT_FILE)
        print(f"SIMULATION COMPLETE -- {total_seats} constituencies, "
              f"{sum(r['Seat_Polled'] for r in final_seat_results):,} total votes simulated")
        results_df = pd.DataFrame(final_seat_results)
        print(results_df["Winner"].value_counts().to_string())

# ══════════════════════════════════════════════════════════════════════════════
# ASYNC ENGINE — aiohttp fast path (replaces blocking requests + ThreadPool)
# ══════════════════════════════════════════════════════════════════════════════

async def _raw_llm_call_async(client, prompt: str):
    """Async single LLM call. Returns parsed dict or None."""
    if not OLLAMA_IS_RUNNING:
        return None
    result = await client.call_async(prompt)
    if result:
        with _print_lock:
            print(f"       [LLM] SPA={result.get('SPA','?')} AIADMK={result.get('AIADMK','?')} TVK={result.get('TVK','?')} Others={result.get('Others','?')} | {str(result.get('Reason',''))[:80]}")
    return result


async def _run_r1_agent_async(client, agent, persona, constituency, culture, context):
    prompt = _build_r1_prompt(agent, persona, constituency, culture, context)
    raw = await _raw_llm_call_async(client, prompt)
    if raw and (_safe_int(raw.get("SPA")) + _safe_int(raw.get("AIADMK")) +
                _safe_int(raw.get("TVK")) + _safe_int(raw.get("Others"))) > 0:
        vote = _normalise_vote(raw)
        vote["Reason"] = _valid_reason(raw.get("Reason", "").strip(), vote, persona, context)
    else:
        vote = _debate_fallback(agent, persona, context)
    vote["agent"] = agent["name"]
    return vote


async def _run_r2_agent_async(client, agent, persona, constituency, culture, context, my_r1, others_r1):
    prompt = _build_r2_prompt(agent, persona, constituency, culture, context, my_r1, others_r1)
    raw = await _raw_llm_call_async(client, prompt)
    if raw and (_safe_int(raw.get("SPA")) + _safe_int(raw.get("AIADMK")) +
                _safe_int(raw.get("TVK")) + _safe_int(raw.get("Others"))) > 0:
        vote = _normalise_vote(raw)
        vote["Reason"] = _valid_reason(raw.get("Reason", "").strip(), vote, persona, context)
    else:
        vote = my_r1
    vote["agent"] = agent["name"]
    return vote


async def debate_vote_async(client, persona, constituency, culture, context) -> dict:
    """
    Async 3-Round Debate. R1 and R2 use asyncio.gather() — all 3 agents
    fire simultaneously with zero thread overhead.
    """
    log_lines = []
    log_lines.append(f"    [{constituency[:10]}] [DEBATE] {persona.get('occupation','?')} | {persona.get('age','')} {persona.get('gender','')}")

    # Round 1 — 3 agents in TRUE parallel
    round1 = list(await asyncio.gather(*[
        _run_r1_agent_async(client, agent, persona, constituency, culture, context)
        for agent in DEBATE_AGENTS
    ]))
    _order = {a["name"]: i for i, a in enumerate(DEBATE_AGENTS)}
    round1.sort(key=lambda v: _order.get(v.get("agent", ""), 99))

    for v in round1:
        log_lines.append(f"      R1 [{v['agent'][:25]}]: SPA={v['SPA']}% AIADMK={v['AIADMK']}% TVK={v['TVK']}% Others={v['Others']}%")
        log_lines.append(f"         → {v['Reason']}")

    # Round 2 — 3 revisions in TRUE parallel
    log_lines.append(f"    [{constituency[:10]}] Round 2 — Parallel revisions...")
    round2 = list(await asyncio.gather(*[
        _run_r2_agent_async(
            client, agent, persona, constituency, culture, context,
            round1[i], [r for j, r in enumerate(round1) if j != i]
        )
        for i, agent in enumerate(DEBATE_AGENTS)
    ]))
    round2.sort(key=lambda v: _order.get(v.get("agent", ""), 99))

    for v in round2:
        log_lines.append(f"      R2 [{v['agent'][:25]}]: SPA={v['SPA']}% AIADMK={v['AIADMK']}% TVK={v['TVK']}% Others={v['Others']}%")
        log_lines.append(f"         → {v['Reason']}")

    # Round 3 — Moderator (sequential, needs all R2)
    log_lines.append(f"    [{constituency[:10]}] Round 3 — Moderator synthesis...")
    raw = await _raw_llm_call_async(client, _build_moderator_prompt(persona, constituency, culture, context, round2))
    if raw and (_safe_int(raw.get("SPA")) + _safe_int(raw.get("AIADMK")) +
                _safe_int(raw.get("TVK")) + _safe_int(raw.get("Others"))) > 0:
        final = _normalise_vote(raw)
        final["Reason"] = _valid_reason(raw.get("Reason", "").strip(), final, persona, context)
        final["Source"] = "DEBATE"
    else:
        avg = {k: sum(r[k] for r in round2) / len(round2) for k in ["SPA", "AIADMK", "TVK", "Others"]}
        final = _normalise_vote(avg)
        final["Reason"] = synthesize_reason(final, persona, context)
        final["Source"] = "DEBATE_AVG"

    final["_round1"] = round1
    final["_round2"] = round2
    final["_log_lines"] = log_lines
    return final


# ══════════════════════════════════════════════════════════════════════════════
# BATCHED DEBATE ENGINE
# Each API call handles BATCH_SIZE personas → 7 calls/constituency vs 350
# R1: agents vote INDEPENDENTLY (no cross-agent contamination)
# R2: each agent revises after seeing ALL other agents' R1 positions
# R3: neutral moderator synthesizes per-persona
# ══════════════════════════════════════════════════════════════════════════════

def _batch_voter_list(buckets):
    return "\n".join(
        f"VOTER_{i+1}: {b.get('age','')} {b.get('gender','')}, {b.get('occupation','')} | "
        f"Education: {b.get('literacy','')} | Concern: {b.get('concern','')} | Media: {b.get('media','')}"
        for i, b in enumerate(buckets)
    )

def _build_batch_r1_prompt(agent, buckets, constituency, culture, context):
    n = len(buckets)
    return f"""System: {agent['system']}

CONSTITUENCY: {constituency} ({culture} belt, {context['district']} district)
2021 Winner: {context['winner_2021']} | Turnout surge: +{context.get('turnout_delta',0):.1f}%
Sentiment (Scale -100 to +100): SPA={context['sent_spa']:.0f} AIADMK={context['sent_aiadmk']:.0f} TVK={context['sent_tvk']:.0f} Others={context['sent_others']:.0f}
(Note: Scores < 15 are MILD; avoid unrealistic landslides based on mild scores.)

VOTERS:
{_batch_voter_list(buckets)}

From YOUR analytical lens, predict each voter's vote split INDEPENDENTLY.
STRICT ANTI-BIAS RULE: Analyze each persona strictly based on their individual age, occupation, and concern. Do NOT assume consensus within the group. Ensure nuances between different demographic buckets are preserved.
Return ONLY a JSON array of exactly {n} objects (no markdown):
[{{"voter":1,"SPA":N,"AIADMK":N,"TVK":N,"Others":N,"Reason":"One sentence persona-specific reasoning."}}, ...]
CRITICAL: Numbers 0-100, sum to exactly 100 per voter."""

def _build_batch_r2_prompt(agent, buckets, constituency, culture, context, my_r1_votes, others_r1):
    n = len(buckets)
    voter_block = "\n".join(
        f"VOTER_{i+1}: {b.get('age','')} {b.get('gender','')}, {b.get('occupation','')} | Concern: {b.get('concern','')}\n"
        f"  YOUR R1: SPA={my_r1_votes[i].get('SPA',0)}% AIADMK={my_r1_votes[i].get('AIADMK',0)}% TVK={my_r1_votes[i].get('TVK',0)}% Others={my_r1_votes[i].get('Others',0)}%\n" +
        "\n".join(
            f"  [{o['agent']}]: SPA={o['votes'][i].get('SPA',0)}% AIADMK={o['votes'][i].get('AIADMK',0)}% TVK={o['votes'][i].get('TVK',0)}% Others={o['votes'][i].get('Others',0)}% — {o['votes'][i].get('Reason','')}"  
            for o in others_r1
        )
        for i, b in enumerate(buckets)
    )
    return f"""System: {agent['system']}

CONSTITUENCY: {constituency} — Revise or confirm your Round 1 votes after seeing other analysts' positions.

{voter_block}

ANTI-BIAS RULE: Do NOT simply follow the majority. Only revise if another analyst provides a compelling, data-driven reason relevant to the specific voter's persona. Protect individual voter nuances.
Return ONLY a JSON array of exactly {n} objects:
[{{"voter":1,"SPA":N,"AIADMK":N,"TVK":N,"Others":N,"Reason":"Nuanced revision or confirmation reason."}}, ...]
CRITICAL: Numbers 0-100, sum to exactly 100 per voter."""

def _build_batch_moderator_prompt(buckets, constituency, culture, context, r2_by_agent):
    n = len(buckets)
    voter_block = "\n".join(
        f"VOTER_{i+1}: {b.get('age','')} {b.get('gender','')}, {b.get('occupation','')} | Concern: {b.get('concern','')}\n" +
        "\n".join(
            f"  [{a['agent']}]: SPA={a['votes'][i].get('SPA',0)}% AIADMK={a['votes'][i].get('AIADMK',0)}% TVK={a['votes'][i].get('TVK',0)}% Others={a['votes'][i].get('Others',0)}% — {a['votes'][i].get('Reason','')}"
            for a in r2_by_agent
        )
        for i, b in enumerate(buckets)
    )
    return f"""System: You are a neutral election moderator. Synthesize three analysts' R2 positions for each voter — do NOT simply average.

CONSTITUENCY: {constituency}

{voter_block}

ANTI-BIAS RULE: Do NOT simply average the numbers. Protect minority viewpoints and outliers. If one analyst has a strong, persona-specific reason for a shift, weigh it heavily. Avoid "groupthink" outcomes.
Return ONLY a JSON array of exactly {n} objects:
[{{"voter":1,"SPA":N,"AIADMK":N,"TVK":N,"Others":N,"Reason":"Persona-specific synthesis preserving individual nuances."}}, ...]
CRITICAL: Numbers 0-100, sum to exactly 100 per voter."""


def _build_ultra_debate_prompt(batch, constituency, culture, context):
    """
    Synthesizes the entire 3-round multi-agent debate into a single, high-fidelity prompt.
    Requests Round 1 (3 agents), internal synthesis, and final Moderator result in one JSON response.
    """
    persona_list = "\n".join([f"- {p.get('age','')} {p.get('gender','')}, {p.get('occupation','')} (Concern: {p.get('concern','')})" for p in batch])
    
    prompt = f"""
{ELECTION_CONTEXT}

CONSTITUENCY: {constituency}
CULTURE: {culture}
METRICS & SCALING:
- Sentiment Scale: -100 to +100 (0=Neutral, 10=Mild, 30=Strong, 50+=Overwhelming).
- SPA Sentiment: {context.get('sent_spa',0)}
- AIADMK Sentiment: {context.get('sent_aiadmk',0)}
- TVK Sentiment: {context.get('sent_tvk',0)}
- Others Sentiment: {context.get('sent_others',0)}
(IMPORTANT: Sentiment scores < 15 are MILD and should NOT trigger landslides.)

TASK:
You must simulate a multi-agent debate for the following {len(batch)} voter personas:
{persona_list}

AGENTS INVOLVED:
1. Welfare Analyst: Focused on SPA benefits. Must strongly prioritize direct cash transfers (Magalir Urimai Thogai) as a non-negotiable floor for female/low-income personas.
2. Anti-Incumbency Critic: Focused on AIADMK/Inflation/Gaps.
3. Youth/Disruption Analyst: Focused on TVK/NTK social media surge.

PROCESS:
1. ROUND 1: Each agent provides their initial vote share for the 4 parties.
2. ROUND 2: Agents debate and revise their scores based on the other analysts' perspectives.
3. MODERATOR: A neutral moderator synthesizes the final vote split for each persona.

ANTI-BIAS RULE: If a persona is 'Highly educated' or 'Youth' in a 'TVK HIGH' zone, TVK must receive a significant share. If 'Female' and 'Low-income', SPA's welfare floor must be respected.
OTHERS GUARDRAIL: 'Others' (NTK/PMK) represent disruptive minority blocks. Unless the constituency is a specific stronghold for their leader (e.g. Thiruvotriyur for Seeman), they should rarely exceed 35% total share.

OUTPUT FORMAT:
Return a JSON object with a "results" key containing an array of {len(batch)} objects.
Each object MUST have:
{{
  "SPA": percentage,
  "AIADMK": percentage,
  "TVK": percentage,
  "Others": percentage,
  "Reason": "Brief synthesis of the debate rounds and final conclusion."
}}
JSON:
"""
    return prompt

async def debate_vote_batch_async(client, buckets, constituency, culture, context, csv_lock):
    """
    ULTRA-EFFICIENT MODE: 3-round debate synthesized in ONE single API call per batch.
    Ensures 234 seats fit within 1.5K daily request limit.
    """
    all_results = []
    for start in range(0, len(buckets), BATCH_SIZE):
        batch = buckets[start:start + BATCH_SIZE]
        n     = len(batch)

        # Build a "Deep Debate" prompt that asks for R1, R2, and Moderator synthesis in one shot
        prompt = _build_ultra_debate_prompt(batch, constituency, culture, context)
        raw    = await client.call_batch_async(prompt, expected_count=n)

        for idx, bucket in enumerate(batch):
            if raw and len(raw) == n:
                final = _normalise_vote(raw[idx])
                final["Reason"] = _valid_reason(raw[idx].get("Reason","").strip(), final, bucket, context)
                final["Source"] = "DEBATE_ULTRA"
            else:
                # Fallback to data-driven heuristic if LLM fails
                final = _debate_fallback(DEBATE_AGENTS[0], bucket, context)
                final["Source"] = "DEBATE_FALLBACK"
            
            # Record for voter_agent_logs.csv
            final["Constituency"] = constituency
            final["Culture"] = culture
            final["Voter_Profile"] = f"{bucket.get('age','')} {bucket.get('gender','')}, {bucket.get('occupation','')}"
            final["Occupation"] = bucket.get("occupation","")
            final["Age"] = bucket.get("age","")
            final["Gender"] = bucket.get("gender","")
            final["Education"] = bucket.get("literacy","")
            final["Media_Consumption"] = bucket.get("media","")
            final["Primary_Grievance"] = bucket.get("concern","")
            final["Voter_Weight"] = bucket.get("pct", 0) # Use pct as weight
            all_results.append(final)
            
            with _print_lock:
                print(f"       [{constituency[:10]}] VOTER_{start+idx+1}: SPA={final['SPA']}% AIADMK={final['AIADMK']}% TVK={final['TVK']}% Others={final['Others']}%")

    return all_results


async def ask_llm_async(client, persona, constituency, culture, context) -> dict:
    """Async single-agent LLM vote. Same logic as ask_llm(), async HTTP."""
    if not OLLAMA_IS_RUNNING:
        return fallback_vote(persona, context)
    raw = await client.call_async(build_prompt(persona, constituency, culture, context))
    if raw:
        total = (_safe_int(raw.get("SPA")) + _safe_int(raw.get("AIADMK")) +
                 _safe_int(raw.get("TVK")) + _safe_int(raw.get("Others")))
        if total > 0:
            f = 100.0 / total
            vs = {
                "SPA":          round(_safe_int(raw.get("SPA"))    * f),
                "AIADMK":       round(_safe_int(raw.get("AIADMK")) * f),
                "TVK":          round(_safe_int(raw.get("TVK"))    * f),
                "Others":       round(_safe_int(raw.get("Others")) * f),
                "Source":       "LLM",
                "Raw_Response": json.dumps(raw),
            }
            rr = raw.get("Reason", "").strip()
            vs["Reason"] = rr if len(rr) > 10 else synthesize_reason(vs, persona, context)
            return vs
    return fallback_vote(persona, context)


async def _simulate_constituency_async(client, semaphore, csv_lock, idx, total_seats, row, df_sent):
    """Async version of _simulate_constituency. All LLM calls are non-blocking."""
    async with semaphore:
        constituency = row["Constituency"]
        culture      = row["Culture"] if pd.notna(row["Culture"]) else "Mixed"
        polled       = int(row["Seat_Polled"]) if "Seat_Polled" in row else int(
                         row["Registered_Voters"] / row["Assembly_Seats"] * row["Turnout_2026"] / 100)
        district     = str(row.get("District_x", row.get("District", "")))

        with _print_lock:
            print(f"\n[{idx+1}/{total_seats}] Starting {constituency} ({polled:,} voters)...")

        literacy   = float(row.get("Literacy_Pct", 74))
        urban_p    = float(row.get("Urban_Pct", 48))
        agri_lab   = float(row.get("AgriLabour_Pct", 29))
        gdp        = float(row.get("GDP_Lakhs", 0))
        census_occ = CENSUS_2011_OCCUPATION.get(district)

        if not df_sent.empty and "Constituency" in df_sent.columns:
            seat_sent = df_sent[df_sent["Constituency"] == constituency]
        else:
            seat_sent = pd.DataFrame()

        if not seat_sent.empty:
            s_spa    = float(seat_sent.iloc[0]["Candidate_Sentiment_SPA"])
            s_aiadmk = float(seat_sent.iloc[0]["Candidate_Sentiment_AIADMK"])
            s_tvk    = float(seat_sent.iloc[0]["Candidate_Sentiment_TVK"])
            s_others = float(seat_sent.iloc[0]["Candidate_Sentiment_Others"])
        else:
            s_spa = s_aiadmk = s_tvk = s_others = 0.0

        winner = get_winner_2021(constituency)
        context = {
            "district": district, "gdp": gdp, "literacy": literacy,
            "urban_pct": urban_p, "agri_pct": agri_lab, "winner_2021": winner,
            "sent_spa": s_spa, "sent_aiadmk": s_aiadmk, "sent_tvk": s_tvk, "sent_others": s_others,
            "seat_type":              str(row.get("Seat_Type", "COMPETITIVE")),
            "tvk_zone":               str(row.get("TVK_Zone", "MEDIUM")),
            "incumbency_factor":      str(row.get("Incumbency_Factor", "COMPETITIVE")),
            "sc_boost":               int(row.get("SC_Boost", 0)),
            "anti_inc_score":         float(row.get("Anti_Incumbency_Score", 0)),
            "surge_type":             str(row.get("Turnout_Surge_Type", "ANTI_INCUMBENCY")),
            "turnout_delta":          float(row.get("Turnout_Delta", 0)),
            "voter_profile":          str(row.get("Voter_Profile_Extended", row.get("Voter_Profile", ""))),
            "sc_st_pct":              float(row.get("SC_ST_Pop_Pct", 16.0)),
            "margin_2021":            str(row.get("Margin_2021_Category", "COMFORTABLE")),
            "incumbent_recontesting": str(row.get("Incumbent_Recontesting", "UNKNOWN")),
        }

        # ── Star Candidate Boost ─────────────────────────────────────────────
        if constituency in STAR_SEATS:
            boosts = STAR_SEATS[constituency]
            if "SPA" in boosts:    context["sent_spa"]    += boosts["SPA"]
            if "AIADMK" in boosts: context["sent_aiadmk"] += boosts["AIADMK"]
            if "TVK" in boosts:    context["sent_tvk"]    += boosts["TVK"]
            if "Others" in boosts: context["sent_others"] += boosts["Others"]
            with _print_lock:
                print(f"    [STAR_SEAT] Applied personal loyalty boost for {constituency}")

        buckets = generate_personas(
            constituency=constituency, culture=culture, district=district,
            num_personas=NUM_PERSONAS, census_occ=census_occ,
            literacy_pct=literacy, urban_pct=urban_p
        )

        # ── Batched debate or single-call path ───────────────────────────────
        if USE_DEBATE_MODE and OLLAMA_IS_RUNNING:
            all_vote_splits = await debate_vote_batch_async(client, buckets, constituency, culture, context, csv_lock)
        else:
            all_vote_splits = list(await asyncio.gather(*[
                ask_llm_async(client, b, constituency, culture, context) for b in buckets
            ]))

        spa_votes = admk_votes = tvk_votes = others_votes = 0
        persona_logs = []
        for bucket, vote_split in zip(buckets, all_vote_splits):
            bucket_size = int(polled * bucket["pct"])
            b_spa    = int(bucket_size * vote_split["SPA"]    / 100)
            b_admk   = int(bucket_size * vote_split["AIADMK"] / 100)
            b_tvk    = int(bucket_size * vote_split["TVK"]    / 100)
            b_others = int(bucket_size * vote_split["Others"] / 100)
            spa_votes += b_spa; admk_votes += b_admk
            tvk_votes += b_tvk; others_votes += b_others

            r1 = vote_split.get("_round1", [{}, {}, {}])
            r2 = vote_split.get("_round2", [{}, {}, {}])
            persona_logs.append({
                "Constituency": constituency, "Culture": culture,
                "Persona": bucket.get("label", ""), "Occupation": bucket.get("occupation", ""),
                "Age": bucket.get("age", ""), "Gender": bucket.get("gender", ""),
                "Literacy": bucket.get("literacy", ""), "Media": bucket.get("media", ""),
                "Concern": bucket.get("concern", ""), "Bucket_Voters": bucket_size,
                "Decision_Mode": vote_split.get("Source", "fallback"),
                "SPA_Pct": vote_split["SPA"], "AIADMK_Pct": vote_split["AIADMK"],
                "TVK_Pct": vote_split["TVK"], "Others_Pct": vote_split["Others"],
                "SPA_Votes": b_spa, "AIADMK_Votes": b_admk,
                "TVK_Votes": b_tvk, "Others_Votes": b_others,
                "Reason": vote_split.get("Reason", ""),
                "Raw_Response": vote_split.get("Raw_Response", ""),
                "R1_Welfare_SPA":    r1[0].get("SPA",""),  "R1_Welfare_ADMK":   r1[0].get("AIADMK",""),
                "R1_Welfare_TVK":    r1[0].get("TVK",""),  "R1_Welfare_Others": r1[0].get("Others",""), "R1_Welfare_Reason": r1[0].get("Reason",""),
                "R1_Economy_SPA":    r1[1].get("SPA",""),  "R1_Economy_ADMK":   r1[1].get("AIADMK",""),
                "R1_Economy_TVK":    r1[1].get("TVK",""),  "R1_Economy_Others": r1[1].get("Others",""), "R1_Economy_Reason": r1[1].get("Reason",""),
                "R1_Youth_SPA":      r1[2].get("SPA",""),  "R1_Youth_ADMK":     r1[2].get("AIADMK",""),
                "R1_Youth_TVK":      r1[2].get("TVK",""),  "R1_Youth_Others":   r1[2].get("Others",""), "R1_Youth_Reason":   r1[2].get("Reason",""),
                "R2_Welfare_SPA":    r2[0].get("SPA",""),  "R2_Welfare_ADMK":   r2[0].get("AIADMK",""),
                "R2_Welfare_TVK":    r2[0].get("TVK",""),  "R2_Welfare_Others": r2[0].get("Others",""), "R2_Welfare_Reason": r2[0].get("Reason",""),
                "R2_Economy_SPA":    r2[1].get("SPA",""),  "R2_Economy_ADMK":   r2[1].get("AIADMK",""),
                "R2_Economy_TVK":    r2[1].get("TVK",""),  "R2_Economy_Others": r2[1].get("Others",""), "R2_Economy_Reason": r2[1].get("Reason",""),
                "R2_Youth_SPA":      r2[2].get("SPA",""),  "R2_Youth_ADMK":     r2[2].get("AIADMK",""),
                "R2_Youth_TVK":      r2[2].get("TVK",""),  "R2_Youth_Others":   r2[2].get("Others",""), "R2_Youth_Reason":   r2[2].get("Reason",""),
            })

        total_cast  = max(1, spa_votes + admk_votes + tvk_votes + others_votes)
        winner_v    = max(spa_votes, admk_votes, tvk_votes, others_votes)
        winner_name = ["SPA", "AIADMK+", "TVK", "Others"][
            [spa_votes, admk_votes, tvk_votes, others_votes].index(winner_v)]
        second      = sorted([spa_votes, admk_votes, tvk_votes, others_votes], reverse=True)[1]
        margin      = winner_v - second

        seat_result = {
            "Constituency": constituency,
            "District":     row.get("District_x", row.get("District", "")),
            "Culture":      culture,
            "Seat_Polled":  total_cast,
            "SPA_Votes":    spa_votes,   "AIADMK_Votes": admk_votes,
            "TVK_Votes":    tvk_votes,   "Others_Votes": others_votes,
            "SPA_Pct":      round(spa_votes   / total_cast * 100, 2),
            "AIADMK_Pct":   round(admk_votes  / total_cast * 100, 2),
            "TVK_Pct":      round(tvk_votes   / total_cast * 100, 2),
            "Others_Pct":   round(others_votes/ total_cast * 100, 2),
            "Winner":       winner_name,
            "Winning_Votes": winner_v,
            "Margin_Votes": margin,
            "Margin_Pct":   round(margin / total_cast * 100, 2),
        }

        with _print_lock:
            print(f"[{idx+1}/{total_seats}] {constituency:30s} => {winner_name} wins by {margin:,} votes")

        return seat_result, persona_logs


async def run_simulation_async(limit=None):
    """
    Async entry point for the full simulation.
    Uses OllamaAsyncClient (aiohttp) + asyncio.Semaphore for constituency parallelism.
    Identical outputs to run_simulation() — faster due to non-blocking I/O.
    """
    global OLLAMA_IS_RUNNING, _stop_requested

    signal.signal(signal.SIGINT, _handle_signal)

    # Load data
    enriched_path = "assembly_metadata_enriched.csv"
    base_path     = "assembly_metadata.csv"
    if os.path.exists(enriched_path):
        df = pd.read_csv(enriched_path)
        print("[OK] Loaded assembly_metadata_enriched.csv")
    else:
        df = pd.read_csv(base_path)
        print("[WARN] Using base assembly_metadata.csv")

    if "Constituency_Registered_Voters" in df.columns:
        df["Seat_Registered"] = df["Constituency_Registered_Voters"].astype(int)
    else:
        df["Seat_Registered"] = (df["Registered_Voters"] / df["Assembly_Seats"]).astype(int)
    df["Seat_Polled"] = (df["Seat_Registered"] * df["Turnout_2026"] / 100).astype(int)
    
    if limit:
        df = df.head(limit)
        print(f"[DEBUG] Limited simulation to first {limit} constituencies.")

    # Check Cerebras (sync ping — fast enough to do outside async loop)
    try:
        OLLAMA_IS_RUNNING = get_cerebras_client().ping()
    except Exception:
        OLLAMA_IS_RUNNING = False
    print(f"[{'OK' if OLLAMA_IS_RUNNING else 'WARN'}] Cerebras: {'ONLINE — LLM active' if OLLAMA_IS_RUNNING else 'OFFLINE — heuristic fallback'}")

    df_sent = pd.read_csv("assembly_candidate_sentiment.csv") if os.path.exists("assembly_candidate_sentiment.csv") else pd.DataFrame()

    total_seats = len(df)
    completed   = _load_checkpoint()

    if completed:
        print(f"[RESUME] {len(completed)}/{total_seats} already done.")
    else:
        # Initialize CSVs with headers immediately
        # Initialize CSVs with correct high-fidelity headers
        results_headers = [
            "Constituency", "District", "Culture", "Seat_Polled", 
            "SPA_Votes", "AIADMK_Votes", "TVK_Votes", "Others_Votes", 
            "SPA_Pct", "AIADMK_Pct", "TVK_Pct", "Others_Pct", 
            "Winner", "Winning_Votes", "Margin_Votes", "Margin_Pct"
        ]
        pd.DataFrame(columns=results_headers).to_csv("simulation_results.csv", index=False)
        
        # Logs include Round 1 and Round 2 debate data
        log_headers = [
            "Constituency", "Culture", "Persona", "Occupation", "Age", "Gender",
            "Literacy", "Media", "Concern", "Bucket_Voters", "Decision_Mode",
            "SPA_Pct", "AIADMK_Pct", "TVK_Pct", "Others_Pct",
            "SPA_Votes", "AIADMK_Votes", "TVK_Votes", "Others_Votes",
            "Reason", "Raw_Response",
            "R1_Welfare_SPA", "R1_Welfare_ADMK", "R1_Welfare_TVK", "R1_Welfare_Others", "R1_Welfare_Reason",
            "R1_Economy_SPA", "R1_Economy_ADMK", "R1_Economy_TVK", "R1_Economy_Others", "R1_Economy_Reason",
            "R1_Youth_SPA", "R1_Youth_ADMK", "R1_Youth_TVK", "R1_Youth_Others", "R1_Youth_Reason",
            "R2_Welfare_SPA", "R2_Welfare_ADMK", "R2_Welfare_TVK", "R2_Welfare_Others", "R2_Welfare_Reason",
            "R2_Economy_SPA", "R2_Economy_ADMK", "R2_Economy_TVK", "R2_Economy_Others", "R2_Economy_Reason",
            "R2_Youth_SPA", "R2_Youth_ADMK", "R2_Youth_TVK", "R2_Youth_Others", "R2_Youth_Reason"
        ]
        pd.DataFrame(columns=log_headers).to_csv("voter_agent_logs.csv", index=False)
        print("[FRESH] Starting new simulation run (CSVs initialized).")

    pending_df = df[~df["Constituency"].isin(completed)].reset_index(drop=True)
    print(f"\nAsync simulation: {CONSTITUENCY_WORKERS} semaphore slots | {len(pending_df)} constituencies remaining...")

    semaphore  = asyncio.Semaphore(CONSTITUENCY_WORKERS)
    csv_lock   = asyncio.Lock()
    comp_lock  = asyncio.Lock()

    client = get_cerebras_client()

    async def _run_one(i, row):
        if _stop_requested:
            return None
        res = await _simulate_constituency_async(client, semaphore, csv_lock, int(len(completed)) + i, total_seats, row, df_sent)
        if res is None:
            return None
        seat_result, persona_logs = res
        cname = seat_result["Constituency"]

        # ── Write immediately on completion (don't wait for all 234) ──────────
        async with csv_lock:
            pd.DataFrame([seat_result]).to_csv(
                "simulation_results.csv", mode="a",
                header=not os.path.exists("simulation_results.csv") or os.path.getsize("simulation_results.csv") == 0,
                index=False)
            pd.DataFrame(persona_logs).to_csv(
                "voter_agent_logs.csv", mode="a",
                header=not os.path.exists("voter_agent_logs.csv") or os.path.getsize("voter_agent_logs.csv") == 0,
                index=False)

        async with comp_lock:
            completed.add(cname)
            _save_checkpoint(completed)

        return seat_result  # only return summary, not full logs

    tasks   = [_run_one(i, row) for i, row in pending_df.iterrows()]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    final_seat_results = [r for r in results if r and not isinstance(r, Exception)]
    for r in results:
        if isinstance(r, Exception):
            print(f"[ERROR] {r}")

    done = len(completed)
    print(f"\n{'='*60}")
    if _stop_requested and (total_seats - done) > 0:
        print(f"[PAUSED] {done}/{total_seats} done. Re-run to resume.")
    else:
        if os.path.exists(CHECKPOINT_FILE):
            os.remove(CHECKPOINT_FILE)
        print(f"SIMULATION COMPLETE — {total_seats} constituencies, "
              f"{sum(r['Seat_Polled'] for r in final_seat_results):,} total votes")
        print(pd.DataFrame(final_seat_results)["Winner"].value_counts().to_string())


if __name__ == "__main__":
    run_simulation()

