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

TARGET_CITIES = ["Pune", "Noida", "Delhi", "Gurugram", "Hyderabad", "Mumbai", "Bengaluru"]
POSITIVE_SKILLS = ["embeddings", "vector search", "faiss", "rag", "nlp", "transformers", "search ranking"]
NEGATIVE_SKILLS = ["computer vision", "robotics", "reinforcement learning (robotics)"]
COMPANIES = ["Search Labs AI", "VectorForge", "NeuralIndex", "InfoRetriever Inc",
             "TCS", "Infosys", "SemanticStack", "RankWorks"]
TITLES = ["ML Engineer", "NLP Engineer", "Search Engineer", "Applied Scientist",
          "Data Scientist", "Backend Engineer", "Software Engineer"]


# --------------------------------------------------------------------------
# Sample data generation (for users without a real dataset to test with)
# --------------------------------------------------------------------------

def _random_candidate(idx: int) -> dict:
    total_exp = round(random.uniform(1, 14), 1)
    n_roles = random.randint(1, 4)
    careers = []
    years_left = total_exp
    for i in range(n_roles):
        dur = round(min(years_left, random.uniform(0.5, 4.0)), 1)
        years_left = max(0.0, years_left - dur)
        careers.append({
            "company": random.choice(COMPANIES),
            "title": random.choice(TITLES),
            "duration_years": dur,
            "is_current": i == 0,
            "description": random.choice([
                "Deployed and launched a production RAG search pipeline using embeddings and faiss.",
                "Built and A/B tested a vector search ranking model.",
                "Worked on internal tooling and support tickets.",
                "Researched robotics perception using computer vision.",
            ]),
        })

    skills = {}
    for s in random.sample(POSITIVE_SKILLS, k=random.randint(1, 4)):
        skills[s] = {
            "proficiency": random.choice(["beginner", "intermediate", "expert"]),
            "duration_months": random.randint(0, 48),
            "endorsements": random.randint(0, 20),
            "assessment_score": random.randint(20, 100),
        }
    for s in random.sample(NEGATIVE_SKILLS, k=random.randint(0, 2)):
        skills[s] = {
            "proficiency": "intermediate",
            "duration_months": random.randint(0, 24),
            "endorsements": random.randint(0, 10),
            "assessment_score": random.randint(20, 100),
        }

    return {
        "candidate_id": f"C{idx:04d}",
        "name": f"Candidate {idx}",
        "total_experience_years": total_exp,
        "career": careers,
        "skills": skills,
        "current_location": random.choice(TARGET_CITIES + ["London", "San Francisco", "Singapore"]),
        "willing_to_relocate": random.choice([True, False]),
        "graduation_year": datetime.now().year - int(total_exp) - random.randint(0, 2),
        "days_since_last_active": random.randint(0, 120),
        "recruiter_response_rate": round(random.uniform(0, 1), 2),
        "open_to_work": random.choice([True, False]),
        "interview_completion_rate": round(random.uniform(0, 1), 2),
        "notice_period_days": random.choice([0, 15, 30, 60, 90]),
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

def run_ranker(candidates_file, top_n):
    """Invoke rank.py as a subprocess and load the resulting CSV."""
    if candidates_file is None:
        return None, None, "⚠️ Please upload a candidates .jsonl file first (or generate a sample)."

    if not os.path.exists(RANK_SCRIPT):
        return None, None, (
            "❌ Could not find rank.py next to app.py.\n"
            "Make sure rank.py, config.py, and the pipeline/ package are uploaded "
            "alongside this app.py in the Space repo."
        )

    in_path = candidates_file.name if hasattr(candidates_file, "name") else candidates_file
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

    log = f"$ {' '.join(cmd)}\n\n--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}"

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
                        label="Candidates file (.jsonl)",
                        file_types=[".jsonl"],
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