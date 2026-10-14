# Running the SeedCheck code

This note documents the software workflow only. It does not add research claims or interpret results.

## Install and run

From the repository root, install the package and its development dependencies with `python -m pip install -e '.[dev]'`. Then run `seedcheck smoke`, `pytest`, or `seedcheck run --config configs/experiment.example.json`.

The default run uses local deterministic/mock behavior and does not contact an API. `seedcheck smoke` makes temporary examples in memory and verifies the injector, scorer, and three sentinel reviewers.

## Data shape

The runner reads `*.json` files in the configured dataset folder. Each case contains `source`, `report`, and `records`; `records` is an array of InjectionRecord objects. Keep development and held-out test cases in separate folders. The committed `data/dev` case is a tiny software fixture, not an experimental sample.

Use `seedcheck inject` with one clean report and a plan JSON to produce a report and its ground-truth record. Then validate the pair with tests or `validate_ground_truth` before including it in a case.

## Reviewer outputs and matching

Reviewers return JSON of the form `{"issues":[{"quote":"...","category":"...","explanation":"..."}]}`. A quote must be an exact, unique quote from one complete report sentence. A quote absent from the report or not aligned to sentence boundaries is `invalid_issue`; an exact quote occurring more than once is `ambiguous_match`. Neither is credited. One valid quote can detect any planted span it overlaps.

## Configurations and API access

`configs/experiment.example.json` defines the C0–C4 slots. C0 is the transparent number/name string baseline. C1–C4 are configuration slots; their mock mode returns no findings and is not a simulated model result. Oracle, null, and spam sentinels are available by passing `--mode sentinel:oracle`, `sentinel:null`, or `sentinel:spam`.

For a real call, configure a model id, set `SEEDCHECK_BASE_URL` and `SEEDCHECK_API_KEY` in the process environment, and run with `--mode api`. The adapter sends a deterministic-temperature chat-completions request to a caller-supplied OpenAI-compatible endpoint. Do not put credentials in files or commits. API mode refuses to start a call without explicit input/output token prices for that model. Prices are user-supplied and must be checked against the provider's current rate card.

Cached responses are written under `.seedcheck-cache`; the append-only usage ledger is `results/ledger.jsonl`. `runs/`, credentials, and local databases are ignored by Git. The starter config has a $1 budget; the runner reserves 50% headroom over a character-based input estimate plus the configured output-token cap before each request, then checks actual returned token usage. This is an application-side guard, not a provider billing guarantee: tokenization and provider-side overhead vary, so inspect the ledger and provider bill before scaling beyond a small run.

## Prompt and statistics

The prompt source is `prompts/reviewer_v1.txt`; `prompts/reviewer_v1.sha256` freezes the initial version, and every run records its SHA-256 hash. If development work changes the prompt before any held-out scoring, review that change and update the checksum deliberately. After held-out scoring begins, do not tune the prompt against those cases. Recall and clean-report false-positive-rate intervals use deterministic report-level bootstrap resampling (seed 20261013). With only one fixture report the interval is not useful for research inference.

## Current limits

- Unsupported-claim injection is a controlled append; the software can establish that it was absent from the source text, not prove a broad semantic entailment claim.
- C0 uses simple string/regex heuristics. It is an inspectable baseline, not a validated entity recognizer.
- The generic API adapter does not normalize vendor-specific response formats or guarantee JSON-mode support.
- The starter split manifest has no held-out cases. Add and freeze a suitable development/test corpus before interpreting model comparisons.
