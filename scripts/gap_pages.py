#!/usr/bin/env python3
"""Pages where a zero-score answer is not in the markdown, excluding a skip list.
Usage: python scripts/gap_pages.py preds.jsonl parsed_dir skip_ids.txt > gap_pages.txt
"""
import json, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluate import normalize
preds, parsed, skip = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
skipped = {l.split("\t")[0].strip().removesuffix(".png") for l in open(skip) if l.strip() and not l.startswith("#")}
gaps = Counter(); mdlen = {}; examples = {}
for l in open(preds, encoding="utf-8"):
    r = json.loads(l)
    if r["official_score"] > 0 or str(r["doc_id"]) in skipped: continue
    md = (parsed / r["img_hash"] / "result.md").read_text(encoding="utf-8")
    if any(normalize(a) and normalize(a) in normalize(md) for a in r["answers"]): continue
    d = str(r["doc_id"]); gaps[d] += 1; mdlen[d] = len(md); examples.setdefault(d, r["answers"][0])
print("# doc_id\tgap_questions\tmd_chars\texample_gold")
for d, n in gaps.most_common():
    print(f"{d}\t{n}\t{mdlen[d]}\t{examples[d]}")
print(f"# {sum(gaps.values())} gap questions on {len(gaps)} pages", file=sys.stderr)
