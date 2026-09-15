#!/usr/bin/env python3
"""Build the evidence gallery: for a few DocVQA pages, draw the grounding element
that carries the answer on the page image and collect the question, answer and
markdown excerpt into GALLERY.md.

Inputs: data/docvqa/ (images, annotations), parsed/{img_hash}/ (result.md,
grounding.json from the DocAI API), results/predictions.jsonl (which question to
show: the first one the campaign answered exactly).

Usage: python scripts/build_gallery.py --doc-ids 14465,5238 [--out assets/gallery]
Needs: pillow
"""
import argparse
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw

BLUE = (109, 187, 255)


def norm(s: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", (s or "").lower()).split())


def find_element(grounding: dict, answer: str) -> dict | None:
    """First element whose text contains the answer (normalized). Tables are
    searched cell by cell so the box is the cell, not the whole table."""
    target = norm(answer)
    best = None
    for page in grounding.get("pages", []):
        for el in page.get("elements", []):
            for cell in el.get("cells") or []:
                if target and target in norm(cell.get("text", "")) and cell.get("bbox"):
                    return {"bbox": cell["bbox"], "text": cell["text"], "label": "table cell",
                            "page": page.get("page_number", 1)}
            text = norm(el.get("content") or el.get("text") or "")
            if target and target in text:
                cand = {"bbox": el.get("bbox"), "text": el.get("content") or el.get("text"),
                        "label": el.get("label", ""), "page": page.get("page_number", 1)}
                if best is None or len(text) < len(norm(best["text"])):
                    best = cand
    return best


def to_pixels(bbox, w: int, h: int) -> tuple[int, int, int, int]:
    if isinstance(bbox, dict):
        x1, y1, x2, y2 = bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]
    else:
        x1, y1, x2, y2 = bbox
    if max(x1, y1, x2, y2) <= 1.5:  # normalized
        return int(x1 * w), int(y1 * h), int(x2 * w), int(y2 * h)
    return int(x1), int(y1), int(x2), int(y2)


def excerpt(md: str, answer: str, width: int = 240) -> str:
    i = md.lower().find(answer.lower())
    if i < 0:
        i = 0
    start = max(0, i - width // 2)
    return md[start : start + width].replace("\n", " ").strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc-ids", required=True)
    ap.add_argument("--out", default="assets/gallery")
    ap.add_argument("--max-width", type=int, default=900)
    args = ap.parse_args()

    hashes = json.loads(Path("data/docvqa/hashes.json").read_text())
    preds = [json.loads(l) for l in open("results/predictions.jsonl", encoding="utf-8")]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cards = []

    for doc_id in args.doc_ids.split(","):
        h = hashes[doc_id]
        pdir = Path("parsed") / h
        rows = [r for r in preds if str(r["doc_id"]) == doc_id]
        exact = [r for r in rows if r["official_score"] == 1.0] or rows
        grounding = json.loads((pdir / "grounding.json").read_text(encoding="utf-8"))
        md = (pdir / "result.md").read_text(encoding="utf-8")

        chosen, el = None, None
        for r in exact:  # pick the first exact answer we can locate in the parse output
            el = find_element(grounding, r["pred"])
            if el and el.get("bbox"):
                chosen = r
                break
        if not chosen:
            chosen, el = exact[0], None

        img = Image.open(Path("data/docvqa/images") / f"{doc_id}.png").convert("RGB")
        if el and el.get("bbox"):
            x1, y1, x2, y2 = to_pixels(el["bbox"], *img.size)
            d = ImageDraw.Draw(img)
            for k in range(4):
                d.rectangle([x1 - k, y1 - k, x2 + k, y2 + k], outline=BLUE)
        if img.width > args.max_width:
            img = img.resize((args.max_width, int(img.height * args.max_width / img.width)))
        img_path = out / f"{doc_id}.png"
        img.save(img_path, optimize=True)

        cards.append({
            "doc_id": doc_id, "img_hash": h, "question": chosen["question"], "answer": chosen["pred"],
            "gold": chosen["answers"], "image": str(img_path), "element_label": (el or {}).get("label"),
            "element_text": (el or {}).get("text"), "excerpt": excerpt(md, chosen["pred"]),
            "located": bool(el and el.get("bbox")),
        })
        print(f"{doc_id}: {'box drawn' if cards[-1]['located'] else 'answer not located in grounding'} | {chosen['question'][:60]} -> {chosen['pred'][:40]}")

    (out / "cards.json").write_text(json.dumps(cards, indent=1, ensure_ascii=False))
    print(f"wrote {len(cards)} cards to {out}/cards.json")


if __name__ == "__main__":
    main()
