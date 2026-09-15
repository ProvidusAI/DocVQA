# Official DocVQA submission

The validation split has public answers, so any validation number, ours included, can be argued with. The test split answers are private and are scored only by the Robust Reading Competition portal. A test-set entry is the number nobody can dispute.

## What the portal expects

Source: the DocVQA challenge page on rrc.cvc.uab.es (challenge 17, Task 1, Single Page Document VQA).

- One JSON file, a list with one object per test question: `{"questionId": <int>, "answer": "<string>"}`. Example from the portal: `[{"answer": "TRANSMIT CONFIRMATION REPORT", "questionId": 8399}, ...]`.
- Metric: ANLS. Answers are not case sensitive but are space sensitive.
- Test split: 5,188 questions over 1,287 documents. Images and questions are public (the Hugging Face mirror `lmms-lab/DocVQA` test split carries both), answers are not.
- An account on the portal is needed to submit and to appear on the leaderboard. Submissions carry a method name and description; the description is where the configuration is declared.

## Steps

1. Register at https://rrc.cvc.uab.es and join the DocVQA challenge (ch=17).
2. Download the test split:

       python scripts/download_docvqa.py --split test

   This writes `data/docvqa-test/` with `annotations.jsonl` (no answers), `images/` and `hashes.json`.
3. Parse every test page with DocAI, same configuration as the validation run:

       python scripts/parse_with_docai.py --kb-id <kb> --dataset-dir data/docvqa-test --parsed-dir parsed-test

4. Answer the questions from the parsed markdown, one pass, same prompt and QA model as the validation run:

       python scripts/run_qa.py --model <qa model> --run-id test-<date> --dataset-dir data/docvqa-test --parsed-dir parsed-test

5. Build the submission file:

       python scripts/make_submission.py results/runs/test-<date>/predictions.jsonl --out results/runs/test-<date>/result_task1.json

6. Upload `result_task1.json` on the portal under Task 1. Method name: "Providus DocAI parse + <QA model>". Description: the configuration table from the README (layout, OCR, vision, QA model, prompt, no image at answer time), and a link to this repository once it is public.
7. Record the portal's ANLS in the README next to the validation number, with the submission date and method id.

## Rules we hold ourselves to

- The test run uses exactly the configuration and prompt that produced the validation number reported alongside it. No changes between the two.
- One submission per configuration. If the configuration changes, it is a new method entry on the portal, not an overwrite.
- No dataset-issue exclusions on the test set; the portal scores every question.
- The run's `parsed-test/`, `predictions.jsonl`, `run.json` and `result_task1.json` are kept with checksums so the entry can be audited.
