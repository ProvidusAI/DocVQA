#!/usr/bin/env python3
"""Derive results/predictions.jsonl from the DocAI locked campaign artifact.

Copies per-question fields verbatim. Edits nothing. Rows sorted by question_id
so the output is byte-identical on every run.

Usage: python scripts/derive_predictions.py <path-to-locked-json>
"""
import hashlib
import json
import sys
from pathlib import Path

EXPECTED_SHA256 = "c8e12ed12d203b586a66981c7b1cc6d573e793640e0dd6ec01280ac4563e8525"
KEEP = ["question_id", "doc_id", "img_hash", "question", "answers", "pred"]


def main(src: str) -> None:
    raw = Path(src).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_SHA256:
        sys.exit(f"source sha256 {digest} does not match the locked artifact")
    rows = json.loads(raw)["per_question"]
    out = Path("results/predictions.jsonl")
    with out.open("w", encoding="utf-8") as fh:
        for r in sorted(rows, key=lambda r: int(r["question_id"])):
            row = {k: r[k] for k in KEEP}
            row["official_score"] = float(r["official_score"])
            row["internal_score"] = float(r["score"])
            row["exact_ci"] = bool(r["exact_ci"])
            row["exact_normalized"] = bool(r["exact_normalized"])
            row["diagnostic"] = str(r.get("diagnostic") or "")
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    sums = Path("results/SHA256SUMS")
    sums.write_text(f"{hashlib.sha256(out.read_bytes()).hexdigest()}  predictions.jsonl\n")
    print(f"wrote {out} ({len(rows)} rows); source sha256 ok")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
