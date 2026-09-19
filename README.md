<p align="center">
  <img src="assets/banner.png" alt="Providus DocAI on DocVQA" width="100%">
</p>

<h1 align="center">Providus AI on DocVQA</h1>

<p align="center">
  <strong>Document parsing scored by what a language model can answer from the output alone. No image at answer time.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Official%20ANLS-0.9066-2B6FAA" alt="Official ANLS 0.9066">
  <img src="https://img.shields.io/badge/Normalized%20exact%20match-88.3%25-6DBBFF" alt="Normalized exact match 88.3%">
  <img src="https://img.shields.io/badge/Exact%20%2B%20near%20match-93.1%25-6DBBFF" alt="Exact + near match 93.1%">
  <img src="https://img.shields.io/badge/Questions-5%2C349-111111" alt="5,349 questions">
  <img src="https://img.shields.io/badge/Dataset-DocVQA%20val-555555" alt="DocVQA validation">
  <img src="https://img.shields.io/badge/Parsed%20by-Providus%20DocAI-E89B3C" alt="Parsed by Providus DocAI">
</p>

<p align="center">
  <a href="https://platform.providus.ai/register">Try DocAI</a> •
  <a href="https://api.providus.ai/docs">API reference</a> •
  <a href="https://docs.providus.ai">Docs</a> •
  <a href="https://docs.providus.ai/mcp">MCP</a> •
  <a href="MISSES.md">Where the misses are</a> •
  <a href="NEXT_ITERATION.md">Next iteration</a> •
  <a href="SUBMISSION.md">Official submission</a>
</p>

Providus DocAI turns a scanned page into two things: markdown a person can read, and a grounding JSON a program can trust. Every element in the JSON carries its page, its bounding box, its text and a confidence; tables carry their cells with row and column geometry. DocVQA is how we test that output is complete. Its 5,349 questions cover 1,286 real scanned documents: forms, letters, reports, tables, charts. (Two of them, document ids 4331 and 4386, are byte-identical page images, so the pipeline parses 1,285 unique pages.) The benchmark is normally used to score vision models that look at the page. We use it differently: the question-answering model never sees an image, only what DocAI extracted. If the answer is not in our output, the model cannot find it.

## What the parse output looks like

Five DocVQA pages, parsed on a laptop with local models (glm-ocr and qwen3-vl-4b in LM Studio, no cloud). The blue box is the grounding element DocAI returned that contains the answer. No box was drawn by hand: `scripts/build_gallery.py` searches the grounding JSON for the answer text and draws the element's bounding box.

<table>
<tr>
<td width="50%"><img src="assets/gallery/6982.png" alt="Budget request summary form"></td>
<td width="50%"><img src="assets/gallery/5238.png" alt="Writer assignment letter"></td>
</tr>
<tr>
<td>
<b>Q:</b> According to the budget request summary, what is the total amount of the proposed budget?<br>
<b>A:</b> 15,000.00<br>
A typed 1966 grant form. DocAI returned the table with 15 cells from TableFormer geometry and the total row as its own element.
</td>
<td>
<b>Q:</b> What is the Date Assigned as per the document?<br>
<b>A:</b> January 18, 2005<br>
A label and value pair in running text. The element is 16 characters wide, so a downstream system can highlight exactly that span.
</td>
</tr>
<tr>
<td><img src="assets/gallery/14465.png" alt="Line chart of motor vehicle accident mortality"></td>
<td><img src="assets/gallery/14314.png" alt="Report cover with photo and seal"></td>
</tr>
<tr>
<td>
<b>Q:</b> What is the title of the plot?<br>
<b>A:</b> AGE ADJUSTED MOTOR VEHICLE ACCIDENT MORTALITY RATE CANADA<br>
The title is a <code>figure_title</code> element; the chart itself gets a vision pass that reads axes, scale and the data points into the markdown.
</td>
<td>
<b>Q:</b> In which sea did the sea bird wreck occur?<br>
<b>A:</b> IRISH SEA<br>
A photographed cover with a seal. The seal is detected as its own <code>seal</code> element and its text is read; the title lines are separate text elements.
</td>
</tr>
<tr>
<td><img src="assets/gallery/4806.png" alt="Annual report page with header"></td>
<td>
<b>Q:</b> What is the name of the company?<br>
<b>A:</b> ITC Limited<br>
A designed annual report page. The header block is returned as a <code>header</code> element, separate from the body text, so headers and footers can be kept or dropped by the consumer.
</td>
</tr>
</table>

## What one parse call returns

The element behind the second card, verbatim from `grounding.json`:

```json
{
  "id": "p1_e0004",
  "type": "text",
  "label": "text",
  "bbox": { "x1": 0.357, "y1": 0.183, "x2": 0.492, "y2": 0.2 },
  "pixel_bbox": [357, 183, 492, 200],
  "content": "January 18, 2005",
  "ocr_content_len": 16,
  "confidence": { "score": 0.75, "route": "medium", "vlm_applied": false },
  "markdown_anchor": "p1-e0004"
}
```

Coordinates come normalized and in pixels. `confidence.route` says whether the element was routed to the vision model for a second look. `markdown_anchor` links the element to its place in `result.md`, so a citation in the markdown can be traced back to a box on the page. Table elements add a `cells` array (row, column, span, bbox, text) with `cellsSource` naming how the geometry was measured; the budget form above reports `table-former`. The full document is `schema_version`, `document`, `confidence`, `diagnostics` and `pages[]`, each page with `width`, `height` and `elements[]`.

```
 PDF / scan            Providus DocAI                       QA model              Score
┌────────────┐   ┌──────────────────────────┐   ┌──────────────────────────┐   ┌───────────┐
│ 1,286 docs │ → │ layout → OCR → vision    │ → │ grounded chunks (text +  │ → │ ANLS /    │
│            │   │ markdown + grounding JSON│   │ boxes), no page image    │   │ exact     │
└────────────┘   └──────────────────────────┘   └──────────────────────────┘   └───────────┘
```

## Result

**Official ANLS 0.9066. Normalized exact match 88.3% (4,725 of 5,349). Exact or near match 93.1% (4,981).** May 2026 campaign result, DocVQA validation set, all 5,349 questions scored, none excluded.

| Metric | Value | Definition |
|---|---:|---|
| Official ANLS | 0.9066 | Standard DocVQA ANLS. Best normalized Levenshtein similarity over the accepted answers, zero below 0.5. |
| Normalized exact match | 88.3% (4,725) | Exact after lowercasing and removing punctuation, accents and extra spaces. |
| Case-insensitive exact match | 84.2% (4,506) | Exact after lowercasing and trimming only. |
| Exact + near match | 93.1% (4,981) | 4,725 exact plus 256 near matches. A near match is a prediction that is not exact but, after normalization, has Levenshtein similarity of at least 0.35 to an accepted answer, or contains it or is contained by it (3 or more characters), or shares at least 80% of the shorter answer's tokens (or half of all tokens with at least two shared). Examples from this run: "May 3, 2006 at 9:00 a.m. local time" for "May 3, 2006", "quality issues" for "Quality", "Week 2" for "2". Useful for seeing how much is a formatting gap rather than a missing answer; not a leaderboard metric. |

Every number in this table is recomputed by `evaluate.py` from `results/predictions.jsonl`. The script exits non-zero if any value differs from what is written here, and it runs in GitHub Actions on every push (`.github/workflows/evaluate.yml`). `MISSES.md` lists where the remaining errors are and what fixes each group.

## Runs

Each run is one configuration over all 5,349 questions, scored with `evaluate.py`. The parsed output for every page, the predictions and the run manifest live under `runs/<run id>/`.

| Run | Official ANLS | Normalized exact | Case-insensitive exact | Exact + near match | Configuration |
|---|---:|---:|---:|---:|---|
| May 2026 campaign result | 0.9066 | 88.3% (4,725) | 84.2% (4,506) | 93.1% (4,981) | glm-ocr@f16, qwen/qwen3-vl-30b (LM Studio), QA gpt-5.4-mini and gpt-5.4, grounded chunks up to 24,000 characters |
| 2026-09-19 local run | 0.8598 | 82.5% (4,412) | 78.1% (4,176) | 87.2% (4,663)* | ggml-org/glm-ocr, qwen/qwen3-vl-30b (LM Studio on a Mac Studio), QA gpt-5.6-luna at low reasoning effort, full page markdown as context, 256 output tokens |

*For runs after May 2026 this column counts questions with official ANLS of at least 0.5 (exact plus partial credit); the campaign scorer's near-match rule is not part of this toolkit.

The 2026-09-19 run is the first under the protocol in `NEXT_ITERATION.md`: the whole set parsed once with one configuration on local models, then answered in one pass by one QA model. Its artifacts are in `runs/2026-09-19-local-glm-ocr-qwen3-vl-30b/`: `parsed/` (1,285 pages, `result.md` and `grounding.json` each, plus `_manifest.json` with the configuration and DocAI manifest ids), `predictions.jsonl`, `run.json` and `SHA256SUMS`. Of its 686 zero-score questions, 313 are answers the model reported as not found in the parsed text; the rest are wrong answers. Score it yourself:

    python evaluate.py runs/2026-09-19-local-glm-ocr-qwen3-vl-30b/predictions.jsonl

## Methodology

1. Each of the 1,285 unique page images is parsed by DocAI: layout detection, OCR, and a vision pass over figures and tables. The output is markdown plus a grounding JSON that lists every element with its page, bounding box and text.
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

DocAI runs the same pipeline against any OCR, vision or QA model you point it at, hosted or local. That is a design choice: an on-prem customer with no internet runs everything on one LM Studio box, and the cloud service uses hosted models. Every result we publish names the models that produced it. The gallery above was produced with the smaller local models (glm-ocr, qwen3-vl-4b) on a laptop; the benchmark figures below used qwen3-vl-30b.

## Where it runs

| | How | Models |
|---|---|---|
| Cloud API | `https://api.providus.ai`, API key in `x-api-key` | Hosted OCR, vision and QA models |
| On-prem | Versioned installer, Docker, one machine, no internet needed | Your LM Studio or Ollama models |
| Coding agents | DocAI MCP server for Claude Code, Cursor, Codex | Same API underneath |
| Redaction | Rules per knowledge base; PII, health, card and company data scrubbed from markdown and burned on page images at parse time | Runs after parse, on-prem by default |

One pipeline, one artifact contract, in all four.

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

Running on your own hardware: the on-prem installer is a versioned script with a published checksum. Download it, verify it, read it, then run it:

    curl -fsSLO https://providus.ai/deployment.sh
    curl -fsSLO https://providus.ai/deployment.sh.sha256
    shasum -a 256 -c deployment.sh.sha256      # sha256sum -c on Linux
    sh deployment.sh

It installs the same stack on macOS, Linux or Windows with local models; the release bundle and its checksum are at `https://providus.ai/bundles/docai-onprem-<version>.zip` and `.zip.sha256`. On-prem installs point `DOCAI_BASE_URL` at their own instance and everything above works unchanged.

## Dataset

DocVQA validation split, 5,349 questions over 1,286 documents (1,285 unique page images; document ids 4331 and 4386 share one). We read it from the Hugging Face mirror `lmms-lab/DocVQA` (config `DocVQA`, split `validation`). The images are not stored in this repo; the script below downloads about 1 GB into `data/docvqa/`:

    pip install -r requirements-download.txt
    python scripts/download_docvqa.py

It writes one PNG per document, `annotations.jsonl` with the questions and accepted answers, and `hashes.json`, which maps each `docId` to the 12-character `img_hash` used in `results/predictions.jsonl`, so your `parsed/` folders line up with the published rows. The official distribution is through the RRC portal at docvqa.org under its own terms; the mirror lists apache-2.0.

## Repository structure

    .
    ├── README.md
    ├── MISSES.md                 where the remaining errors are and what fixes each group
    ├── NEXT_ITERATION.md         protocol for the next run
    ├── SUBMISSION.md             how the official test-set entry on the RRC portal is produced
    ├── prompt.md                 the QA system prompt
    ├── evaluate.py               standalone scorer (official ANLS, exact match)
    ├── requirements.txt          editdistance, requests
    ├── requirements-download.txt datasets, pillow (dataset download only)
    ├── assets/
    │   ├── banner.png
    │   └── gallery/                  the five evidence cards above (images + cards.json)
    ├── scripts/
    │   ├── derive_predictions.py     builds results/predictions.jsonl from the campaign artifact
    │   ├── build_gallery.py          draws the answer element's box on the page for the gallery
    │   ├── download_docvqa.py        step 1: dataset to data/docvqa/
    │   ├── parse_with_docai.py       step 2: every page through the DocAI API to parsed/
    │   ├── run_qa.py                 step 3: QA over the parsed markdown, one pass
    │   └── make_submission.py        converts a test run into the RRC portal's result_task1.json
    ├── runs/<run id>/             one folder per run: parsed/, predictions.jsonl, run.json, SHA256SUMS
    ├── results/
    │   ├── predictions.jsonl         the published run, 5,349 rows
    │   ├── SHA256SUMS
    │   └── runs/<run-id>/            your own runs (not committed)
    ├── data/docvqa/                  dataset (not committed)
    │   ├── annotations.jsonl
    │   ├── hashes.json
    │   └── images/{docId}.png
    └── parsed/{img_hash}/            DocAI output per page (not committed)
        ├── result.md
        └── grounding.json

## Reproduce

Two levels. The first checks our published numbers and takes a few seconds. The second re-runs the benchmark end to end with your own DocAI key and QA model.

### 1. Verify the published table

    pip install -r requirements.txt
    python evaluate.py

`evaluate.py` recomputes every metric from `results/predictions.jsonl` and exits non-zero if any value differs from the table above. `results/SHA256SUMS` covers the predictions file.

### 2. Run the benchmark yourself

Step 1, dataset (about 1 GB):

    pip install -r requirements-download.txt
    python scripts/download_docvqa.py

Step 2, parse every page with DocAI. Create an account at https://platform.providus.ai/register, make a key under Settings, API Keys, and create a knowledge base to hold the pages (`POST /v1/knowledge-bases` or the app). Then:

    pip install -r requirements.txt
    export DOCAI_API_KEY=...
    export DOCAI_BASE_URL=https://api.providus.ai     # or your on-prem instance
    python scripts/parse_with_docai.py --kb-id <knowledge base id>

Each page is uploaded with `auto_parse=true`; the script waits for the job and saves `result.md` and `grounding.json` under `parsed/{img_hash}/`. It skips pages that are already parsed, so it can be stopped and resumed. Parsing is per unique image, so the full set costs 1,285 parse credits.

Step 3, answer the questions from the parsed markdown alone and score:

    export QA_API_KEY=...
    export QA_BASE_URL=https://api.openai.com/v1      # any OpenAI-compatible endpoint
    python scripts/run_qa.py --model openai/gpt-5.6-luna --run-id luna-baseline
    python evaluate.py results/runs/luna-baseline/predictions.jsonl

The QA model receives `prompt.md` as the system prompt and the full `result.md` of the page as the user message, temperature 0, 128 output tokens. It never receives the image. The run writes `results/runs/<run-id>/predictions.jsonl` in the same shape as the published file plus a `run.json` with the model and endpoint, and `evaluate.py` prints the same table for it. This is the protocol in `NEXT_ITERATION.md`: one configuration, one pass, official scoring.

Try a small slice first: every script accepts `--limit N`.

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
| `internal_score` | float | Campaign scorer, 0 to 1. Rows at or above 0.5 are the "exact + near match" count; the near-match rule is defined under Result |
| `exact_ci` | boolean | Case-insensitive exact match |
| `exact_normalized` | boolean | Exact match after normalization |
| `diagnostic` | string | Miss category used in `MISSES.md` |

---

<p align="center">
  Built by <a href="https://providus.ai">Providus AI</a>. Questions and evaluations: <a href="mailto:hello@providus.ai">hello@providus.ai</a>
</p>
