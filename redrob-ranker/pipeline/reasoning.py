"""
pipeline/reasoning.py
Fact-based reasoning builder. Every string is grounded in actual candidate data.
No template phrases. No hallucination.
"""
from datetime import datetime
from dateutil.parser import parse as parse_date


# Banned template phrases from the old system. If any appears, it's a bug.
BANNED_PHRASES = [
    "Has owned the ranking layer for an e-commerce",
    "Has shipped ranking models for a product discovery",
    "Has built a content recommendation system (10M",
    "Has developed a semantic search feature for an internal knowledge base",
    "Has implemented a RAG-based customer support chatbot",
    "Has built a RAG-based ranking pipeline at scale (50M",
    "Has led migration from keyword to embedding",
    "Has shipped personalisation infrastructure",
    "Has fine-tuned LLMs (LLaMA/Mistral) with LoRA",
    "Has owned end-to-end ranking at a recommendations",
    "Has designed and rolled out large-scale semantic search",
]

# Core skills worth highlighting in reasoning
CORE_SKILLS = {
    "embeddings", "sentence-transformers", "sentence transformers",
    "vector search", "faiss", "pinecone", "weaviate",
    "qdrant", "milvus", "elasticsearch", "opensearch",
    "information retrieval", "ranking", "reranking",
    "semantic search", "nlp", "rag",
    "learning to rank", "lora", "qlora", "peft",
    "fine-tuning llms", "bge", "e5",
}

# Title keywords for finding best role
_ROLE_KEYWORDS = [
    "ml", "ai", "search", "ranking", "nlp", "retrieval",
    "recommendation", "recsys", "scientist", "applied",
]

# Primary cities
PRIMARY_CITIES = [
    "Pune", "Noida", "Delhi", "Gurgaon", "Gurugram",
    "Hyderabad", "Mumbai", "Bangalore", "Bengaluru",
]


def _find_best_role(career_history: list):
    """Find the first role whose title contains an ML/AI/search keyword."""
    for job in career_history:
        title_l = job.get("title", "").lower()
        if any(kw in title_l for kw in _ROLE_KEYWORDS):
            return job
    return career_history[0] if career_history else None


def _find_trusted_skills(skills: list, max_count: int = 2) -> list:
    """Find skills with real trust signals: duration >= 10, endorsements >= 4, advanced/expert."""
    result = []
    for s in skills:
        name_l = s["name"].lower()
        if (name_l in CORE_SKILLS
                and s.get("duration_months", 0) >= 10
                and s.get("endorsements", 0) >= 4
                and s.get("proficiency") in ("advanced", "expert")):
            dur = s.get("duration_months", 0)
            result.append(f"{s['name']} ({dur}mo)")
        if len(result) >= max_count:
            break
    return result


def build_reasoning(candidate: dict, score_details: dict) -> str:
    """
    Build a 2-sentence reasoning string from ACTUAL candidate fields.
    Every string is unique because it uses real values.
    """
    profile = candidate["profile"]
    signals = candidate.get("redrob_signals", {})
    skills = candidate.get("skills", [])
    career_history = candidate.get("career_history", [])

    # ── SENTENCE 1: Who they are (from real fields) ──────────────────────
    title = profile.get("current_title", "Engineer")
    company = profile.get("current_company", "")
    yoe = profile.get("years_of_experience", 0)

    best_role = _find_best_role(career_history)
    if best_role:
        best_company = best_role.get("company", "")
        best_duration = best_role.get("duration_months", 0)
        best_title = best_role.get("title", "")
    else:
        best_company = company
        best_duration = 0
        best_title = title

    # Build s1
    if best_company != company and best_company:
        s1 = f"{title} at {company} ({yoe}yr); prior: {best_title} at {best_company} {best_duration}mo"
    else:
        s1 = f"{title} at {company} ({yoe}yr, {best_duration}mo in role)"

    trusted_skills = _find_trusted_skills(skills)
    if trusted_skills:
        s1 += f"; skills: {', '.join(trusted_skills)}"

    # ── SENTENCE 2: Signals and fit (from real values) ───────────────────
    # Read actual signal values
    last_active_s = signals.get("last_active_date", "2020-01-01")
    try:
        last_active = parse_date(last_active_s)
        days_inactive = (datetime(2026, 6, 26) - last_active).days
    except Exception:
        days_inactive = 999

    notice_period_days = signals.get("notice_period_days", 180)
    recruiter_response_rate = signals.get("recruiter_response_rate", 0.0)
    open_to_work_flag = signals.get("open_to_work_flag", False)
    github_activity_score = signals.get("github_activity_score", -1)
    willing_to_relocate = signals.get("willing_to_relocate", False)
    location = profile.get("location", "Unknown")
    country = profile.get("country", "India")

    in_target = any(c.lower() in location.lower() for c in PRIMARY_CITIES)

    parts = []

    # Location
    if in_target:
        parts.append(f"{location} (target)")
    elif country == "India" and willing_to_relocate:
        parts.append(f"{location}, relocate-ready")
    elif country == "India":
        parts.append(f"{location}, not relocating")
    else:
        parts.append(f"{country} (international)")

    # Notice
    if notice_period_days <= 30:
        parts.append("available <=30d")
    elif notice_period_days <= 60:
        parts.append(f"{notice_period_days}d notice")
    else:
        parts.append(f"long notice {notice_period_days}d")

    # Activity
    if days_inactive <= 30:
        parts.append(f"active {days_inactive}d ago")
    elif days_inactive > 120:
        parts.append(f"inactive {days_inactive}d")

    # Response rate
    rr = int(recruiter_response_rate * 100)
    if rr >= 70:
        parts.append(f"response {rr}%")
    elif rr < 25:
        parts.append(f"low response {rr}%")

    # GitHub
    if github_activity_score > 55:
        parts.append(f"GitHub {int(github_activity_score)}")

    s2 = "; ".join(parts) + "."

    result = f"{s1}. {s2}"

    # ── SAFETY: Banned phrase guard ──────────────────────────────────────
    for phrase in BANNED_PHRASES:
        if phrase in result:
            raise ValueError(f"BUG: banned phrase found: {phrase[:50]}")

    # Truncate to 300 chars max
    return result[:300].strip()
