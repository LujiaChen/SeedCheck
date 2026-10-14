from __future__ import annotations

import re
from typing import Any

from jsonschema import validate

ERROR_TYPES = {"numeric_change", "entity_swap", "unsupported_claim"}


def inject(report: dict[str, Any], plan: dict[str, str], injection_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Apply one exact, reproducible replacement/addition and return report plus ground truth."""
    kind = plan["error_type"]
    if kind not in ERROR_TYPES:
        raise ValueError(f"Unsupported error type: {kind}")
    text = report["text"]
    original = plan.get("original_text")
    replacement = plan["injected_text"]
    if kind == "unsupported_claim":
        if original not in (None, ""):
            raise ValueError("unsupported_claim plans append a new claim and must not set original_text")
        start = len(text)
        updated_text = text + replacement
        original_value = None
    else:
        if not original or original == replacement:
            raise ValueError("Replacement injections require distinct, non-empty original and injected text")
        matches = list(re.finditer(re.escape(original), text))
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one occurrence of {original!r}; found {len(matches)}")
        match = matches[0]
        start, end = match.span()
        updated_text = text[:start] + replacement + text[end:]
        original_value = original
        if kind == "numeric_change":
            number = re.compile(r"(?<!\w)\d[\d,.]*(?!\w)")
            old_numbers = number.findall(original)
            new_numbers = number.findall(replacement)
            if not old_numbers or not new_numbers or old_numbers == new_numbers:
                raise ValueError("numeric_change must change at least one numeric value")
    end = start + len(replacement)
    injected_report = dict(report, report_id=report["report_id"].removesuffix("_clean") + "_inj", variant="injected", text=updated_text)
    record = {
        "injection_id": injection_id, "report_id": injected_report["report_id"], "error_type": kind,
        "original_text": original_value, "injected_text": replacement, "start": start, "end": end,
        "explanation": plan["explanation"],
    }
    return injected_report, record


def validate_ground_truth(source: dict[str, Any], clean: dict[str, Any], injected_report: dict[str, Any], record: dict[str, Any], injection_schema: dict[str, Any]) -> None:
    validate(record, injection_schema)
    if clean["source_id"] != source["source_id"] or injected_report["source_id"] != source["source_id"]:
        raise ValueError("Source/report IDs do not agree")
    if injected_report["variant"] != "injected" or injected_report["report_id"] != record["report_id"]:
        raise ValueError("InjectionRecord must identify the injected report")
    if not (0 <= record["start"] <= record["end"] <= len(injected_report["text"])):
        raise ValueError("Ground-truth span is outside the report")
    if injected_report["text"][record["start"]:record["end"]] != record["injected_text"]:
        raise ValueError("Ground-truth span does not point to injected_text")
    kind, original = record["error_type"], record["original_text"]
    if kind in {"numeric_change", "entity_swap"}:
        if not original or original == record["injected_text"] or original not in clean["text"]:
            raise ValueError("Replacement injection is not supported by the clean report")
        rebuilt = clean["text"].replace(original, record["injected_text"], 1)
        if rebuilt != injected_report["text"]:
            raise ValueError("Injected report is not exactly reproducible from clean report")
        if original not in source["text"]:
            raise ValueError("Original replacement text is not present in source")
    elif kind == "unsupported_claim":
        if original is not None or not record["injected_text"].strip():
            raise ValueError("Unsupported claims must be appended and have null original_text")
        if injected_report["text"] != clean["text"] + record["injected_text"]:
            raise ValueError("Unsupported claim is not an exact append to clean report")
        if record["injected_text"].strip() in source["text"]:
            raise ValueError("Unsupported claim text is present verbatim in the source")
