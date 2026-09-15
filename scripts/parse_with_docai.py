#!/usr/bin/env python3
"""Parse every DocVQA page image with the DocAI API.

For each image: upload with auto_parse, wait for the parse job, download the
markdown and the grounding JSON into parsed/{img_hash}/. Safe to re-run; documents
that already have both files are skipped.

    parsed/{img_hash}/result.md
    parsed/{img_hash}/grounding.json

Usage:
  export DOCAI_API_KEY=...          # Settings > API Keys in the DocAI app
  export DOCAI_BASE_URL=https://api.providus.ai   # or your on-prem instance
  python scripts/parse_with_docai.py --kb-id <knowledge base id> [--data-dir data] [--limit N]
Needs: pip install requests
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

BASE = os.environ.get("DOCAI_BASE_URL", "https://api.providus.ai").rstrip("/")
HEADERS = {"x-api-key": os.environ.get("DOCAI_API_KEY", "")}
TERMINAL = {"completed", "failed", "cancelled"}


def parse_one(img_path: Path, kb_id: str, out_dir: Path, timeout_s: int) -> str:
    with img_path.open("rb") as fh:
        r = requests.post(
            f"{BASE}/v1/files",
            headers=HEADERS,
            files={"file": (img_path.name, fh, "image/png")},
            data={"kb_id": kb_id, "auto_parse": "true"},
            timeout=120,
        )
    r.raise_for_status()
    body = r.json()
    file_id = body["file"]["id"]
    job_id = body["parse_job"]["job_id"]

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        j = requests.get(f"{BASE}/v1/files/{file_id}/jobs/{job_id}", headers=HEADERS, timeout=60)
        j.raise_for_status()
        status = j.json()["job"]["status"]
        if status in TERMINAL:
            break
        time.sleep(5)
    else:
        return "timeout"
    if status != "completed":
        return status

    a = requests.get(f"{BASE}/v1/files/{file_id}/artefacts", headers=HEADERS, timeout=60)
    a.raise_for_status()
    parse_manifests = [m for m in a.json()["artifacts"] if m["artifact_type"] == "parse"]
    links = parse_manifests[0]["links"]
    out_dir.mkdir(parents=True, exist_ok=True)
    for key, name in (("result_md", "result.md"), ("grounding_json", "grounding.json")):
        if not links.get(key):
            return f"missing {key}"
        d = requests.get(f"{BASE}{links[key]}", headers=HEADERS, timeout=120)
        d.raise_for_status()
        (out_dir / name).write_bytes(d.content)
    return "completed"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb-id", required=True)
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--parsed-dir", default="parsed")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--doc-ids", default=None, help="comma-separated docIds to parse (default: all)")
    ap.add_argument("--timeout", type=int, default=900, help="seconds to wait per document")
    args = ap.parse_args()
    if not HEADERS["x-api-key"]:
        sys.exit("DOCAI_API_KEY is not set")

    hashes = json.loads((Path(args.data_dir) / "docvqa" / "hashes.json").read_text())
    if args.doc_ids:
        wanted = set(args.doc_ids.split(","))
        hashes = {d: h for d, h in hashes.items() if d in wanted}
    items = sorted(hashes.items())[: args.limit] if args.limit else sorted(hashes.items())
    done = failed = skipped = 0
    for doc_id, img_hash in items:
        out_dir = Path(args.parsed_dir) / img_hash
        if (out_dir / "result.md").exists() and (out_dir / "grounding.json").exists():
            skipped += 1
            continue
        img_path = Path(args.data_dir) / "docvqa" / "images" / f"{doc_id}.png"
        try:
            status = parse_one(img_path, args.kb_id, out_dir, args.timeout)
        except requests.HTTPError as exc:
            status = f"http {exc.response.status_code}: {exc.response.text[:200]}"
        if status == "completed":
            done += 1
        else:
            failed += 1
            print(f"{doc_id} ({img_hash}): {status}", file=sys.stderr, flush=True)
        if (done + failed) % 25 == 0:
            print(f"parsed {done}, failed {failed}, skipped {skipped}", flush=True)
    print(f"done: parsed {done}, failed {failed}, skipped {skipped}")


if __name__ == "__main__":
    main()
