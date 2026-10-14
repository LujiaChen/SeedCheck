from __future__ import annotations

import random
from collections import defaultdict
from typing import Any

from .reviewer import locate_quote


def score(report: dict[str, Any], records: list[dict[str, Any]], output: dict[str, Any]) -> dict[str, Any]:
    found: set[str] = set()
    issue_results = []
    false_positives = 0
    true_positive_issues = 0
    for issue in output.get("issues", []):
        status, start, end = locate_quote(report["text"], issue.get("quote", ""))
        detected = []
        if status == "matched":
            for rec in records:
                if start < rec["end"] and end > rec["start"]:
                    found.add(rec["injection_id"])
                    detected.append(rec["injection_id"])
            if not detected:
                false_positives += 1
            else:
                true_positive_issues += 1
        issue_results.append({"status": status, "detected_injection_ids": detected})
    by_type: dict[str, dict[str, int]] = defaultdict(lambda: {"found": 0, "total": 0})
    for rec in records:
        by_type[rec["error_type"]]["total"] += 1
        by_type[rec["error_type"]]["found"] += rec["injection_id"] in found
    return {
        "report_id": report["report_id"], "variant": report["variant"], "detected": len(found),
        "injection_count": len(records), "recall": len(found) / len(records) if records else None,
        "false_positive_count": false_positives,
        "issue_precision": true_positive_issues / (true_positive_issues + false_positives) if true_positive_issues + false_positives else None,
        "invalid_issue_count": sum(x["status"] == "invalid_issue" for x in issue_results),
        "ambiguous_match_count": sum(x["status"] == "ambiguous_match" for x in issue_results),
        "by_error_type": {k: {**v, "recall": v["found"] / v["total"] if v["total"] else None} for k, v in sorted(by_type.items())},
        "issues": issue_results,
    }


def bootstrap_report_ci(values: list[tuple[int, int]], iterations: int = 2000, seed: int = 20261013) -> dict[str, Any]:
    """Report-level percentile CI for pooled recall; tuple is (found, total) per report."""
    if not values:
        return {"estimate": None, "lower_95": None, "upper_95": None, "reports": 0}
    def ratio(sample: list[tuple[int, int]]) -> float:
        denominator = sum(total for _, total in sample)
        return sum(found for found, _ in sample) / denominator if denominator else 0.0
    rng = random.Random(seed)
    estimates = sorted(ratio([values[rng.randrange(len(values))] for _ in values]) for _ in range(iterations))
    return {"estimate": ratio(values), "lower_95": estimates[int(0.025 * (iterations - 1))], "upper_95": estimates[int(0.975 * (iterations - 1))], "reports": len(values), "iterations": iterations, "seed": seed}
