#!/usr/bin/env python3
"""Recompute the DocVQA metric table from a predictions file.

Standalone: no DocAI imports. For the published file (results/predictions.jsonl)
it also fails (exit 1) if the recomputed numbers differ from the README, so the
table is checked, not asserted. For any other file it just prints the table.

Usage: python evaluate.py [results/predictions.jsonl | results/runs/<run-id>/predictions.jsonl]
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

import editdistance

PUBLISHED = {
    "total": 5349,
    "official_anls": 0.906554,
    "exact_ci": 4506,
    "exact_normalized": 4725,
    "coverage": 4981,        # internal_score >= 0.5
    "internal_anls": 0.921347,
}


def normalize(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    s = s.encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^\w\s]", " ", s.lower())
    return " ".join(s.split())


def normalize_ci(s: str) -> str:
    return " ".join((s or "").strip().lower().split())


def official_anls(pred: str, answers: list[str], threshold: float = 0.5) -> float:
    p = normalize(pred)
    best = 0.0
    for a in answers:
        g = normalize(a)
        ml = max(len(p), len(g))
        nls = 1.0 if ml == 0 else 1.0 - editdistance.eval(p, g) / ml
        best = max(best, nls)
    return best if best >= threshold else 0.0


def main(path: str) -> int:
    rows = [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]
    n = len(rows)
    got = {
        "total": n,
        "official_anls": round(sum(official_anls(r["pred"], r["answers"]) for r in rows) / n, 6),
        "exact_ci": sum(any(normalize_ci(r["pred"]) == normalize_ci(a) for a in r["answers"]) for r in rows),
        "exact_normalized": sum(any(normalize(r["pred"]) == normalize(a) for a in r["answers"]) for r in rows),
        "coverage": sum(r["internal_score"] >= 0.5 for r in rows),
        "internal_anls": round(sum(r["internal_score"] for r in rows) / n, 6),
    }
    print(f"questions                 {got['total']}")
    print(f"official ANLS             {got['official_anls']:.6f}")
    print(f"case-insensitive exact    {got['exact_ci']}  ({got['exact_ci']/n:.1%})")
    print(f"normalized exact          {got['exact_normalized']}  ({got['exact_normalized']/n:.1%})")
    print(f"exact + partial coverage  {got['coverage']}  ({got['coverage']/n:.1%})")
    print(f"internal ANLS             {got['internal_anls']:.6f}  (repair-loop scorer, not ANLS)")
    if Path(path).resolve() != Path("results/predictions.jsonl").resolve():
        return 0  # a new run: print the table, nothing to assert against
    bad = {k: (got[k], PUBLISHED[k]) for k in PUBLISHED if got[k] != PUBLISHED[k]}
    if bad:
        print(f"MISMATCH vs published: {bad}", file=sys.stderr)
        return 1
    print("all published values reproduced")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "results/predictions.jsonl"))
