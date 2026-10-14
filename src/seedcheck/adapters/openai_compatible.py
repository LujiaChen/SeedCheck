"""Small opt-in OpenAI-compatible chat-completions adapter using only stdlib."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


def review(model_id: str, prompt: str, source: str, report: str, max_output_tokens: int = 512, timeout: int = 60) -> tuple[str, dict[str, int]]:
    key = os.environ.get("SEEDCHECK_API_KEY")
    base_url = os.environ.get("SEEDCHECK_BASE_URL")
    if not key or not base_url:
        raise RuntimeError("Real API mode requires SEEDCHECK_API_KEY and SEEDCHECK_BASE_URL")
    url = base_url.rstrip("/") + "/chat/completions"
    payload = {"model": model_id, "temperature": 0, "max_tokens": max_output_tokens, "messages": [
        {"role": "system", "content": prompt},
        {"role": "user", "content": "SOURCE DOCUMENT:\n" + source + "\n\nREPORT:\n" + report},
    ]}
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"API request failed: {exc}") from exc
    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("API response did not contain choices[0].message.content") from exc
    usage = body.get("usage")
    if not isinstance(usage, dict) or "prompt_tokens" not in usage or "completion_tokens" not in usage:
        raise RuntimeError("API response omitted token usage; refusing to record a zero-cost call")
    try:
        input_tokens, output_tokens = int(usage["prompt_tokens"]), int(usage["completion_tokens"])
    except (TypeError, ValueError) as exc:
        raise RuntimeError("API response contained invalid token usage") from exc
    if input_tokens < 0 or output_tokens < 0:
        raise RuntimeError("API response contained negative token usage")
    return content, {"input_tokens": input_tokens, "output_tokens": output_tokens}
