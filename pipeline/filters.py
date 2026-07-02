import sys
sys.path.insert(0, '.')
from config import SERVICES_FIRMS, NON_TECH_TITLES

def _check_tenure_impossible(c: dict) -> bool:
    """Returns True if candidate is VALID (no impossible tenure)."""
    yoe = c["profile"].get("years_of_experience", 0)
    for role in c.get("career_history", []):
        duration = role.get("duration_months", 0)
        if duration > yoe * 14:
            return False
    return True

def _check_skill_inflation(c: dict) -> bool:
    """Returns True if candidate is VALID (no fake expert skills)."""
    fake_expert_count = 0
    for skill in c.get("skills", []):
        if (skill.get("proficiency") == "expert" and
                skill.get("duration_months", 0) == 0 and
                skill.get("endorsements", 0) == 0):
            fake_expert_count += 1
    return fake_expert_count < 3

def _check_experience_vs_education(c: dict) -> bool:
    """Returns True if claimed YOE is plausible vs graduation year."""
    edu = c.get("education", [])
    if not edu:
        return True
    end_years = [e.get("end_year", 2020) for e in edu if e.get("end_year")]
    if not end_years:
        return True
    earliest_grad = min(end_years)
    yoe = c["profile"].get("years_of_experience", 0)
    max_possible_yoe = (2026 - earliest_grad) + 4
    return yoe <= max_possible_yoe

def _check_location_reachable(c: dict) -> bool:
    """Returns True if candidate could reach the role."""
    country = c["profile"].get("country", "India")
    willing = c.get("redrob_signals", {}).get("willing_to_relocate", False)
    if country != "India" and not willing:
        return False
    return True

def _check_not_purely_nontechnical(c: dict) -> bool:
    """Returns True if candidate has some technical background."""
    current_title = c["profile"].get("current_title", "").lower()
    is_nontechnical_title = any(
        t.lower() in current_title for t in NON_TECH_TITLES
    )
    if not is_nontechnical_title:
        return True
    tech_keywords = ["engineer", "scientist", "developer", "researcher",
                     "analyst", "architect", "ml", "ai", "data"]
    for role in c.get("career_history", []):
        title = role.get("title", "").lower()
        if any(kw in title for kw in tech_keywords):
            return True
    return False

def _check_multiple_current_employers(c: dict) -> bool:
    """Returns True if candidate is VALID (not 3+ current jobs at different companies)."""
    current_jobs = [j for j in c.get("career_history", []) if j.get("is_current")]
    if len(current_jobs) >= 3:
        companies = {j.get("company", "") for j in current_jobs}
        if len(companies) >= 3:
            return False
    return True

def _check_expert_vs_assessment(c: dict) -> bool:
    """Returns True if candidate is VALID (no expert + low assessment contradiction)."""
    assessment_scores = c.get("redrob_signals", {}).get("skill_assessment_scores", {})
    if not assessment_scores:
        return True
    contradictions = 0
    for skill in c.get("skills", []):
        if skill.get("proficiency") == "expert":
            score = assessment_scores.get(skill["name"], -1)
            if 0 <= score < 35:
                contradictions += 1
    return contradictions < 2

def hard_filter(candidates: list) -> list:
    checks = {
        "Honeypot (impossible tenure)": _check_tenure_impossible,
        "Honeypot (skill inflation)":   _check_skill_inflation,
        "Honeypot (edu vs exp)":        _check_experience_vs_education,
        "Honeypot (multi-employer)":    _check_multiple_current_employers,
        "Honeypot (expert vs assess)":  _check_expert_vs_assessment,
        "Location unreachable":         _check_location_reachable,
        "Purely non-technical":         _check_not_purely_nontechnical,
    }

    removed_counts = {name: 0 for name in checks}
    kept = []

    for c in candidates:
        passed = True
        for name, fn in checks.items():
            if not fn(c):
                removed_counts[name] += 1
                passed = False
                break
        if passed:
            kept.append(c)

    print("\n-- Hard Filter Results -------------------------")
    for name, count in removed_counts.items():
        print(f"  {name:<35} {count:>6} removed")
    print(f"  {'Remaining candidates':<35} {len(kept):>6}")
    print("------------------------------------------------\n")

    return kept
