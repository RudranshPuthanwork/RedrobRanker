"""
Redrob Candidate Ranker — Gradio App
=====================================
Hugging Face Space front-end for the Redrob multi-dimensional candidate
ranking pipeline (rank.py + pipeline/{loader,filters,scorer,reasoning,output}.py).

This app:
  1. Lets a user upload a candidates.jsonl file.
  2. Runs the existing ranking pipeline (rank.py) as a subprocess so the
     Space stays decoupled from internal pipeline implementation details.
  3. Displays the ranked results in a table, with per-candidate reasoning.
  4. Offers the final CSV as a download.
  5. Includes an "About" tab documenting the architecture, scoring formula,
     and honeypot filters, plus a button to generate synthetic sample data
     for quick testing when the user has no real dataset handy.

Expected repo layout (sibling files to this app.py):
    rank.py
    config.py
    pipeline/
        __init__.py
        loader.py
        filters.py
        scorer.py
        reasoning.py
        output.py
"""

import json
import os
import random
import subprocess
import sys
import tempfile
import traceback
from datetime import datetime, timedelta

import gradio as gr
import pandas as pd

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
RANK_SCRIPT = os.path.join(REPO_ROOT, "rank.py")

TARGET_CITIES = [
    ("Pune", "Maharashtra"), ("Noida", "Uttar Pradesh"), ("Delhi", "Delhi"),
    ("Gurugram", "Haryana"), ("Hyderabad", "Telangana"), ("Mumbai", "Maharashtra"),
    ("Bengaluru", "Karnataka"),
]
OTHER_LOCATIONS = [("Chennai", "Tamil Nadu"), ("Toronto", None), ("London", None),
                    ("San Francisco", None), ("Singapore", None)]

POSITIVE_SKILLS = ["Embeddings", "Vector Search", "FAISS", "RAG", "NLP",
                    "Transformers", "Search Ranking", "Fine-tuning LLMs", "LoRA"]
NEGATIVE_SKILLS = ["Computer Vision", "Robotics", "Image Classification"]
NEUTRAL_SKILLS = ["Python", "SQL", "AWS", "Kubernetes", "Docker", "GCP", "Excel"]

COMPANIES = ["Search Labs AI", "VectorForge", "NeuralIndex", "InfoRetriever Inc",
             "TCS", "Infosys", "Wipro", "SemanticStack", "RankWorks"]
INDUSTRIES = ["Software", "IT Services", "AI/ML", "E-commerce"]
COMPANY_SIZES = ["1-50", "51-200", "201-500", "1001-5000", "10001+"]
TITLES = ["ML Engineer", "NLP Engineer", "Search Engineer", "Applied Scientist",
          "Data Scientist", "Backend Engineer", "Software Engineer"]
DESCRIPTIONS = [
    "Deployed and launched a production RAG search pipeline using embeddings and FAISS.",
    "Built and A/B tested a vector search ranking model serving live traffic.",
    "Worked on internal tooling, support tickets, and minor bug fixes.",
    "Researched perception using computer vision and robotics control loops.",
]


# --------------------------------------------------------------------------
# Sample data generation (for users without a real dataset to test with)
# --------------------------------------------------------------------------

def _iso(d: datetime) -> str:
    return d.strftime("%Y-%m-%d")


def _random_candidate(idx: int) -> dict:
    total_exp = round(random.uniform(1, 14), 1)
    n_roles = random.randint(1, 4)
    career = []
    cursor = datetime.now()
    months_left = int(total_exp * 12)
    for i in range(n_roles):
        dur = max(3, min(months_left, random.randint(6, 48)))
        months_left = max(0, months_left - dur)
        start = cursor - timedelta(days=dur * 30)
        is_current = i == 0
        career.append({
            "company": random.choice(COMPANIES),
            "title": random.choice(TITLES),
            "start_date": _iso(start),
            "end_date": None if is_current else _iso(cursor),
            "duration_months": dur,
            "is_current": is_current,
            "industry": random.choice(INDUSTRIES),
            "company_size": random.choice(COMPANY_SIZES),
            "description": random.choice(DESCRIPTIONS),
        })
        cursor = start

    grad_end = datetime.now().year - int(total_exp) - random.randint(0, 1)
    education = [{
        "institution": random.choice(["IIT Bombay", "BITS Pilani", "VIT Chennai", "Georgia Tech"]),
        "degree": random.choice(["B.E.", "B.Tech", "M.Tech", "B.Sc"]),
        "field_of_study": random.choice(["Computer Science", "Artificial Intelligence", "Electronics"]),
        "start_year": grad_end - 4,
        "end_year": grad_end,
        "grade": f"{round(random.uniform(6.0, 9.5), 2)} CGPA",
        "tier": random.choice(["tier_1", "tier_2", "tier_3"]),
    }]

    skills = []
    assessment_scores = {}
    for name in random.sample(POSITIVE_SKILLS, k=random.randint(2, 5)):
        prof = random.choice(["beginner", "intermediate", "advanced", "expert"])
        skills.append({
            "name": name,
            "proficiency": prof,
            "endorsements": random.randint(0, 50),
            "duration_months": random.randint(0, 48),
        })
        if random.random() < 0.7:
            assessment_scores[name] = round(random.uniform(20, 100), 1)
    for name in random.sample(NEGATIVE_SKILLS, k=random.randint(0, 2)):
        skills.append({
            "name": name,
            "proficiency": random.choice(["beginner", "intermediate", "advanced"]),
            "endorsements": random.randint(0, 20),
            "duration_months": random.randint(0, 24),
        })
    for name in random.sample(NEUTRAL_SKILLS, k=random.randint(1, 3)):
        skills.append({
            "name": name,
            "proficiency": random.choice(["beginner", "intermediate", "advanced"]),
            "endorsements": random.randint(0, 20),
            "duration_months": random.randint(0, 24),
        })

    city, state = random.choice(TARGET_CITIES + OTHER_LOCATIONS)
    is_india = state is not None or city in [c for c, s in TARGET_CITIES]
    location_str = f"{city}, {state}" if state else city

    last_active = datetime.now() - timedelta(days=random.randint(0, 120))
    signup = datetime.now() - timedelta(days=random.randint(120, 600))

    return {
        "candidate_id": f"CAND_{idx:07d}",
        "profile": {
            "anonymized_name": f"Candidate {idx}",
            "headline": f"{career[0]['title']} | {total_exp} yrs experience",
            "summary": f"Professional with {total_exp} years of experience in {career[0]['industry']}.",
            "location": location_str,
            "country": "India" if is_india else city,
            "years_of_experience": total_exp,
            "current_title": career[0]["title"],
            "current_company": career[0]["company"],
            "current_company_size": career[0]["company_size"],
            "current_industry": career[0]["industry"],
        },
        "career_history": career,
        "education": education,
        "skills": skills,
        "certifications": [],
        "languages": [{"language": "English", "proficiency": "professional"}],
        "redrob_signals": {
            "profile_completeness_score": round(random.uniform(30, 100), 1),
            "signup_date": _iso(signup),
            "last_active_date": _iso(last_active),
            "open_to_work_flag": random.choice([True, False]),
            "profile_views_received_30d": random.randint(0, 50),
            "applications_submitted_30d": random.randint(0, 10),
            "recruiter_response_rate": round(random.uniform(0, 1), 2),
            "avg_response_time_hours": round(random.uniform(1, 200), 1),
            "skill_assessment_scores": assessment_scores,
            "connection_count": random.randint(10, 800),
            "endorsements_received": random.randint(0, 60),
            "notice_period_days": random.choice([0, 15, 30, 60, 90]),
            "expected_salary_range_inr_lpa": {
                "min": round(random.uniform(8, 25), 1),
                "max": round(random.uniform(25, 50), 1),
            },
            "preferred_work_mode": random.choice(["onsite", "remote", "hybrid"]),
            "willing_to_relocate": random.choice([True, False]),
            "github_activity_score": round(random.uniform(-1, 100), 1),
            "search_appearance_30d": random.randint(0, 300),
            "saved_by_recruiters_30d": random.randint(0, 10),
            "interview_completion_rate": round(random.uniform(0, 1), 2),
            "offer_acceptance_rate": round(random.uniform(-1, 1), 2),
            "verified_email": random.choice([True, False]),
            "verified_phone": random.choice([True, False]),
            "linkedin_connected": random.choice([True, False]),
        },
    }


def generate_sample_jsonl(n: int = 100):
    random.seed(42)
    rows = [_random_candidate(i) for i in range(1, n + 1)]
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False, dir=tempfile.gettempdir()
    )
    for r in rows:
        tmp.write(json.dumps(r) + "\n")
    tmp.close()
    return tmp.name


def make_sample_file():
    path = generate_sample_jsonl(100)
    return path, f"✅ Generated {os.path.basename(path)} with 100 synthetic candidates."


# --------------------------------------------------------------------------
# Pipeline runner
# --------------------------------------------------------------------------

def _normalize_to_jsonl(raw_path: str) -> str:
    """rank.py's loader expects line-delimited JSON (one candidate per line).
    Users may instead upload a single .json file containing a JSON array of
    candidates (as Redrob's sample export does) -- convert that transparently
    into a temp .jsonl file. Files that are already valid JSONL pass through
    unchanged."""
    with open(raw_path, "r", encoding="utf-8") as f:
        content = f.read()

    stripped = content.lstrip()

    # Case 1: a JSON array -> explode into one line per candidate.
    if stripped.startswith("["):
        candidates = json.loads(content)
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False, dir=tempfile.gettempdir()
        )
        for c in candidates:
            tmp.write(json.dumps(c) + "\n")
        tmp.close()
        return tmp.name

    # Case 2: a single JSON object -> wrap as a one-line JSONL file.
    if stripped.startswith("{"):
        try:
            obj = json.loads(content)
            tmp = tempfile.NamedTemporaryFile(
                mode="w", suffix=".jsonl", delete=False, dir=tempfile.gettempdir()
            )
            tmp.write(json.dumps(obj) + "\n")
            tmp.close()
            return tmp.name
        except json.JSONDecodeError:
            pass  # fall through -- might already be valid JSONL

    # Case 3: already JSONL (or something rank.py's loader can handle as-is).
    return raw_path


def run_ranker(candidates_file, top_n):
    """Invoke rank.py as a subprocess and load the resulting CSV."""
    if candidates_file is None:
        return None, None, "⚠️ Please upload a candidates .json or .jsonl file first (or generate a sample)."

    if not os.path.exists(RANK_SCRIPT):
        return None, None, (
            "❌ Could not find rank.py next to app.py.\n"
            "Make sure rank.py, config.py, and the pipeline/ package are uploaded "
            "alongside this app.py in the Space repo."
        )

    raw_path = candidates_file.name if hasattr(candidates_file, "name") else candidates_file

    try:
        in_path = _normalize_to_jsonl(raw_path)
    except Exception:
        return None, None, f"❌ Could not parse the uploaded file as JSON/JSONL:\n{traceback.format_exc()}"

    out_fd, out_path = tempfile.mkstemp(suffix=".csv")
    os.close(out_fd)

    cmd = [
        sys.executable, RANK_SCRIPT,
        "--candidates", in_path,
        "--out", out_path,
        "--top", str(int(top_n)),
    ]

    try:
        proc = subprocess.run(
            cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=600
        )
    except Exception as e:
        return None, None, f"❌ Failed to launch rank.py:\n{traceback.format_exc()}"

    convert_note = f"(converted {os.path.basename(raw_path)} -> JSONL)\n" if in_path != raw_path else ""
    log = f"{convert_note}$ {' '.join(cmd)}\n\n--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}"

    if proc.returncode != 0:
        return None, None, f"❌ Pipeline exited with code {proc.returncode}.\n\n{log}"

    if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
        return None, None, f"⚠️ Pipeline finished but produced no output file.\n\n{log}"

    try:
        df = pd.read_csv(out_path)
    except Exception:
        return None, None, f"❌ Could not parse output CSV.\n\n{log}"

    status = f"✅ Ranked {len(df)} candidates. Output saved to CSV.\n\n{log}"
    return df, out_path, status


# --------------------------------------------------------------------------
# About tab content
# --------------------------------------------------------------------------

ABOUT_MD = """
## Redrob Candidate Ranker

An automated, multi-dimensional candidate evaluation and ranking system for
specialized technical roles (ML / NLP / Search Engineering). It filters out
fraudulent "honeypot" profiles, scores eligible candidates across five
dimensions, and generates grounded, fact-based reasoning for each rank.

### Pipeline stages
1. **Loader** — parses the input `.jsonl` file of raw candidate profiles.
2. **Honeypot & Hard Filter Gate** — drops candidates that fail consistency
   checks: impossible tenure, skill inflation, education/experience mismatch,
   3+ concurrent "current" jobs, expert-vs-assessment contradictions, location
   reachability, and purely non-technical career history.
3. **Scoring Engine** — combines:
   - Career Score (45%)
   - Skills Score (30%)
   - Experience Score (25%)
   - → Raw Score, then applies:
     - Shipper Bonus (up to +12%)
     - Location Multiplier (1.0 → 0.05 depending on city / relocation)
     - Behavioral Multiplier (recency, responsiveness, interview completion)
4. **Deterministic Sorting** — by score (desc), ties broken by `candidate_id` (asc).
5. **Reasoning Builder** — two-sentence, template-safe justification grounded
   in real profile fields.
6. **Exporter & Self-Validation** — writes the final CSV and checks headers,
   row count, unique IDs, sequential ranks, monotonic scores, and non-empty
   reasoning.

### Scoring formula
```
Final Score = Raw Score × (1 + Shipper Bonus) × Location Multiplier × Behavioral Multiplier
```

### Location multiplier
| Situation                              | Multiplier |
|-----------------------------------------|-----------:|
| Target Indian city (Mumbai, Bengaluru…) |       1.00 |
| India, willing to relocate              |       0.78 |
| India, not relocating                   |       0.50 |
| International, willing to relocate      |       0.25 |
| International, not relocating           |       0.05 |

### Run from the command line
```bash
python rank.py --candidates <path_to_candidates.jsonl> --out <path_to_output.csv> --top 100
```
"""


# --------------------------------------------------------------------------
# Gradio UI
# --------------------------------------------------------------------------

with gr.Blocks(title="Redrob Candidate Ranker", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🏆 Redrob Candidate Ranker")
    gr.Markdown(
        "Upload a `candidates.jsonl` file, pick how many top candidates to keep, "
        "and run the full honeypot-filtering + multi-dimensional scoring pipeline."
    )

    with gr.Tabs():
        with gr.TabItem("Run Ranker"):
            with gr.Row():
                with gr.Column(scale=1):
                    file_input = gr.File(
                        label="Candidates file (.json array or .jsonl)",
                        file_types=[".json", ".jsonl"],
                    )
                    top_n = gr.Slider(
                        minimum=1, maximum=500, value=100, step=1,
                        label="Top N candidates to output",
                    )
                    run_btn = gr.Button("🚀 Run Ranker", variant="primary")

                    gr.Markdown("---")
                    gr.Markdown("**No dataset handy?** Generate synthetic sample data:")
                    sample_btn = gr.Button("🎲 Generate 100 sample candidates")
                    sample_file_out = gr.File(label="Generated sample file", interactive=False)
                    sample_status = gr.Markdown()

                with gr.Column(scale=2):
                    status_box = gr.Textbox(
                        label="Run log / status", lines=10, interactive=False
                    )
                    results_table = gr.Dataframe(
                        label="Ranked candidates",
                        headers=["candidate_id", "rank", "score", "reasoning"],
                        wrap=True,
                    )
                    csv_out = gr.File(label="Download ranked CSV", interactive=False)

            run_btn.click(
                fn=run_ranker,
                inputs=[file_input, top_n],
                outputs=[results_table, csv_out, status_box],
            )

            sample_btn.click(
                fn=make_sample_file,
                inputs=[],
                outputs=[sample_file_out, sample_status],
            )

        with gr.TabItem("About / Architecture"):
            gr.Markdown(ABOUT_MD)

if __name__ == "__main__":
    demo.launch()