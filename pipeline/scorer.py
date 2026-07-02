"""
pipeline/scorer.py
Multi-dimensional scoring engine for candidate ranking.
Career, skills, and experience are combined additively,
then location and behavioral are applied as terminal multipliers.
"""
import re
from datetime import datetime
from dateutil.parser import parse as parse_date


# ── CORE DESCRIPTION TERMS ───────────────────────────────────────────────────
CORE_TERMS = [
    "embedding", "vector", "retrieval", "ranking", "recommendation",
    "semantic search", "faiss", "elasticsearch", "pinecone", "weaviate",
    "qdrant", "milvus", "opensearch", "deployed", "production", "real users",
    "shipped", "rerank", "dense retrieval", "bm25", "nlp", "language model",
    "fine-tun", "rag", "a/b test",
]

# ── SERVICES COMPANIES ──────────────────────────────────────────────────────
SERVICES_COMPANIES = {
    "tcs", "tata consultancy", "infosys", "wipro", "accenture", "cognizant",
    "capgemini", "hcl", "hcl technologies", "tech mahindra", "mphasis",
    "hexaware", "mindtree", "niit", "birlasoft", "ltimindtree", "persistent",
}

# ── SKILL CORE WEIGHTS ──────────────────────────────────────────────────────
CORE_WEIGHTS = {
    "embeddings": 1.0, "sentence-transformers": 1.0, "sentence transformers": 1.0,
    "vector search": 1.0, "faiss": 0.9, "pinecone": 0.9, "weaviate": 0.9,
    "qdrant": 0.9, "milvus": 0.9, "elasticsearch": 0.85, "opensearch": 0.85,
    "information retrieval": 1.0, "ranking": 0.85, "reranking": 0.90,
    "semantic search": 0.90, "nlp": 0.75, "rag": 0.90,
    "learning to rank": 0.85, "lora": 0.55, "qlora": 0.55, "peft": 0.55,
    "fine-tuning": 0.55, "transformers": 0.65, "huggingface": 0.60,
    "python": 0.50, "pytorch": 0.50, "vector database": 0.90,
    "computer vision": -0.20, "speech recognition": -0.20,
    "robotics": -0.35, "tts": -0.10,
}

PROFICIENCY_MULT = {
    "beginner": 0.35, "intermediate": 0.60, "advanced": 0.85, "expert": 1.0,
}

# ── TITLE TIERS ──────────────────────────────────────────────────────────────
TIER_1_TITLES = [
    "ml engineer", "machine learning engineer", "ai engineer",
    "search engineer", "ranking engineer", "nlp engineer",
    "applied scientist", "research engineer", "recsys",
    "recommendation systems engineer",
]
TIER_2_TITLES = ["data scientist", "applied ml", "applied ai"]
TIER_3_TITLES = ["software engineer", "backend engineer", "platform engineer"]
TIER_4_TITLES = ["data engineer", "analytics engineer"]

# ── SHIPPER KEYWORDS ────────────────────────────────────────────────────────
SHIPPER_KEYWORDS = [
    "shipped", "launched", "deployed", "went live", "in production",
    "real users", "a/b test", "improved latency", "increased ndcg",
    "migrated from", "v2", "end-to-end",
]

# ── PRIMARY TARGET CITIES ───────────────────────────────────────────────────
PRIMARY_CITIES = [
    "pune", "noida", "delhi", "new delhi", "gurugram", "gurgaon",
    "hyderabad", "mumbai", "bengaluru", "bangalore",
]

_NORM_RE = re.compile(r"[^a-z0-9]")

def _normalize(text: str) -> str:
    return _NORM_RE.sub("", text.lower())


# ── HONEYPOT DETECTOR ────────────────────────────────────────────────────────

def _is_honeypot(cand: dict):
    """Returns (is_hp: bool, reason: str)."""
    # 1. Expert/advanced skill with 0 duration
    for s in cand.get("skills", []):
        if s.get("proficiency") in ("expert", "advanced") and s.get("duration_months", 0) == 0:
            return True, f"Skill '{s['name']}' is expert/advanced but duration is 0"

    # 2. Career history date mismatch
    for job in cand.get("career_history", []):
        start_s = job.get("start_date")
        dur_reported = job.get("duration_months", 0)
        if start_s:
            try:
                start_d = parse_date(start_s)
                end_s = job.get("end_date")
                end_d = parse_date(end_s) if end_s else datetime(2026, 6, 26)
                actual_months = (end_d - start_d).days / 30.44
                if dur_reported > actual_months + 3:
                    return True, (
                        f"Job '{job.get('company')}' duration {dur_reported} mos "
                        f"> calendar {round(actual_months)} mos"
                    )
            except Exception:
                pass

    # 3. Job start before education start (gap > 6 years)
    edu_start_years = [
        edu["start_year"]
        for edu in cand.get("education", [])
        if edu.get("start_year")
    ]
    earliest_edu = min(edu_start_years) if edu_start_years else None

    job_start_years = []
    for job in cand.get("career_history", []):
        start_s = job.get("start_date")
        if start_s:
            try:
                job_start_years.append(parse_date(start_s).year)
            except Exception:
                pass
    earliest_job = min(job_start_years) if job_start_years else None

    if earliest_edu and earliest_job and earliest_edu - earliest_job > 6:
        return True, f"Job started in {earliest_job} but education started in {earliest_edu}"

    # 4. Multiple current jobs at different companies (3+ = strong signal)
    current_jobs = [j for j in cand.get("career_history", []) if j.get("is_current")]
    if len(current_jobs) >= 3:
        companies = list({j.get("company") for j in current_jobs})
        if len(companies) >= 3:
            return True, f"3+ simultaneous current jobs at: {companies[:3]}"

    # 5. Extreme YoE mismatch
    profile_yoe = cand["profile"].get("years_of_experience", 0)
    total_months = sum(j.get("duration_months", 0) for j in cand.get("career_history", []))
    total_years = total_months / 12.0
    if total_years - profile_yoe > 5.0 or profile_yoe - total_years > 10.0:
        return True, (
            f"YoE mismatch: profile={profile_yoe}, "
            f"sum of career={round(total_years, 1)}"
        )

    # 6. Skill proficiency vs assessment score mismatch
    assessment_scores = cand.get("redrob_signals", {}).get("skill_assessment_scores", {})
    if assessment_scores:
        contradictions = 0
        for s in cand.get("skills", []):
            if s.get("proficiency") == "expert":
                skill_name = s["name"]
                if skill_name in assessment_scores and assessment_scores[skill_name] < 35:
                    contradictions += 1
        if contradictions >= 2:
            return True, f"Expert proficiency but failed assessment in {contradictions} skills"

    return False, ""


# ── CAREER SCORE ─────────────────────────────────────────────────────────────

def _count_core_terms(text: str) -> int:
    text_l = text.lower()
    return sum(1 for term in CORE_TERMS if term in text_l)


def _career_score(career_history: list, signals: dict):
    """
    Score career history by reading actual role data.
    Returns (career_score: float, is_pure_services: bool).
    """
    if not career_history:
        return 0.0, False

    recency_weights = [1.0, 0.70, 0.45, 0.25]
    weighted_sum = 0.0
    weight_total = 0.0
    all_services = True

    for i, role in enumerate(career_history):
        title_l = role.get("title", "").lower()
        desc_l = role.get("description", "").lower()
        company_l = role.get("company", "").lower()
        core_count = _count_core_terms(desc_l)

        # Title score
        if any(t in title_l for t in TIER_1_TITLES):
            title_score = 1.0
        elif any(t in title_l for t in TIER_2_TITLES) and core_count >= 2:
            title_score = 0.80
        elif any(t in title_l for t in TIER_3_TITLES) and core_count >= 3:
            title_score = 0.60
        elif any(t in title_l for t in TIER_4_TITLES):
            title_score = 0.35
        else:
            title_score = 0.10

        # Company score
        is_services = any(s in company_l for s in SERVICES_COMPANIES)
        if is_services:
            company_score = 0.20
        else:
            all_services = False
            company_size = role.get("company_size", "")
            if company_size in ("51-200", "201-500"):
                company_score = 0.95
            elif company_size in ("501-1000", "1001-5000"):
                company_score = 0.80
            else:
                company_score = 0.60

        # Description score
        description_score = min(core_count / 6.0, 1.0)

        # Combine
        role_score = title_score * 0.40 + company_score * 0.25 + description_score * 0.35

        w = recency_weights[i] if i < len(recency_weights) else 0.25
        weighted_sum += role_score * w
        weight_total += w

    career_score = weighted_sum / weight_total if weight_total > 0 else 0.0

    # Pure services penalty
    if all_services and len(career_history) > 0:
        career_score *= 0.35

    return career_score, all_services


# ── SKILLS TRUST SCORE ───────────────────────────────────────────────────────

def _skills_score(skills: list, signals: dict) -> float:
    """Trust-weighted skills score."""
    assessment_map = signals.get("skill_assessment_scores", {})
    skill_total = 0.0
    penalty_total = 0.0

    for s in skills:
        name_l = s["name"].lower()
        base = CORE_WEIGHTS.get(name_l, 0.0)

        if base < 0:
            # CV/speech/robotics penalty
            penalty_total += abs(base)
            continue
        if base == 0:
            continue

        prof = s.get("proficiency", "beginner")
        prof_mult = PROFICIENCY_MULT.get(prof, 0.35)

        endorse_trust = min(s.get("endorsements", 0) / 35.0, 1.0)
        duration_trust = min(s.get("duration_months", 0) / 20.0, 1.0)

        assessment = assessment_map.get(s["name"], -1)
        assess_trust = (assessment / 100.0) if assessment >= 0 else 0.50

        trust = 0.35 * endorse_trust + 0.35 * duration_trust + 0.30 * assess_trust
        skill_total += base * prof_mult * trust

    score = min(skill_total / 2.5, 1.0)
    score = max(score - penalty_total * 0.1, 0.0)  # apply CV/robotics penalty
    return score


# ── EXPERIENCE SCORE ─────────────────────────────────────────────────────────

def _experience_score(yoe: float) -> float:
    if 6 <= yoe <= 8:
        return 1.0
    elif 5 <= yoe < 6 or 8 < yoe <= 9:
        return 0.85
    elif 4 <= yoe < 5 or 9 < yoe <= 11:
        return 0.65
    elif 3 <= yoe < 4 or 11 < yoe <= 13:
        return 0.40
    else:
        return 0.20


# ── LOCATION MULTIPLIER ─────────────────────────────────────────────────────

def _location_multiplier(profile: dict, signals: dict) -> float:
    location = profile.get("location", "").lower()
    country = profile.get("country", "").lower()
    willing = signals.get("willing_to_relocate", False)

    is_india = country in ("india", "in") or "india" in location

    if any(city in location for city in PRIMARY_CITIES):
        return 1.0

    if is_india:
        return 0.78 if willing else 0.50

    # Outside India
    return 0.25 if willing else 0.05


# ── BEHAVIORAL MULTIPLIER ───────────────────────────────────────────────────

def _behavioral_multiplier(signals: dict) -> float:
    """
    Range: 0.45 to 1.0.
    Formula: 0.45 + 0.55 * behavioral_raw
    """
    # Recency
    last_active_s = signals.get("last_active_date", "2020-01-01")
    try:
        last_active = parse_date(last_active_s)
        days_inactive = (datetime(2026, 6, 26) - last_active).days
    except Exception:
        days_inactive = 999

    if days_inactive <= 14:
        recency = 1.0
    elif days_inactive <= 30:
        recency = 0.88
    elif days_inactive <= 60:
        recency = 0.72
    elif days_inactive <= 90:
        recency = 0.55
    elif days_inactive <= 180:
        recency = 0.30
    else:
        recency = 0.08

    response_rate = signals.get("recruiter_response_rate", 0.0)
    open_to_work = signals.get("open_to_work_flag", False)
    interview_rate = signals.get("interview_completion_rate", 0.5)

    behavioral_raw = (
        0.40 * recency +
        0.30 * response_rate +
        0.20 * (1.0 if open_to_work else 0.15) +
        0.10 * interview_rate
    )

    return 0.45 + (0.55 * behavioral_raw)


# ── SHIPPER BONUS ────────────────────────────────────────────────────────────

def _shipper_bonus(career_history: list) -> float:
    """Scan career descriptions for shipper keywords. Max bonus 0.12."""
    all_desc = " ".join(j.get("description", "") for j in career_history).lower()
    matches = sum(1 for kw in SHIPPER_KEYWORDS if kw in all_desc)
    return min(matches * 0.015, 0.12)


# ── MASTER SCORING FUNCTION ─────────────────────────────────────────────────

def score_candidate(cand: dict):
    """
    Returns (final_score, matched_labels, detail_dict).
    If honeypot or no career match -> (0.0, "honeypot"/"no_career_match", reason_str).
    """
    # Honeypot gate
    hp, reason = _is_honeypot(cand)
    if hp:
        return 0.0, "honeypot", reason

    profile = cand["profile"]
    career_history = cand.get("career_history", [])
    skills = cand.get("skills", [])
    signals = cand.get("redrob_signals", {})

    # Career score
    career, is_pure_services = _career_score(career_history, signals)
    if career == 0.0:
        return 0.0, "no_career_match", "No matching career description"

    # Sub-scores (all 0-1 range)
    sk = _skills_score(skills, signals)
    exp = _experience_score(profile.get("years_of_experience", 0))

    # Weighted additive raw (0-1 range)
    raw = (career * 0.45) + (sk * 0.30) + (exp * 0.25)

    # Shipper bonus (multiplicative nudge, capped at +12%)
    ship = _shipper_bonus(career_history)
    raw = raw * (1.0 + ship)

    # Terminal multipliers
    loc_m = _location_multiplier(profile, signals)
    beh_m = _behavioral_multiplier(signals)

    final_score = round(raw * loc_m * beh_m * 100.0, 6)
    final_score = max(final_score, 0.001)

    return {
        "score": final_score,
        "components": {
            "career": round(career, 4),
            "skills": round(sk, 4),
            "experience": round(exp, 4),
            "location_mult": round(loc_m, 4),
            "behavioral_mult": round(beh_m, 4),
            "shipper_bonus": round(ship, 4),
            "is_pure_services": is_pure_services,
        }
    }
