import json
from pathlib import Path

import pytest
from jsonschema import ValidationError, validate

from seedcheck.baselines.script import review as baseline_review
from seedcheck.cache import get, key_for, put
from seedcheck.adapters.mock import review as mock_review
from seedcheck.adapters.openai_compatible import review as api_review
from seedcheck.injector import inject, validate_ground_truth
from seedcheck.io import read_json
from seedcheck.reviewer import locate_quote, parse_output, prompt_hash, sentinel_output
from seedcheck.scorer import bootstrap_report_ci, score

ROOT = Path(__file__).resolve().parents[1]
SOURCE = read_json(ROOT / "data/examples/source_001.json")
CLEAN = read_json(ROOT / "data/examples/report_001_clean.json")
INJ_SCHEMA = read_json(ROOT / "schemas/injection_record.schema.json")
OUT_SCHEMA = read_json(ROOT / "schemas/reviewer_output.schema.json")


def plan(kind="numeric_change"):
    values = {
        "numeric_change": {"error_type": kind, "original_text": "240", "injected_text": "420", "explanation": "Changed count."},
        "entity_swap": {"error_type": kind, "original_text": "Windsor", "injected_text": "London", "explanation": "Changed city."},
        "unsupported_claim": {"error_type": kind, "original_text": None, "injected_text": " The company won an award in 2024.", "explanation": "Added claim."},
    }
    return values[kind]


@pytest.mark.parametrize("kind", ["numeric_change", "entity_swap", "unsupported_claim"])
def test_injector_outputs_reproducible_valid_ground_truth(kind):
    report, record = inject(CLEAN, plan(kind), "inj_001")
    validate_ground_truth(SOURCE, CLEAN, report, record, INJ_SCHEMA)
    assert report["report_id"] == record["report_id"]
    assert report["text"][record["start"] : record["end"]] == record["injected_text"]


def test_numeric_injection_rejects_non_numeric_substitution():
    with pytest.raises(ValueError, match="numeric_change"):
        inject(CLEAN, {**plan(), "original_text": "Windsor", "injected_text": "London"}, "inj_001")


def test_injector_rejects_ambiguous_source_text():
    report = dict(CLEAN, text=CLEAN["text"] + " 240")
    with pytest.raises(ValueError, match="exactly one occurrence"):
        inject(report, plan(), "inj_001")


def test_ground_truth_rejects_wrong_offset():
    report, record = inject(CLEAN, plan(), "inj_001")
    record["start"] += 1
    with pytest.raises(ValueError, match="span"):
        validate_ground_truth(SOURCE, CLEAN, report, record, INJ_SCHEMA)


def test_quotes_must_be_unique_verbatim_complete_sentences():
    text = "First fact is supported. Second fact is also supported."
    assert locate_quote(text, "First fact is supported.")[0] == "matched"
    assert locate_quote(text, "fact is supported.")[0] == "invalid_issue"
    assert locate_quote(text, "missing.")[0] == "invalid_issue"
    assert locate_quote("Repeat. Repeat.", "Repeat.")[0] == "ambiguous_match"


def test_scorer_and_sentinels():
    report, record = inject(CLEAN, plan(), "inj_001")
    assert score(report, [record], sentinel_output("oracle", report, [record]))["recall"] == 1
    assert score(report, [record], sentinel_output("null", report, [record]))["recall"] == 0
    assert score(CLEAN, [], sentinel_output("spam", CLEAN, []))["false_positive_count"] > 0
    assert mock_review("mock", report, [record])[0] == {"issues": []}


def test_baseline_detects_numeric_and_entity_changes():
    numeric, _ = inject(CLEAN, plan(), "inj_001")
    entity, _ = inject(CLEAN, plan("entity_swap"), "inj_002")
    assert baseline_review(SOURCE["text"], numeric["text"])["issues"]
    assert baseline_review(SOURCE["text"], entity["text"])["issues"]
    assert baseline_review(SOURCE["text"], CLEAN["text"])["issues"] == []


def test_real_api_adapter_needs_explicit_credentials(monkeypatch):
    monkeypatch.delenv("SEEDCHECK_API_KEY", raising=False)
    monkeypatch.delenv("SEEDCHECK_BASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="requires SEEDCHECK_API_KEY"):
        api_review("example/model", "prompt", "source", "report")


def test_prompt_hash_is_stable_and_sha256():
    assert prompt_hash("frozen") == prompt_hash("frozen")
    assert len(prompt_hash("frozen")) == 64


def test_output_schema_and_cache(tmp_path):
    output = {"issues": []}
    assert parse_output(json.dumps(output), OUT_SCHEMA) == output
    with pytest.raises(ValidationError):
        parse_output('{"issues": [], "extra": true}', OUT_SCHEMA)
    key = key_for({"b": 1, "a": 2})
    assert key == key_for({"a": 2, "b": 1})
    put(tmp_path, key, {"output": output})
    assert get(tmp_path, key) == {"output": output}


def test_report_level_bootstrap_is_reproducible():
    one = bootstrap_report_ci([(1, 1), (0, 1)], iterations=100)
    two = bootstrap_report_ci([(1, 1), (0, 1)], iterations=100)
    assert one == two
    assert one["estimate"] == 0.5
