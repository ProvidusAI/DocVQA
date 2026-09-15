#!/usr/bin/env python3
"""Parse every DocVQA page image with the DocAI API, in two phases.

Phase 1 (queue): upload each image with auto_parse and record its file and job id
in parsed/_jobs.json. Uploads do not wait for parsing, so the worker queue stays
full. Phase 2 (collect): poll the recorded jobs, download result.md and
grounding.json into parsed/{img_hash}/. Both phases are resumable; run the script
again and it continues where it stopped.

    parsed/_jobs.json                 {img_hash: {doc_id, file_id, job_id, status}}
    parsed/{img_hash}/result.md
    parsed/{img_hash}/grounding.json

Usage:
  export DOCAI_API_KEY=...          # Settings > API Keys in the DocAI app
  export DOCAI_BASE_URL=https://api.providus.ai   # or your on-prem instance
  python scripts/parse_with_docai.py --kb-id <knowledge base id> [--doc-ids 1,2] [--limit N]
  python scripts/parse_with_docai.py --kb-id <id> --collect-only     # just poll and download
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


def load_jobs(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def save_jobs(path: Path, jobs: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(jobs, indent=1))


def queue(img_path: Path, kb_id: str) -> dict:
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
    return {"file_id": body["file"]["id"], "job_id": body["parse_job"]["job_id"], "status": "queued"}


def job_status(file_id: str, job_id: str) -> str:
    j = requests.get(f"{BASE}/v1/files/{file_id}/jobs/{job_id}", headers=HEADERS, timeout=60)
    j.raise_for_status()
    return j.json()["job"]["status"]


def download(file_id: str, out_dir: Path) -> str:
    a = requests.get(f"{BASE}/v1/files/{file_id}/artefacts", headers=HEADERS, timeout=60)
    a.raise_for_status()
    manifests = [m for m in a.json()["artifacts"] if m["artifact_type"] == "parse"]
    if not manifests:
        return "no parse manifest"
    links = manifests[0]["links"]
    out_dir.mkdir(parents=True, exist_ok=True)
    for key, name in (("result_md", "result.md"), ("grounding_json", "grounding.json")):
        if not links.get(key):
            return f"missing {key}"
        d = requests.get(f"{BASE}{links[key]}", headers=HEADERS, timeout=120)
        d.raise_for_status()
        (out_dir / name).write_bytes(d.content)
    return "completed"


def have_output(out_dir: Path) -> bool:
    return (out_dir / "result.md").exists() and (out_dir / "grounding.json").exists()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb-id", required=True)
    ap.add_argument("--dataset-dir", default="data/docvqa", help="data/docvqa or data/docvqa-test")
    ap.add_argument("--parsed-dir", default="parsed")
    ap.add_argument("--doc-ids", default=None, help="comma-separated docIds (default: all)")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--collect-only", action="store_true", help="skip uploads, poll recorded jobs")
    ap.add_argument("--poll", type=int, default=15, help="seconds between polling rounds")
    ap.add_argument("--max-wait", type=int, default=6 * 3600, help="give up collecting after this many seconds")
    args = ap.parse_args()
    if not HEADERS["x-api-key"]:
        sys.exit("DOCAI_API_KEY is not set")

    parsed = Path(args.parsed_dir)
    jobs_path = parsed / "_jobs.json"
    jobs = load_jobs(jobs_path)
    dataset = Path(args.dataset_dir)
    hashes = json.loads((dataset / "hashes.json").read_text())
    if args.doc_ids:
        wanted = set(args.doc_ids.split(","))
        hashes = {d: h for d, h in hashes.items() if d in wanted}
    items = sorted(hashes.items())[: args.limit] if args.limit else sorted(hashes.items())

    # Phase 1: queue
    if not args.collect_only:
        queued = 0
        for doc_id, img_hash in items:
            if have_output(parsed / img_hash) or img_hash in jobs:
                continue
            img_path = dataset / "images" / f"{doc_id}.png"
            try:
                jobs[img_hash] = {"doc_id": doc_id, **queue(img_path, kb_id=args.kb_id)}
                queued += 1
            except requests.HTTPError as exc:
                print(f"{doc_id}: upload failed http {exc.response.status_code}: {exc.response.text[:200]}",
                      file=sys.stderr, flush=True)
                if exc.response.status_code == 402:
                    save_jobs(jobs_path, jobs)
                    sys.exit("out of credits; stopping the queue phase")
            if queued % 25 == 0 and queued:
                save_jobs(jobs_path, jobs)
                print(f"queued {queued}", flush=True)
        save_jobs(jobs_path, jobs)
        print(f"queue phase done: {queued} new uploads, {len(jobs)} jobs tracked", flush=True)

    # Phase 2: collect
    pending = {h: j for h, j in jobs.items() if h in dict(items).values() or not args.doc_ids}
    pending = {h: j for h, j in pending.items() if not have_output(parsed / h) and j.get("status") not in {"failed", "cancelled"}}
    started = time.time()
    while pending and time.time() - started < args.max_wait:
        for h, j in list(pending.items()):
            try:
                status = job_status(j["file_id"], j["job_id"])
            except requests.HTTPError as exc:
                print(f"{j['doc_id']}: status http {exc.response.status_code}", file=sys.stderr, flush=True)
                continue
            if status not in TERMINAL:
                continue
            if status == "completed":
                status = download(j["file_id"], parsed / h)
            jobs[h]["status"] = status
            del pending[h]
            if status != "completed":
                print(f"{j['doc_id']} ({h}): {status}", file=sys.stderr, flush=True)
        save_jobs(jobs_path, jobs)
        done = sum(1 for h in jobs if have_output(parsed / h))
        failed = sum(1 for j in jobs.values() if j.get("status") in {"failed", "cancelled"} or str(j.get("status", "")).startswith(("missing", "no parse")))
        print(f"collected {done}, failed {failed}, pending {len(pending)}", flush=True)
        if pending:
            time.sleep(args.poll)
    if pending:
        print(f"stopped with {len(pending)} still pending; run again with --collect-only", file=sys.stderr)


if __name__ == "__main__":
    main()
