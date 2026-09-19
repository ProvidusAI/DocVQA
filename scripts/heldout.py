#!/usr/bin/env python3
"""Pick a fixed 300-question held-out set from a predictions file, stratified by outcome.
Usage: python scripts/heldout.py <predictions.jsonl> <parsed dir> <out.txt>
"""
import json, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluate import normalize

preds, parsed, out = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
rows = [json.loads(l) for l in open(preds, encoding="utf-8")]
def present(r):
    md = normalize((parsed / r["img_hash"] / "result.md").read_text(encoding="utf-8"))
    return any(normalize(a) and normalize(a) in md for a in r["answers"])
buckets = {
    "zero_gold_present": ([r for r in rows if r["official_score"] == 0 and present(r)], 120),
    "zero_gold_absent": ([r for r in rows if r["official_score"] == 0 and not present(r)], 40),
    "partial": ([r for r in rows if 0 < r["official_score"] < 1], 40),
    "correct": ([r for r in rows if r["official_score"] >= 1], 100),
}
random.seed(2026)
ids = []
for name, (pool, n) in buckets.items():
    ids += [r["question_id"] for r in random.sample(pool, n)]
    print(f"{name:18s} {n:4d} of {len(pool)}")
Path(out).write_text("\n".join(ids) + "\n")
assert len(set(ids)) == 300
print(f"wrote {out}")
