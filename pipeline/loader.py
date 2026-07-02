import json
from tqdm import tqdm

def load_candidates(path: str) -> list:
    candidates = []
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for line in tqdm(lines, desc="Loading candidates"):
        line = line.strip()
        if line:
            candidates.append(json.loads(line))
    print(f"Loaded {len(candidates)} candidates from {path}")
    return candidates

def load_sample(path: str, n: int = 10) -> list:
    candidates = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= n:
                break
            line = line.strip()
            if line:
                candidates.append(json.loads(line))
    print(f"Loaded {len(candidates)} sample candidates")
    return candidates
