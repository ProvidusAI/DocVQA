# Where the misses are

Zero-score questions under official ANLS: 456 of 5,349.

| Bucket (diagnostic) | Count | What fixes it |
|---|---:|---|
| cache_or_extraction_missing | 272 | Extraction. The parse failed or the answer text never reached the output. Largest group. Re-parse with the current pipeline (router fix, geometry table cells, margin and header/footer OCR) and re-bucket. |
| formatting_mismatch | 0 | QA prompt and narrow post-processing. Right answer, wrong shape. Ask for the verbatim span. Add auditable rules for page numbers, years, counts, table separators and markdown cleanup. |
| evidence_retrieved_qa_wrong | 178 | QA. Give the model the full parsed document instead of a 24,000-character window. Stronger grounded prompt. |
| evidence_missing, evidence_not_retrieved | 5, 1 | Falls out of the extraction lane. |
| Dataset issues | 0 flagged | Review remaining misses by hand. Publish an exclusion list with a reason per question. Excluded questions stay visible and are not counted. Landing AI excluded 18. |

ANLS 0.99 needs about 55 or fewer zero-score questions out of 5,349. Extraction has to deliver most of that. QA work alone cannot.
