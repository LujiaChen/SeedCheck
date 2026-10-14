from __future__ import annotations

from typing import Any

def review(mode: str, report: dict[str, Any], records: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, int], str]:
    if mode != "mock":
        raise ValueError(f"Unknown mock mode: {mode}")
    return {"issues": []}, {"input_tokens": 0, "output_tokens": 0}, "mock"
