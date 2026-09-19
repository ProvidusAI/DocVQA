#!/usr/bin/env python3
"""Compare two predictions files on their common question ids.
Usage: python scripts/compare_runs.py base.jsonl new.jsonl
"""
import json, sys
a = {r["question_id"]: r for r in map(json.loads, open(sys.argv[1], encoding="utf-8"))}
b = {r["question_id"]: r for r in map(json.loads, open(sys.argv[2], encoding="utf-8"))}
ids = sorted(set(a) & set(b))
rec = [i for i in ids if a[i]["official_score"] < 1 <= b[i]["official_score"]]
reg = [i for i in ids if b[i]["official_score"] < 1 <= a[i]["official_score"]]
ma = sum(a[i]["official_score"] for i in ids) / len(ids)
mb = sum(b[i]["official_score"] for i in ids) / len(ids)
nf = lambda d: sum(d[i]["pred"].strip().lower() == "not found" for i in ids)
print(f"common {len(ids)} | recovered {len(rec)} | regressed {len(reg)} | net {len(rec)-len(reg):+d}")
print(f"mean ANLS {ma:.4f} -> {mb:.4f} ({mb-ma:+.4f}) | not-found {nf(a)} -> {nf(b)}")
for i in reg[:15]:
    print(f"  REG {i}: {a[i]['pred']!r} -> {b[i]['pred']!r} | gold {a[i]['answers']}")
