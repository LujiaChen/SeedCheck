# ADR-0001: Project Scope and Initial Design

- **Status**: Proposed
- **Date**: 2026-10-12

## Context

LLM-based reviewer agents are often assumed to catch errors in generated reports, but this is rarely measured with known ground truth. SeedCheck is an attempt to measure it: inject known errors into source-grounded reports and observe how often different reviewer configurations catch them, how often they flag clean reports, and what each detection costs.

## Decision

**Research questions**

- RQ1: On source-grounded reports with injected errors, does an independent LLM reviewer detect more errors than (a) the writer reviewing its own output and (b) a deterministic script baseline?
- RQ2: If an independent reviewer does better, is the gain due to a stronger model within the same provider, or to using a different provider at a similar tier?

**Scope**

- Task domain: review of reports against a given source document.
- Error types for the MVP: `numeric_change`, `entity_swap`, `unsupported_claim`.

**Non-goals**

- General agent benchmarking, or ranking model vendors or frameworks.
- Security or credential-isolation claims.
- Writing-quality evaluation.
- Open-domain fact checking without a source document.
- Omission and causal-reversal errors (deferred; they are hard to locate with character spans).

**Architecture**

- The evaluation core (error injection, scoring, statistics) does not depend on OpenClaw. The system under test connects through adapters, starting with a direct API adapter.
- Ground truth is produced by the injector, not by human annotation, so it is reproducible and free of annotator bias.
- Reviewer output must quote the report verbatim. Matching is then deterministic, and no LLM is needed as a judge. Issues whose quote is not a substring of the report are counted as `invalid_issue` and excluded from detection.

**Metrics and baselines**

- Primary: recall per error type, false-positive rate on clean reports, and token cost per true detection.
- Baselines: a deterministic script that checks numbers and named entities against the source (C0), and writer self-review (C1).
- Reviewer configurations: independent reviewer on the same model (C2), on a stronger model from the same provider (C3), and on a similar-tier model from a different provider (C4).
- All configurations share one prompt template. The prompt is frozen on a development set before the test set is used.
- Uncertainty is reported with bootstrap 95% confidence intervals over reports. Where intervals overlap, results are reported as "not distinguishable at this sample size".

**Cost and reproducibility**

- Model identifiers are recorded in full, along with the date and parameters.
- Raw responses are cached, so the full results can be regenerated offline in replay mode.
- A ledger records token usage and estimated cost for every call. A hard budget cap applies.
- Experiments proceed in gated stages. Larger runs happen only after the earlier stage has produced a usable result.

## Consequences

- Sanity checks come first: an oracle, a null reviewer, and a spam reviewer must score as expected before any real model is evaluated.
- Negative results are reported as results. If the independent reviewer does not beat the script baseline, the write-up says so.
- Hypotheses are written down before the full experiment runs, in `docs/hypotheses.md`.
