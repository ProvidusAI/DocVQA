# Next iteration

1. One configuration, declared before the run: QA `openai/gpt-5.6-luna`; OCR and vision models chosen per run and named in the result. The prompt file is committed before the run starts.
2. One pass over all 5,349 questions. A better run replaces the previous result as a whole.
3. Two reported numbers: official ANLS and case-insensitive exact match. Internal ANLS may be logged for repair tracking. It is never the headline.
4. QA context is the full parsed document (markdown plus grounding). No image.
5. Dataset issues are reviewed after the run and listed in `DATASET_ISSUES.md` with a reason per question. They are excluded from the headline count and shown in the miss gallery.
6. Each run publishes `parsed/` (every document's parse output), `results/predictions.jsonl`, `prompt.md`, the model IDs and `SHA256SUMS`.
7. Publication bar: official ANLS at or above 0.99 on this protocol. Until then this repo stays private.
