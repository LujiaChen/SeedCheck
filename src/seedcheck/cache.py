from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def key_for(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def get(cache_dir: str | Path, key: str) -> dict[str, Any] | None:
    path = Path(cache_dir) / (key + ".json")
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def put(cache_dir: str | Path, key: str, value: dict[str, Any]) -> None:
    path = Path(cache_dir) / (key + ".json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
