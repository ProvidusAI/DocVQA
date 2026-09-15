# Providus AI on DocVQA

DocVQA asks 5,349 questions about 1,285 real scanned documents: forms, letters, reports, tables, charts. It is normally used to score vision models that look at the page. We use it to score our parse output instead. The question-answering model in this benchmark never sees an image. It only sees the text and layout that Providus DocAI extracted from the page. If the answer is not in our output, the model cannot find it.

## Result

**93.1% exact-or-partial coverage (4,981 of 5,349), official ANLS 0.9066.** May 2026 campaign result, DocVQA validation set.

| Metric | Value | Definition |
|---|---:|---|
| Exact + partial coverage | 93.1% (4,981 / 5,349) | Questions scoring at least 0.5 under the internal scorer. A bucket count, not a score. |
| Official ANLS | 0.9066 | Standard DocVQA ANLS. Best normalized Levenshtein similarity over the accepted answers, zero below 0.5. |
| Normalized exact match | 88.3% (4,725) | Exact after lowercasing and removing punctuation, accents and extra spaces. |
| Case-insensitive exact match | 84.2% (4,506) | Exact after lowercasing and trimming. The metric Landing AI reports. |
| Internal ANLS | 0.9213 | Repair-loop scorer. Floors partial credit. Not ANLS. |

Every number in this table is recomputed by `evaluate.py` from `results/predictions.jsonl`. The script exits non-zero if any value differs from what is written here. `MISSES.md` lists where the remaining errors are and what fixes each group.

## Methodology

1. Each of the 1,285 documents is parsed by DocAI: layout detection, OCR, and a vision pass over figures and tables. The output is markdown plus a grounding JSON that lists every element with its page, bounding box and text.
2. For each question, the grounding is turned into chunks and the chunks most relevant to the question are placed in the QA model's context, up to 24,000 characters. The page image is never sent.
3. The QA model returns the shortest verbatim span that answers the question, or "not found". The prompt is in `prompt.md`.
4. Each prediction is scored against the accepted answers with official ANLS and with exact match. `evaluate.py` is the reference implementation of both.

## Configuration

| Role | Model |
|---|---|
| Layout | PP-DocLayoutV3 |
| OCR | glm-ocr@f16 (LM Studio) |
| Vision | qwen/qwen3-vl-30b (LM Studio) |
| QA | gpt-5.4-mini and gpt-5.4 (OpenAI), temperature 0, grounded context up to 24,000 characters, 128 output tokens |

DocAI runs the same pipeline against any OCR, vision or QA model you point it at, hosted or local. That is a design choice: an on-prem customer with no internet runs everything on one LM Studio box, and the cloud service uses hosted models. Every result we publish names the models that produced it.

## Test it on your own documents

A benchmark number tells you how we do on DocVQA's documents. The number that matters is how we do on yours. The same pipeline behind this result is the one behind the DocAI API, so you can run your own bake-off in an afternoon.

Create an account at https://platform.providus.ai/register. New organizations start with trial credits. An organization admin creates a key under Settings, API Keys. Requests carry it in the `x-api-key` header. Questions, larger evaluations or an on-prem trial: hello@providus.ai.

Create a knowledge base, or list the ones you have:

    curl -s https://api.providus.ai/v1/knowledge-bases \
      -H "x-api-key: $DOCAI_API_KEY"

Upload a document and parse it in one call:

    curl -s https://api.providus.ai/v1/files \
      -H "x-api-key: $DOCAI_API_KEY" \
      -F file=@your-document.pdf \
      -F kb_id=$KB_ID \
      -F auto_parse=true

The response includes the file id and the parse job. When the job completes, list the artifacts and fetch the markdown and the grounding JSON (every element with its page, bounding box and text):

    curl -s https://api.providus.ai/v1/files/$FILE_ID/artefacts \
      -H "x-api-key: $DOCAI_API_KEY"

    curl -s https://api.providus.ai/v1/artifacts/$MANIFEST_ID/$ARTIFACT_KEY \
      -H "x-api-key: $DOCAI_API_KEY"

Feed the markdown to the QA model of your choice with `prompt.md` and you have reproduced this benchmark's setup on your own files. Score with your own answer key; `evaluate.py` shows the exact normalization we use.

The interactive API reference is at https://api.providus.ai/docs and the product documentation at https://docs.providus.ai (file upload and processing: https://docs.providus.ai/api/files and https://docs.providus.ai/api/file-processing). If you work from a coding agent, the DocAI MCP server exposes upload, parse, extract, classify, split and search as tools. Setup for Claude Code, Cursor and Codex is at https://docs.providus.ai/mcp; in Claude Code it is `/plugin marketplace add ProvidusAI/docai-plugins` then `/plugin install docai`, with `DOCAI_API_KEY` set.

Running on your own hardware: `curl -fsSL https://providus.ai/deployment.sh | sh` installs the same stack on macOS, Linux or Windows with local models. On-prem installs point `DOCAI_BASE_URL` at their own instance and everything above works unchanged.

## Reproduce the numbers in this repo

    pip install -r requirements.txt
    python evaluate.py

`results/SHA256SUMS` covers the predictions file.

## Data format

One JSON object per line in `results/predictions.jsonl`, sorted by `question_id`:

| Field | Type | Meaning |
|---|---|---|
| `question_id` | string | DocVQA question id |
| `doc_id` | integer | DocVQA document id |
| `img_hash` | string | Short hash of the page image, stable across runs |
| `question` | string | The question as asked |
| `answers` | list of strings | Accepted answers from the dataset |
| `pred` | string | DocAI plus QA model prediction |
| `official_score` | float | Official ANLS for this row, 0 to 1 |
| `internal_score` | float | Internal repair-loop score, 0 to 1 |
| `exact_ci` | boolean | Case-insensitive exact match |
| `exact_normalized` | boolean | Exact match after normalization |
| `diagnostic` | string | Miss category used in `MISSES.md` |

## Files

- `results/predictions.jsonl`: one row per question with the answers, the prediction, both scores and a miss diagnostic.
- `MISSES.md`: where the remaining errors are and what fixes each group.
- `NEXT_ITERATION.md`: how the next run is executed and scored.
- `prompt.md`: the QA prompt.
- `evaluate.py`: standalone scorer, no dependency on the DocAI codebase.

Raw DocVQA images are not included. The Hugging Face mirror (`lmms-lab/DocVQA`) lists apache-2.0; the official distribution is through the RRC portal under its own terms.
