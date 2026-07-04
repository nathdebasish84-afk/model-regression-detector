# Model Regression Detection System

CI for prompt changes. This pipeline runs a golden dataset through an
LLM-powered feature every time the prompt or dataset changes, scores the
output on multiple dimensions, diffs it against the previous run, and blocks
the PR if it finds a real regression.

The feature under test is a customer support email classifier (category +
one-line summary), built on Groq (`llama-3.3-70b-versatile`). The classifier
itself is a stand-in — the point of this repo is the eval/CI harness around
it, which is provider-agnostic.

## Why this exists

Teams ship prompt changes to production by editing a string and hoping for
the best. This is git-style version control and CI for prompt behavior:
every prompt change gets tested against real cases before it merges, and a
Slack alert fires if something breaks.

## Architecture

```
prompts/*.yaml        → versioned prompt configs (the "code" under test)
data/golden_dataset.json → hand-labeled test cases (the "code" under test)
src/classifier.py     → the LLM feature itself
src/eval_runner.py     → runs every case, scores category match + LLM-judged summary quality
src/compare.py         → diffs current run vs. previous run, flags regressions/drift
src/report.py          → renders an HTML diff report
src/alert.py           → posts a Slack summary with a link to the report
main.py                → CLI entrypoint gluing it together
.github/workflows/     → runs the above on every PR touching prompts/ or the dataset
```

Every eval run is written to `runs/run_<timestamp>_<id>.json`. The pipeline
always diffs the latest run against the second-latest, so history matters —
in CI, `runs/` is restored via `actions/cache` between workflow runs even
though it's gitignored locally.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in GROQ_API_KEY, optionally SLACK_WEBHOOK_URL
```

Get a Groq API key from console.groq.com. Slack webhook is optional — the
pipeline just prints a "skipping alert" message if it's not set.

## Running it

```bash
python main.py
```

First run establishes a baseline (nothing to diff against yet). Run it
again after editing a prompt to see the diff logic kick in:

```bash
python main.py --prompt prompts/email_classifier_v2_experimental.yaml
```

`v2_experimental.yaml` is included deliberately — it strips the few-shot
examples and vaguens the category definitions, which is a realistic way a
prompt "simplification" quietly makes things worse. Running the eval against
it after v1 should surface real regressions in `runs/latest_report.html` and
in the console output.

Flags:
- `--prompt <path>` — which prompt config to test (default: `email_classifier_v1.yaml`)
- `--dataset <path>` — which golden dataset to test against
- `--no-alert` — skip the Slack post (useful for local runs)

Exit code is `1` if the run is classified `critical`, so it fails CI.

## How to add test cases

Add an entry to `data/golden_dataset.json`:

```json
{
  "id": "unique_id",
  "input": "the email text",
  "expected_category": "billing|technical|account|general",
  "expected_summary": "ideal one-sentence summary",
  "expected_difficulty": "easy|medium|hard",
  "notes": "why this case matters"
}
```

Seed data is hand-labeled, not LLM-generated — that's the point. The
16 cases here cover the four categories plus deliberate edge cases
(ambiguous, very short, typos, code-mixed language, sarcasm, multi-topic).
The intended workflow: every time a real production email gets
misclassified, add it here as a new case with `expected_difficulty: "hard"`
and a note on why it broke. The dataset should grow from real failures, not
just up-front guessing.

## How to adjust thresholds

`compare_runs()` in `src/compare.py` takes `warn_threshold` (default 3%) and
`critical_threshold` (default 8%) as pass-rate-drop thresholds. With only 16
cases, a single flip is already a 6.25% swing, so these defaults are tuned
for a dataset in the 50-100 range per the original guide — tighten them as
your dataset grows, or you'll get false alarms on small datasets.

`rolling_drift_check()` compares the last 7 runs' average pass rate against
the 7 before that, to catch degradation too gradual to trip a single-run
alert. It needs at least 14 runs of history before it activates.

## Architecture decisions worth knowing for interviews

- **LLM-as-judge is a separate model call, not the model under test grading
  itself.** Judge model is hardcoded to `llama-3.3-70b-versatile` in
  `eval_runner.py` regardless of what's being tested, so a bad prompt can't
  also produce a lenient grade of itself.
- **Category match is binary, summary quality is a judged 1-5 score.**
  These are fundamentally different failure modes — a classifier that's
  100% accurate on category but produces garbage summaries is still
  shipping a broken feature, so both get tracked and reported separately.
- **Thresholds exist because noise isn't signal.** A tiny golden dataset
  makes any single flip look dramatic in percentage terms; the threshold
  logic exists specifically to stop the pipeline from crying wolf.
- **Groq model note:** `llama-3.1-8b-instant` is being deprecated
  (shutting down August 2026) — this project defaults to
  `llama-3.3-70b-versatile` instead. Check Groq's model deprecation page
  before picking a production model.

## Docker

```bash
docker build -t regression-eval .
docker run --rm -e GROQ_API_KEY=$GROQ_API_KEY -e SLACK_WEBHOOK_URL=$SLACK_WEBHOOK_URL regression-eval
```

## CI

`.github/workflows/eval.yml` runs on every PR that touches `prompts/**` or
`data/golden_dataset.json`. Add `GROQ_API_KEY` and (optionally)
`SLACK_WEBHOOK_URL` as repo secrets under Settings → Secrets → Actions.

## Next steps (per the original build guide)

- Expand the golden dataset from 16 to 50-100 cases.
- Swap `RAGAS`/`DeepEval` in for the custom scoring if you want a more
  standardized eval framework to point to.
- Wire the PR comment step to actually block merge on `critical` status
  (currently it comments but doesn't set a required check — add a
  `workflow_dispatch` gate or branch protection rule tied to job success).
