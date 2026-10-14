from __future__ import annotations

import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import FormatChecker, validate

from . import cache
from .adapters import mock, openai_compatible
from .baselines.script import review as script_review
from .io import read_json
from .reviewer import parse_output, prompt_hash, sentinel_output
from .scorer import bootstrap_report_ci, score


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_cases(directory: str | Path) -> list[dict[str, Any]]:
    cases = []
    for path in sorted(Path(directory).glob("*.json")):
        value = read_json(path)
        if {"source", "report", "records"} <= value.keys():
            cases.append(value)
    return cases


def run(config_path: str | Path, mode_override: str | None = None) -> dict[str, Any]:
    config = read_json(config_path)
    root = Path(config_path).resolve().parent.parent
    dataset = (root / config["dataset"]).resolve()
    cache_dir = root / config.get("cache_dir", ".seedcheck-cache")
    ledger_path = root / config.get("ledger", "results/ledger.jsonl")
    prompt_path = root / config.get("prompt", "prompts/reviewer_v1.txt")
    prompt = prompt_path.read_text(encoding="utf-8")
    phash = prompt_hash(prompt)
    lock_path = prompt_path.with_suffix(".sha256")
    if lock_path.exists() and lock_path.read_text(encoding="utf-8").strip() != phash:
        raise ValueError(f"Prompt hash differs from frozen lock {lock_path}; re-freeze only after development review and before scoring held-out cases")
    output_schema = read_json(root / "schemas/reviewer_output.schema.json")
    run_schema = read_json(root / "schemas/run_record.schema.json")
    cases = _load_cases(dataset)
    if not cases:
        raise ValueError(f"No case JSON files found under {dataset}")
    price_cfg = config.get("prices_usd_per_million_tokens", {})
    price_cfg = price_cfg.get("models", price_cfg)
    budget = float(config.get("budget_usd", 0))
    spent = 0.0
    results = []
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    for cfg in config["configurations"]:
        config_id = cfg["id"]
        mode = mode_override or cfg.get("mode", "mock")
        for case in cases:
            source, report, records = case["source"], case["report"], case.get("records", [])
            key = cache.key_for({"config": cfg, "mode": mode, "prompt_hash": phash, "source": source["text"], "report": report["text"]})
            cached = cache.get(cache_dir, key) if mode in {"replay", "api"} else None
            start_time = time.time()
            run_status, usage, error = "ok", {"input_tokens": 0, "output_tokens": 0}, None
            try:
                if cfg.get("kind") == "baseline":
                    output = script_review(source["text"], report["text"])
                elif mode == "sentinel:oracle":
                    output, run_status = sentinel_output("oracle", report, records), "mock"
                elif mode == "sentinel:null":
                    output, run_status = sentinel_output("null", report, records), "mock"
                elif mode == "sentinel:spam":
                    output, run_status = sentinel_output("spam", report, records), "mock"
                elif cached:
                    output, usage, run_status = cached["output"], cached["usage"], "replay"
                elif mode == "replay":
                    raise FileNotFoundError(f"No cached response for {config_id}/{report['report_id']}; replay never falls back to mock")
                elif mode == "api":
                    model = cfg.get("model_id")
                    if not model:
                        raise ValueError(f"{config_id} api mode needs model_id")
                    # Conservative preflight estimate based on characters; use configured rate card only.
                    rates = price_cfg.get(model, {})
                    input_rate = rates.get("input_per_million_tokens")
                    output_rate = rates.get("output_per_million_tokens")
                    if input_rate is None or output_rate is None:
                        raise ValueError(f"No configured token prices for {model}; set prices_usd_per_million_tokens before API calls")
                    max_output_tokens = int(config.get("max_output_tokens", 512))
                    # Reserve 50% headroom over the character-based input estimate and the full output cap.
                    estimate_tokens = ((len(prompt) + len(source["text"]) + len(report["text"]) + 2) * 3 // 2) + 256
                    projected = spent + estimate_tokens * float(input_rate) / 1_000_000 + max_output_tokens * float(output_rate) / 1_000_000
                    if projected >= budget:
                        raise RuntimeError(f"Budget preflight blocked API call: projected input cost ${projected:.6f} reaches budget ${budget:.6f}")
                    raw, usage = openai_compatible.review(model, prompt, source["text"], report["text"], max_output_tokens=max_output_tokens)
                    output = parse_output(raw, output_schema)
                    run_status = "ok"
                    cache.put(cache_dir, key, {"raw": raw, "output": output, "usage": usage})
                else:
                    output, usage, run_status = mock.review(mode if mode in {"oracle", "null", "spam", "mock"} else "mock", report, records)
                validate(output, output_schema)
            except Exception as exc:
                run_status, error, output = "error", str(exc), {"issues": []}
            rates = price_cfg.get(cfg.get("model_id", ""), {})
            in_rate, out_rate = rates.get("input_per_million_tokens"), rates.get("output_per_million_tokens")
            cost = None if in_rate is None or out_rate is None else (usage["input_tokens"] * float(in_rate) + usage["output_tokens"] * float(out_rate)) / 1_000_000
            if cost is not None:
                spent += cost
            row = {
                "run_id": uuid.uuid4().hex, "config_id": config_id,
                "model_id": cfg.get("model_id"), "mode": mode,
                "parameters": {"temperature": 0 if mode == "api" else None, "max_output_tokens": int(config.get("max_output_tokens", 512))},
                "report_id": report["report_id"], "status": run_status, "prompt_hash": phash,
                "response_hash": _hash(json.dumps(output, sort_keys=True)) if run_status != "error" else None,
                "usage": usage, "estimated_cost_usd": cost,
            }
            if error:
                row["error"] = error
            ledger_row = {"timestamp": datetime.now(timezone.utc).isoformat(), **row}
            validate(ledger_row, run_schema, format_checker=FormatChecker())
            with ledger_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(ledger_row, ensure_ascii=False) + "\n")
            result = score(report, records, output)
            cost_per_detection = cost / result["detected"] if cost is not None and result["detected"] else None
            results.append({"config_id": config_id, "mode": mode, "elapsed_seconds": round(time.time() - start_time, 3), "estimated_cost_per_true_detection_usd": cost_per_detection, "score": result, "run": row})
    summaries = {}
    for cfg in config["configurations"]:
        rows = [r for r in results if r["config_id"] == cfg["id"]]
        summaries[cfg["id"]] = bootstrap_report_ci([(r["score"]["detected"], r["score"]["injection_count"]) for r in rows if r["score"]["injection_count"] > 0])
        clean_rows = [r for r in rows if r["score"]["variant"] == "clean"]
        summaries[cfg["id"]]["false_positive_rate_ci"] = bootstrap_report_ci([(int(r["score"]["false_positive_count"] > 0), 1) for r in clean_rows])
    return {"prompt_hash": phash, "cases": len(cases), "estimated_cost_usd": spent, "budget_usd": budget, "results": results, "recall_ci_by_config": summaries}
