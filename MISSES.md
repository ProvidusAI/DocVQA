# Where the misses are

Zero-score questions under official ANLS: 456 of 5,349.

| Bucket (diagnostic) | Count | What fixes it |
|---|---:|---|
| cache_or_extraction_missing | 272 | Extraction. The parse failed or the answer text never reached the output. Largest group. Re-parse with the current pipeline (router fix, geometry table cells, margin and header/footer OCR) and re-bucket. |
| evidence_retrieved_qa_wrong | 178 | QA. Give the model the full parsed document instead of a 24,000-character window. Stronger grounded prompt. |
| evidence_missing, evidence_not_retrieved | 5, 1 | Falls out of the extraction lane. |
| Dataset issues | 0 flagged | Review remaining misses by hand. Publish an exclusion list with a reason per question. Excluded questions stay visible and are not counted. Today every question is counted. |

Partial-credit questions (official score above 0 and below 1): 168 of 5,349. These do not score zero, but each one costs ANLS and none counts as exact.

| Bucket (diagnostic) | Count | What fixes it |
|---|---:|---|
| formatting_mismatch | 95 | QA prompt and narrow post-processing. Right answer, wrong shape. Ask for the verbatim span. Add auditable rules for page numbers, years, counts, table separators and markdown cleanup. |
| cache_or_extraction_missing | 66 | Extraction. Part of the answer text is missing from the output, so the model returned a truncated span. Same lane as the zero-score group. |
| evidence_missing, evidence_not_retrieved | 4, 3 | Falls out of the extraction lane. |

ANLS 0.99 needs about 55 or fewer zero-score questions out of 5,349, with the partial-credit group mostly converted to exact. Extraction has to deliver most of that. QA work alone cannot.
