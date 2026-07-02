"""
rank.py - Main entry point for the Redrob Candidate Ranker.

Usage:
    python rank.py --candidates candidates.jsonl --out submission.csv
"""
import argparse
import json
import time
import sys
import os

# Add project root to path so pipeline imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline.scorer import score_candidate
from pipeline.reasoning import build_reasoning
from pipeline.output import write_submission, validate_submission


def main():
    parser = argparse.ArgumentParser(description="Redrob Candidate Ranker")
    parser.add_argument("--candidates", required=True, help="Path to candidates.jsonl")
    parser.add_argument("--out", required=True, help="Output CSV path")
    parser.add_argument("--top", type=int, default=100, help="Number of top candidates (default 100)")
    args = parser.parse_args()

    t0 = time.time()

    # ── PHASE 1: Load + Score ────────────────────────────────────────────
    print(f"Reading candidates from: {args.candidates}")
    scored = []
    total = 0
    honeypot_count = 0
    no_match_count = 0

    with open(args.candidates, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            total += 1
            cand = json.loads(line)
            result = score_candidate(cand)

            if isinstance(result, dict):
                score = result["score"]
                matched_labels = []
                details = result
                tag = "no_career_match" if score == 0.0 else ""
            else:
                score = result[0]
                matched_labels = result[1]
                details = result[2]
                tag = matched_labels if score == 0.0 else ""

            if score > 0.0:
                scored.append((score, cand, matched_labels, details))
            else:
                if tag == "honeypot":
                    honeypot_count += 1
                elif tag == "no_career_match":
                    no_match_count += 1

            if total % 20000 == 0:
                print(f"  Scanned {total} candidates... ({len(scored)} scored)")

    t1 = time.time()
    print(f"\nPhase 1 complete in {t1 - t0:.2f}s")
    print(f"  Total candidates:     {total}")
    print(f"  Honeypots filtered:   {honeypot_count}")
    print(f"  No career match:      {no_match_count}")
    print(f"  Scored (non-zero):    {len(scored)}")

    # Deterministic: score DESC, candidate_id ASC
    # Round score to 4 decimal places to match output writer rounding
    scored.sort(key=lambda x: (-round(x[0], 4), x[1]["candidate_id"]))

    # ── PHASE 3: Generate Reasoning for Top N ────────────────────────────
    print(f"\nGenerating reasoning for top {args.top} candidates...")
    ranked_with_reasoning = []
    for score, cand, labels, details in scored[:args.top]:
        reasoning = build_reasoning(cand, details)
        ranked_with_reasoning.append((score, cand, labels, details, reasoning))

    # ── PHASE 4: Write Output ────────────────────────────────────────────
    write_submission(ranked_with_reasoning, args.out, top_n=args.top)

    # ── PHASE 5: Self-Validate ───────────────────────────────────────────
    validate_submission(args.out)

    t2 = time.time()
    print(f"\nTotal execution time: {t2 - t0:.2f}s")

    # Print top 5 for quick sanity check
    print("\n" + "=" * 60)
    print("TOP 5 CANDIDATES (quick preview)")
    print("=" * 60)
    for i, (score, cand, labels, details, reasoning) in enumerate(ranked_with_reasoning[:5], 1):
        p = cand["profile"]
        print(f"\n#{i}. {cand['candidate_id']} | Score: {score:.4f}")
        print(f"   {p['current_title']} | {p['years_of_experience']} yrs | {p['location']}")
        print(f"   Matched: {labels}")
        print(f"   Reasoning: {reasoning[:150]}...")


if __name__ == "__main__":
    main()
