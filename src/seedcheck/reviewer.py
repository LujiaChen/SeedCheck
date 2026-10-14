from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from jsonschema import validate

_SENTENCE_BREAK = re.compile(r"(?<=[.!?])(?:[ \t]+|\n+)(?=[A-Z\"'])")


def sentence_spans(text: str) -> list[tuple[int, int]]:
    spans = []
    start = 0
    for match in _SENTENCE_BREAK.finditer(text):
        left, right = start, match.start()
        while left < right and text[left].isspace():
            left += 1
        while right > left and text[right - 1].isspace():
            right -= 1
        if left < right:
            spans.append((left, right))
        start = match.end()
    left, right = start, len(text)
    while left < right and text[left].isspace():
        left += 1
    while right > left and text[right - 1].isspace():
        right -= 1
    if left < right:
        spans.append((left, right))
    return spans


def prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def parse_output(raw: str, schema: dict[str, Any]) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Reviewer did not return valid JSON: {exc}") from exc
    validate(value, schema)
    return value


def sentence_aligned(report: str, quote: str) -> bool:
    """Quote must be verbatim and start/end at sentence boundaries."""
    start = report.find(quote)
    if start < 0 or report.find(quote, start + 1) >= 0:
        return False
    end = start + len(quote)
    return (start, end) in sentence_spans(report)


def locate_quote(report: str, quote: str) -> tuple[str, int | None, int | None]:
    positions = [m.start() for m in re.finditer(re.escape(quote), report)] if quote else []
    if not positions:
        return "invalid_issue", None, None
    if len(positions) > 1:
        return "ambiguous_match", None, None
    start = positions[0]
    end = start + len(quote)
    if not sentence_aligned(report, quote):
        return "invalid_issue", start, end
    return "matched", start, end


def sentinel_output(mode: str, report: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    if mode == "null":
        return {"issues": []}
    issues = []
    if mode == "oracle":
        for rec in records:
            start, end = rec["start"], rec["end"]
            span = next(((a, b) for a, b in sentence_spans(report["text"]) if start <= b and end >= a and (start >= a or report["text"][start:a].isspace()) and (end <= b or report["text"][b:end].isspace())), None)
            if span is None:
                raise ValueError(f"Ground-truth span {rec['injection_id']} does not fall in a complete sentence")
            a, b = span
            quote = report["text"][a:b]
            issues.append({"quote": quote, "category": rec["error_type"], "explanation": "Oracle sentinel: known planted span."})
    elif mode == "spam":
        for start, end in sentence_spans(report["text"]):
            issues.append({"quote": report["text"][start:end], "category": "other", "explanation": "Spam sentinel: flag every sentence."})
    else:
        raise ValueError(f"Unknown sentinel: {mode}")
    return {"issues": issues}
