from __future__ import annotations

import re
from typing import Any

from ..reviewer import sentence_spans

_NUMBER = re.compile(r"(?<!\w)\d[\d,.%]*(?!\w)")
_PROPER = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+(?:Ltd|Inc|Corp))?\b")
_STOP = {"The", "In", "Its", "A", "An", "This", "That", "Company", "Harbor"}


def _norm_number(value: str) -> str:
    return re.sub(r"[, ]", "", value).lower()


def review(source: str, report: str) -> dict[str, Any]:
    """Transparent string baseline; intentionally heuristic, not an NLP fact checker."""
    source_numbers = {_norm_number(x) for x in _NUMBER.findall(source)}
    source_names = set(_PROPER.findall(source))
    issues = []
    for start, end in sentence_spans(report):
        sentence = report[start:end]
        nums = {_norm_number(x) for x in _NUMBER.findall(sentence)}
        names = {x for x in _PROPER.findall(sentence) if x not in _STOP}
        changed = nums - source_numbers
        swapped = {n for n in names if n not in source_names and len(n) > 2}
        if changed or swapped:
            category = "numeric_change" if changed else "entity_swap"
            details = []
            if changed:
                details.append("numbers absent from source: " + ", ".join(sorted(changed)))
            if swapped:
                details.append("names absent from source: " + ", ".join(sorted(swapped)))
            issues.append({"quote": sentence, "category": category, "explanation": "; ".join(details)})
    return {"issues": issues}
