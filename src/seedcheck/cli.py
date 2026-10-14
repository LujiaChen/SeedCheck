from __future__ import annotations

import argparse
import json
from pathlib import Path

from jsonschema import validate

from .experiment import run
from .injector import inject, validate_ground_truth
from .io import read_json, write_json
from .reviewer import sentinel_output
from .scorer import score


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser(prog="seedcheck", description="Run reproducible source-grounded report review experiments.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("smoke", help="Run the local deterministic end-to-end sanity suite")
    run_parser = sub.add_parser("run", help="Run all configured reviewer conditions against a dataset")
    run_parser.add_argument("--config", default="configs/experiment.example.json")
    run_parser.add_argument("--mode", choices=["mock", "replay", "api", "sentinel:oracle", "sentinel:null", "sentinel:spam"])
    inject_parser = sub.add_parser("inject", help="Create an injected report and its ground-truth record")
    inject_parser.add_argument("--report", required=True)
    inject_parser.add_argument("--plan", required=True)
    inject_parser.add_argument("--injection-id", required=True)
    inject_parser.add_argument("--output-report", required=True)
    inject_parser.add_argument("--output-record", required=True)
    args = parser.parse_args()
    root = _root()
    if args.command == "inject":
        report, plan = read_json(args.report), read_json(args.plan)
        injected, record = inject(report, plan, args.injection_id)
        validate(record, read_json(root / "schemas/injection_record.schema.json"))
        write_json(args.output_report, injected)
        write_json(args.output_record, record)
        return
    if args.command == "run":
        result = run(args.config, args.mode)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    # Smoke checks all three error classes and sentinel behavior on ephemeral examples.
    source = read_json(root / "data/examples/source_001.json")
    clean = read_json(root / "data/examples/report_001_clean.json")
    scenarios = [
        {"error_type": "numeric_change", "original_text": "240", "injected_text": "420", "explanation": "smoke numeric"},
        {"error_type": "entity_swap", "original_text": "Windsor", "injected_text": "London", "explanation": "smoke entity"},
        {"error_type": "unsupported_claim", "original_text": None, "injected_text": " The company won a design award.", "explanation": "smoke unsupported"},
    ]
    schema = read_json(root / "schemas/injection_record.schema.json")
    for i, plan in enumerate(scenarios, start=1):
        report, record = inject(clean, plan, f"inj_{i:03}")
        validate_ground_truth(source, clean, report, record, schema)
        assert score(report, [record], sentinel_output("oracle", report, [record]))["recall"] == 1.0
        assert score(report, [record], sentinel_output("null", report, [record]))["recall"] == 0.0
        assert score(report, [record], sentinel_output("spam", report, [record]))["recall"] == 1.0
    clean_score = score(clean, [], sentinel_output("spam", clean, []))
    assert clean_score["false_positive_count"] > 0
    print("Smoke passed: 3 injection types; oracle recall=1; null recall=0; spam flags clean report.")


if __name__ == "__main__":
    main()
