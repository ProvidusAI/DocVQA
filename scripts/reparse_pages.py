#!/usr/bin/env python3
"""Delete, re-upload and re-parse chosen DocVQA pages, then compare old and new output.

Usage:
  export DOCAI_API_KEY=... DOCAI_BASE_URL=http://localhost:8080
  python scripts/reparse_pages.py --kb-id <kb> --run-dir runs/<run> --ids-file ids.txt --dataset-dir <dir>          # stage + report
  python scripts/reparse_pages.py --kb-id <kb> --run-dir runs/<run> --ids-file ids.txt --dataset-dir <dir> --apply  # copy into parsed/
ids.txt: one doc id per line ("1085" or "1085.png", extra tab columns ignored, # comments skipped).
Parse options go with the upload; the worker env supplies the vision model.
"""
import argparse, json, os, shutil, sys, time
from pathlib import Path
import requests
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluate import normalize

BASE = os.environ.get("DOCAI_BASE_URL", "http://localhost:8080").rstrip("/")
H = {"x-api-key": os.environ.get("DOCAI_API_KEY", "")}
OPTIONS = {"backend": "ocr-model", "redact": False}


def req(method, path, **kw):
    r = requests.request(method, f"{BASE}{path}", headers=H, timeout=kw.pop("timeout", 120), **kw)
    r.raise_for_status()
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb-id", required=True)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--ids-file", required=True)
    ap.add_argument("--dataset-dir", default="data/docvqa", help="has images/ and annotations.jsonl")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--poll", type=int, default=15)
    ap.add_argument("--collect-only", action="store_true", help="skip delete/upload; poll the latest parse job of each page")
    a = ap.parse_args()
    if not H["x-api-key"]:
        sys.exit("DOCAI_API_KEY is not set")
    run = Path(a.run_dir); parsed = run / "parsed"; staging = run / "reparse-staging"
    manifest_path = parsed / "_manifest.json"; manifest = json.loads(manifest_path.read_text())
    hashes = {str(json.loads(l)["doc_id"]): json.loads(l)["img_hash"] for l in open("results/predictions.jsonl", encoding="utf-8")}
    ids = [l.split("\t")[0].strip().removesuffix(".png") for l in open(a.ids_file) if l.strip() and not l.startswith("#")]
    ann = {}
    for l in open(Path(a.dataset_dir) / "annotations.jsonl", encoding="utf-8"):
        r = json.loads(l); ann.setdefault(str(r["docId"]), []).append(r["answers"])

    def gold_present(md, doc_id):
        n = normalize(md)
        return sum(any(normalize(x) and normalize(x) in n for x in answers) for answers in ann.get(doc_id, []))

    if a.apply:
        for doc_id in ids:
            h = hashes[doc_id]; src = staging / h
            if not (src / "result.md").exists():
                print(f"{doc_id}: nothing staged", file=sys.stderr); continue
            for name in ("result.md", "grounding.json"):
                shutil.copy(src / name, parsed / h / name)
            manifest["pages"][h].update(json.loads((src / "_ids.json").read_text()))
        both = "vision vision-model, vision-model on low-yield pages"
        if both not in manifest["config"]:
            manifest["config"] = manifest["config"].replace("vision vision-model", both)
        manifest_path.write_text(json.dumps(manifest, indent=1))
        shutil.rmtree(staging, ignore_errors=True)
        print(f"applied {len(ids)} pages into {parsed}"); return

    files = {Path(f["filename"]).stem: f for f in req("GET", f"/v1/files?kb_id={a.kb_id}&limit=2000").json()["files"] if not f.get("deleted_at")}
    jobs = {}
    for doc_id in ids:
        old = files.get(doc_id)
        if a.collect_only:
            js = [j for j in req("GET", f"/v1/files/{old['id']}/jobs").json()["jobs"] if j.get("kind", "parse") == "parse"]
            jobs[doc_id] = (old["id"], max(js, key=lambda j: j["created_at"])["id"])
            continue
        if old:
            req("DELETE", f"/v1/files/{old['id']}")
        with open(Path(a.dataset_dir) / "images" / f"{doc_id}.png", "rb") as fh:
            body = req("POST", "/v1/files", files={"file": (f"{doc_id}.png", fh, "image/png")},
                       data={"kb_id": a.kb_id, "auto_parse": "true", "parse_options": json.dumps(OPTIONS)}).json()
        jobs[doc_id] = (body["file"]["id"], body["parse_job"]["job_id"])
    print(f"queued {len(jobs)}", flush=True)

    pending = dict(jobs)
    while pending:
        time.sleep(a.poll)
        for doc_id, (fid, jid) in list(pending.items()):
            st = req("GET", f"/v1/files/{fid}/jobs/{jid}").json()["job"]["status"]
            if st in ("completed", "failed", "cancelled"):
                pending.pop(doc_id)
                if st != "completed":
                    print(f"{doc_id}: {st}", file=sys.stderr, flush=True)
        print(f"pending {len(pending)}", flush=True)

    rows = []
    for doc_id, (fid, jid) in jobs.items():
        h = hashes[doc_id]; d = staging / h; d.mkdir(parents=True, exist_ok=True)
        arts = [m for m in req("GET", f"/v1/files/{fid}/artefacts").json()["artifacts"] if m["artifact_type"] == "parse"]
        if not arts:
            rows.append((doc_id, "no manifest", 0, 0, 0, 0)); continue
        links = arts[0]["links"]
        for key, name in (("result_md", "result.md"), ("grounding_json", "grounding.json")):
            (d / name).write_bytes(req("GET", links[key]).content)
        (d / "_ids.json").write_text(json.dumps({"file_id": fid, "manifest_id": arts[0]["id"], "job_id": jid}))
        old_md = (parsed / h / "result.md").read_text(encoding="utf-8"); new_md = (d / "result.md").read_text(encoding="utf-8")
        rows.append((doc_id, "ok", len(old_md), len(new_md), gold_present(old_md, doc_id), gold_present(new_md, doc_id)))
    with (run / "reparse-report.tsv").open("a") as fh:
        for r in rows:
            fh.write("\t".join(map(str, r)) + "\n")
    print(f"{'doc':>6} {'status':10} {'chars':>7}->{'chars':<7} {'gold':>4}->{'gold':<4}")
    for doc_id, st, oc, nc, og, ng in rows:
        print(f"{doc_id:>6} {st:10} {oc:7d}->{nc:<7d} {og:4d}->{ng:<4d}")
    better = sum(ng > og for *_, og, ng in rows); same = sum(ng == og for *_, og, ng in rows)
    print(f"gold-present improved on {better}, unchanged on {same}, worse on {len(rows)-better-same}")


if __name__ == "__main__":
    main()
