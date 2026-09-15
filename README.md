# Providus AI on DocVQA

DocVQA validation set, 5,349 questions, 1,285 documents (`lmms-lab/DocVQA`).

## May 2026 campaign result

| Metric | Value | Definition |
|---|---:|---|
| Exact + partial coverage | 93.1% (4,981 / 5,349) | Questions scoring at least 0.5 under the internal scorer. A bucket count, not a score. |
| Official ANLS | 0.9066 | Standard DocVQA ANLS. Best normalized Levenshtein similarity over the accepted answers, zero below 0.5. |
| Normalized exact match | 88.3% (4,725) | Exact after lowercasing and removing punctuation, accents and extra spaces. |
| Case-insensitive exact match | 84.2% (4,506) | Exact after lowercasing and trimming. The metric Landing AI reports. |
| Internal ANLS | 0.9213 | Repair-loop scorer. Floors partial credit. Not ANLS. |

## Configuration

| Role | Model |
|---|---|
| Layout | PP-DocLayoutV3 |
| OCR | glm-ocr@f16 (LM Studio) |
| Vision | qwen/qwen3-vl-30b (LM Studio) |
| QA | gpt-5.4-mini and gpt-5.4 (OpenAI), temperature 0, grounded context up to 24,000 characters, 128 output tokens |

The QA model only sees the parsed document text and grounding. It never sees the page image.

Providus swaps OCR, vision and QA models by design. Every result names the models it was produced with.

## Reproduce the numbers

    pip install -r requirements.txt
    python evaluate.py

`evaluate.py` recomputes the table from `results/predictions.jsonl` and exits non-zero if any value differs from this README. `results/SHA256SUMS` covers the predictions file.

## Files

- `results/predictions.jsonl`: one row per question with the answers, the prediction, both scores and a miss diagnostic.
- `MISSES.md`: where the remaining errors are and what fixes each group.
- `NEXT_ITERATION.md`: how the next run is executed and scored.
- `prompt.md`: the QA prompt.

Raw DocVQA images are not included. The Hugging Face mirror lists apache-2.0; the official distribution is through the RRC portal under its own terms.
