"""
pipeline/output.py
CSV exporter with deterministic tie-breaking and format validation.
"""
import csv
import os


def write_submission(ranked: list, out_path: str, top_n: int = 100):
    """
    Write the final submission CSV.

    Parameters
    ----------
    ranked : list of tuples
        Each tuple: (score, candidate_dict, matched_labels, details, reasoning_str)
        Must already be sorted by score DESC, candidate_id ASC.
    out_path : str
        Path for the output CSV file.
    top_n : int
        Number of candidates to include (default 100).
    """
    # Ensure we only take top_n
    top = ranked[:top_n]

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])

        for rank_idx, (score, cand, _labels, _details, reasoning) in enumerate(top, 1):
            cid = cand["candidate_id"]
            writer.writerow([cid, rank_idx, round(score, 4), reasoning])

    print(f"\nSubmission written to: {out_path}")
    print(f"  Rows: {len(top)}")


def validate_submission(out_path: str) -> bool:
    """
    Quick self-check of the output CSV.
    Returns True if the file passes all checks.
    """
    if not os.path.exists(out_path):
        print(f"FAIL: File {out_path} does not exist.")
        return False

    with open(out_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    errors = []

    # 1. Check header
    expected = {"candidate_id", "rank", "score", "reasoning"}
    if set(reader.fieldnames) != expected:
        errors.append(f"Header mismatch: got {reader.fieldnames}, expected {sorted(expected)}")

    # 2. Check row count
    if len(rows) != 100:
        errors.append(f"Row count: {len(rows)} (expected 100)")

    # 3. Check unique candidate_ids
    cids = [r["candidate_id"] for r in rows]
    if len(set(cids)) != len(cids):
        errors.append(f"Duplicate candidate_ids found")

    # 4. Check ranks are 1-100
    ranks = [int(r["rank"]) for r in rows]
    if ranks != list(range(1, len(rows) + 1)):
        errors.append(f"Ranks are not sequential 1..{len(rows)}")

    # 5. Check scores are monotonically non-increasing
    scores = [float(r["score"]) for r in rows]
    for i in range(1, len(scores)):
        if scores[i] > scores[i - 1]:
            errors.append(f"Score not monotonically decreasing at rank {i+1}")
            break

    # 6. Check reasoning not empty
    empty_reasoning = [r["rank"] for r in rows if not r["reasoning"].strip()]
    if empty_reasoning:
        errors.append(f"Empty reasoning at ranks: {empty_reasoning[:5]}")

    if errors:
        print("\nVALIDATION FAILED:")
        for e in errors:
            print(f"  - {e}")
        return False
    else:
        print("\nVALIDATION PASSED: All checks OK.")
        print(f"  100 unique candidates, ranks 1-100, scores descending, reasoning present.")
        return True
