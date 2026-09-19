#!/usr/bin/env python3
"""Answer every DocVQA question from the parsed markdown alone, then score.

One configuration, one pass. The QA model gets prompt.md as the system prompt and
the full result.md of the page as context. It never sees the image. Output has the
same shape as results/predictions.jsonl so evaluate.py can score it.

Usage:
  export QA_API_KEY=...                       # OpenAI-compatible endpoint key
  export QA_BASE_URL=https://api.openai.com/v1
  python scripts/run_qa.py --model openai/gpt-5.6-luna --run-id luna-baseline \
      [--dataset-dir data/docvqa] [--parsed-dir parsed] [--limit N] [--workers 4]
  python evaluate.py results/runs/luna-baseline/predictions.jsonl
Needs: pip install requests editdistance
"""
import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluate import normalize, normalize_ci, official_anls  # noqa: E402

BASE = os.environ.get("QA_BASE_URL", "https://api.openai.com/v1").rstrip("/")
KEY = os.environ.get("QA_API_KEY", "")
NOT_FOUND = "not found"


class TransientError(Exception):
    pass


class PermanentError(Exception):
    pass


def ask(model: str, system: str, question: str, document: str, max_tokens: int, reasoning: str) -> str:
    user = f"Question: {question}\n\nDocument (markdown):\n{document}"
    r = requests.post(
        f"{BASE}/chat/completions",
        headers={"Authorization": f"Bearer {KEY}", "content-type": "application/json"},
        json={
            # OpenAI's GPT-5-era models reject max_tokens and a pinned temperature;
            # the plain model id has no "openai/" prefix (that prefix is DocAI's role alias).
            "model": model.split("/", 1)[1] if model.startswith("openai/") else model,
            "max_completion_tokens": max_tokens,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            # Without this, GPT-5-era models spend the whole completion budget on hidden
            # reasoning and return an empty answer (finish_reason=length, content="").
            **({"reasoning_effort": reasoning} if reasoning != "none" else {}),
        },
        timeout=180,
    )
    if r.status_code in (429, 500, 502, 503, 504):
        raise TransientError(f"{r.status_code}: {r.text[:200]}")
    if r.status_code >= 400:
        raise PermanentError(f"{r.status_code}: {r.text[:300]}")
    text = r.json()["choices"][0]["message"]["content"] or ""
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        try:
            return str(json.loads(m.group(0)).get("answer", "")).strip()
        except json.JSONDecodeError:
            pass
    return text.strip().strip('"')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--dataset-dir", default="data/docvqa", help="data/docvqa or data/docvqa-test")
    ap.add_argument("--parsed-dir", default="parsed")
    ap.add_argument("--prompt", default="prompt.md")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--ids-file", default=None, help="only these question ids, one per line")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--max-tokens", type=int, default=256)
    ap.add_argument("--reasoning", default="low", choices=["none", "minimal", "low", "medium", "high"],
                    help="reasoning_effort sent to OpenAI-compatible endpoints; none omits the field")
    args = ap.parse_args()
    if not KEY:
        sys.exit("QA_API_KEY is not set")

    prompt_md = Path(args.prompt).read_text(encoding="utf-8")
    m = re.search(r"```text\n(.*?)```", prompt_md, re.S)
    system = m.group(1).strip() if m else prompt_md

    rows = [json.loads(l) for l in (Path(args.dataset_dir) / "annotations.jsonl").open(encoding="utf-8")]
    # Annotations written by other downloaders carry no img_hash; take it from the
    # published predictions (docId -> img_hash) so parsed/{img_hash} resolves.
    if rows and "img_hash" not in rows[0]:
        by_doc = {str(json.loads(l)["doc_id"]): json.loads(l)["img_hash"]
                  for l in open("results/predictions.jsonl", encoding="utf-8")}
        for r in rows:
            r["img_hash"] = by_doc.get(str(r["docId"]), "")
    if args.ids_file:
        keep = {l.strip() for l in open(args.ids_file) if l.strip()}
        rows = [r for r in rows if str(r["questionId"]) in keep]
    if args.limit:
        rows = rows[: args.limit]

    out_dir = Path("results") / "runs" / args.run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "predictions.jsonl"
    done_ids = set()
    if out_path.exists():
        kept = []
        for l in out_path.open(encoding="utf-8"):
            rec = json.loads(l)
            if rec["diagnostic"] == "api_error":
                continue  # re-ask these on resume
            kept.append(l)
            done_ids.add(rec["question_id"])
        out_path.write_text("".join(kept), encoding="utf-8")
    todo = [r for r in rows if r["questionId"] not in done_ids]

    def work(row: dict) -> dict:
        md_path = Path(args.parsed_dir) / row["img_hash"] / "result.md"
        if md_path.exists():
            pred, diagnostic = "", "api_error"
            for attempt in range(4):
                try:
                    pred = ask(args.model, system, row["question"], md_path.read_text(encoding="utf-8"), args.max_tokens, args.reasoning)
                    diagnostic = "answered"
                    break
                except (TransientError, requests.RequestException) as exc:
                    time.sleep(2 ** attempt)
                    err = str(exc)
                except PermanentError as exc:
                    err = str(exc)
                    if "max_tokens or model output limit" in err and attempt == 0:
                        # The cap was spent on reasoning; OpenAI reports that as a 400.
                        # One retry with four times the budget resolves it in practice.
                        try:
                            pred = ask(args.model, system, row["question"], md_path.read_text(encoding="utf-8"), args.max_tokens * 4, args.reasoning)
                            diagnostic = "answered"
                        except Exception as exc2:
                            err = str(exc2)
                    break
            if diagnostic == "api_error":
                with (out_dir / "errors.jsonl").open("a", encoding="utf-8") as ef:
                    ef.write(json.dumps({"question_id": row["questionId"], "doc_id": row["docId"], "error": err}) + "\n")
                print(f"api error on question {row['questionId']} (doc {row['docId']}): {err[:160]}", file=sys.stderr, flush=True)
        else:
            pred, diagnostic = NOT_FOUND, "parse_missing"
        score = official_anls(pred, row["answers"])
        if score >= 1.0:
            diagnostic = "exact"
        return {
            "question_id": row["questionId"],
            "doc_id": int(row["docId"]),
            "img_hash": row["img_hash"],
            "question": row["question"],
            "answers": row["answers"],
            "pred": pred,
            "official_score": round(score, 4),
            "internal_score": round(score, 4),
            "exact_ci": any(normalize_ci(pred) == normalize_ci(a) for a in row["answers"]),
            "exact_normalized": any(normalize(pred) == normalize(a) for a in row["answers"]),
            "diagnostic": diagnostic,
        }

    with out_path.open("a", encoding="utf-8") as fh, ThreadPoolExecutor(args.workers) as pool:
        for i, result in enumerate(pool.map(work, todo), 1):
            fh.write(json.dumps(result, ensure_ascii=False) + "\n")
            fh.flush()
            if i % 100 == 0:
                print(f"{i}/{len(todo)}", flush=True)

    (out_dir / "run.json").write_text(json.dumps({
        "run_id": args.run_id, "qa_model": args.model, "qa_base_url": BASE,
        "prompt": args.prompt, "max_tokens": args.max_tokens, "reasoning_effort": args.reasoning, "questions": len(rows),
    }, indent=1))
    print(f"wrote {out_path}; score it with: python evaluate.py {out_path}")


if __name__ == "__main__":
    main()
