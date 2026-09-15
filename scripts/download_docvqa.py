#!/usr/bin/env python3
"""Download the DocVQA validation split into data/docvqa/.

Writes one PNG per document plus the question file, and a docId -> img_hash map
so parse output folders line up with results/predictions.jsonl.

    data/docvqa/
      annotations.jsonl   5,349 rows: questionId, question, answers, docId
      images/{docId}.png  1,285 page images
      hashes.json         {docId: img_hash}

Usage: python scripts/download_docvqa.py [--data-dir data] [--limit N]
Needs: pip install datasets pillow   (about 1 GB of download)
"""
import argparse
import hashlib
import io
import json
from pathlib import Path


def image_hash(png_bytes: bytes) -> str:
    """Same 12-char md5 prefix the campaign used for img_hash."""
    return hashlib.md5(png_bytes).hexdigest()[:12]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--limit", type=int, default=None, help="first N questions only")
    args = ap.parse_args()

    from datasets import load_dataset

    out = Path(args.data_dir) / "docvqa"
    img_dir = out / "images"
    img_dir.mkdir(parents=True, exist_ok=True)

    ds = load_dataset("lmms-lab/DocVQA", "DocVQA", split="validation")
    if args.limit:
        ds = ds.select(range(min(args.limit, len(ds))))

    hashes: dict[str, str] = {}
    with (out / "annotations.jsonl").open("w", encoding="utf-8") as ann:
        for i, row in enumerate(ds, 1):
            doc_id = str(row["docId"])
            img_path = img_dir / f"{doc_id}.png"
            if doc_id not in hashes:
                if img_path.exists():
                    png = img_path.read_bytes()
                else:
                    buf = io.BytesIO()
                    row["image"].save(buf, format="PNG")
                    png = buf.getvalue()
                    img_path.write_bytes(png)
                hashes[doc_id] = image_hash(png)
            ann.write(json.dumps({
                "questionId": str(row["questionId"]),
                "question": row["question"],
                "answers": list(row["answers"]),
                "docId": doc_id,
                "img_hash": hashes[doc_id],
            }, ensure_ascii=False) + "\n")
            if i % 500 == 0:
                print(f"{i}/{len(ds)} questions, {len(hashes)} images", flush=True)

    (out / "hashes.json").write_text(json.dumps(hashes, indent=1))
    print(f"done: {len(ds)} questions, {len(hashes)} images in {out}")


if __name__ == "__main__":
    main()
