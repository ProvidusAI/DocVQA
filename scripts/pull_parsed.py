#!/usr/bin/env python3
"""Pull parsed output for every DocVQA page from a DocAI knowledge base.

For each file named {docId}.png in the knowledge base, downloads the latest parse
manifest's result.md and grounding.json into <parsed-dir>/{img_hash}/, using the
docId -> img_hash mapping from results/predictions.jsonl. Writes
<parsed-dir>/_manifest.json with file ids, manifest ids and the run configuration
you pass in. Resumable: pages that already have both files are skipped.

Usage:
  export DOCAI_API_KEY=... DOCAI_BASE_URL=http://localhost:8080
  python scripts/pull_parsed.py --kb-id <id> --parsed-dir runs/<run-id>/parsed \
      --config "DocAI parsing pipeline; run 2026-09" [--workers 8] [--with-images]
Needs: requests
"""
import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

BASE = os.environ.get("DOCAI_BASE_URL", "https://api.providus.ai").rstrip("/")
HEADERS = {"x-api-key": os.environ.get("DOCAI_API_KEY", "")}


def get(path: str, **kw):
    r = requests.get(f"{BASE}{path}", headers=HEADERS, timeout=kw.pop("timeout", 120), **kw)
    r.raise_for_status()
    return r


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb-id", required=True)
    ap.add_argument("--parsed-dir", required=True)
    ap.add_argument("--config", required=True, help="human-readable model configuration for the manifest")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--with-images", action="store_true", help="also download the cropped figure images (large)")
    args = ap.parse_args()
    if not HEADERS["x-api-key"]:
        sys.exit("DOCAI_API_KEY is not set")

    hashes = {str(json.loads(l)["doc_id"]): json.loads(l)["img_hash"]
              for l in open("results/predictions.jsonl", encoding="utf-8")}
    files = [f for f in get(f"/v1/files?kb_id={args.kb_id}").json()["files"] if not f.get("deleted_at")]
    out = Path(args.parsed_dir)
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "_manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {"config": args.config, "base_url": BASE, "kb_id": args.kb_id, "pages": {}}

    def pull(f: dict) -> tuple[str, str]:
        doc_id = Path(f["filename"]).stem
        h = hashes.get(doc_id)
        if not h:
            return doc_id, "not in dataset"
        d = out / h
        if (d / "result.md").exists() and (d / "grounding.json").exists():
            return doc_id, "skipped"
        arts = [m for m in get(f"/v1/files/{f['id']}/artefacts").json()["artifacts"] if m["artifact_type"] == "parse"]
        if not arts:
            return doc_id, "no parse manifest"
        m = arts[0]
        links = m["links"]
        d.mkdir(parents=True, exist_ok=True)
        for key, name in (("result_md", "result.md"), ("grounding_json", "grounding.json")):
            if not links.get(key):
                return doc_id, f"missing {key}"
            (d / name).write_bytes(get(links[key]).content)
        if args.with_images and links.get("imgs"):
            listing = get(links["imgs"]).json()
            (d / "imgs").mkdir(exist_ok=True)
            for entry in listing.get("files", listing if isinstance(listing, list) else []):
                url = entry.get("url") if isinstance(entry, dict) else None
                if url:
                    (d / "imgs" / Path(url.split("file=")[-1]).name).write_bytes(get(url.replace(BASE, "")).content)
        manifest["pages"][h] = {"doc_id": doc_id, "file_id": f["id"], "manifest_id": m["id"], "job_id": m.get("job_id")}
        return doc_id, "pulled"

    counts: dict[str, int] = {}
    with ThreadPoolExecutor(args.workers) as pool:
        for i, (doc_id, status) in enumerate(pool.map(pull, files), 1):
            counts[status] = counts.get(status, 0) + 1
            if status not in ("pulled", "skipped"):
                print(f"{doc_id}: {status}", file=sys.stderr, flush=True)
            if i % 200 == 0:
                manifest_path.write_text(json.dumps(manifest, indent=1))
                print(f"{i}/{len(files)} {counts}", flush=True)
    manifest_path.write_text(json.dumps(manifest, indent=1))
    print(f"done: {counts} -> {out}")


if __name__ == "__main__":
    main()
