#!/usr/bin/env python3
"""Turn a run's predictions into the RRC portal submission file for DocVQA Task 1.

Portal format (rrc.cvc.uab.es, challenge 17, Task 1): one JSON list, one object
per test question, keys "questionId" (int) and "answer" (str). Every test question
must be present; missing ones are written with an empty answer and counted.

Usage: python scripts/make_submission.py results/runs/<run-id>/predictions.jsonl \
           --annotations data/docvqa-test/annotations.jsonl --out results/runs/<run-id>/result_task1.json
"""
import argparse
import json
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("predictions")
    ap.add_argument("--annotations", default="data/docvqa-test/annotations.jsonl")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    preds = {}
    for line in Path(args.predictions).open(encoding="utf-8"):
        r = json.loads(line)
        preds[str(r["question_id"])] = r["pred"]

    rows, missing = [], 0
    for line in Path(args.annotations).open(encoding="utf-8"):
        q = json.loads(line)
        qid = str(q["questionId"])
        if qid not in preds:
            missing += 1
        answer = preds.get(qid, "")
        if answer.strip().lower() == "not found":
            answer = ""
        rows.append({"questionId": int(qid), "answer": answer})

    Path(args.out).write_text(json.dumps(rows, ensure_ascii=False))
    print(f"wrote {args.out}: {len(rows)} questions, {missing} without a prediction")


if __name__ == "__main__":
    main()
