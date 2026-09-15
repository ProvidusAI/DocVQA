# Next iteration

1. One configuration, declared before the run: a frontier QA model (`openai/gpt-5.6-luna`, or Claude Sonnet for a like-for-like comparison with other published parser benchmarks); OCR and vision models chosen per run and named in the result. The prompt file is committed before the run starts.
2. One pass over all 5,349 questions. A better run replaces the previous result as a whole.
3. Two reported numbers: official ANLS and normalized exact match, with case-insensitive exact match alongside. No other scores are reported.
4. QA context is the full parsed document (markdown plus grounding). No image at answer time.
5. Dataset issues are reviewed after the run and listed in `DATASET_ISSUES.md` with a reason per question. They are excluded from the headline count and shown in the miss gallery. Until that review exists, every question is counted.
6. Each run publishes `parsed/` (every page's parse output), `results/runs/<run-id>/predictions.jsonl`, `run.json`, `prompt.md`, the model IDs and `SHA256SUMS`. The scripts in `scripts/` are the runner.
7. Publication bar: official ANLS at or above 0.99 on this protocol. Until then this repo stays private.
8. After the validation run, submit the same configuration to the DocVQA test set through the RRC portal (docvqa.org). The test answers are not public, so a leaderboard entry settles the comparison that a validation number cannot.
