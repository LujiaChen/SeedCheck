# Hypotheses

These are predictions written before any test is run. Results are compared against them afterwards. The predictions are not changed after results are seen.

## The three approaches being compared

- **Script**: a simple program that checks whether numbers and names in the report also appear in the source. No AI involved.
- **Self-check**: the same AI that wrote the report checks its own output.
- **Separate reviewer**: a different AI session, with no access to the writing process, checks the report.

## Hypothesis 1: A separate reviewer finds more mistakes than self-check

- Expected: the separate reviewer finds more of the planted mistakes.
- Refuted if: self-check finds the same number or more, or the difference is too small to be reliable.

## Hypothesis 2: A reviewer from a different company adds value

- Expected: a reviewer from a different AI company finds more mistakes than a reviewer from the same company.
- Refuted if: the difference is too small to be reliable.

## Hypothesis 3: A simple script is enough for some kinds of mistakes

- Expected: for changed numbers and swapped names, the script finds about as many mistakes as the AI reviewer.
- Refuted if: the AI reviewer clearly finds more of these mistakes.
- If expected: these kinds of mistakes can be checked without AI.

## Rules

- Predictions are not edited after results are seen.
- Anything tested that is not listed here is labelled "extra, not planned in advance".
