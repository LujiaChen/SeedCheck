import json
from pathlib import Path

import pytest
from jsonschema import ValidationError, validate

ROOT = Path(__file__).resolve().parents[1]


def load(relative_path):
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


SCHEMA = load("schemas/injection_record.schema.json")
EXAMPLES = [
    load("data/examples/injection_record_001_numeric.json"),
    load("data/examples/injection_record_002_entity.json"),
    load("data/examples/injection_record_003_unsupported.json"),
]


def test_examples_are_valid():
    for example in EXAMPLES:
        validate(example, SCHEMA)


def test_example_injection_ids_are_unique():
    injection_ids = [example["injection_id"] for example in EXAMPLES]
    assert len(injection_ids) == len(set(injection_ids))


def test_missing_injected_text_is_rejected():
    bad = dict(EXAMPLES[0])
    del bad["injected_text"]
    with pytest.raises(ValidationError):
        validate(bad, SCHEMA)


def test_error_type_must_be_supported():
    bad = dict(EXAMPLES[0], error_type="omission")
    with pytest.raises(ValidationError):
        validate(bad, SCHEMA)


def test_negative_position_is_rejected():
    bad = dict(EXAMPLES[0], start=-1)
    with pytest.raises(ValidationError):
        validate(bad, SCHEMA)


def test_extra_field_is_rejected():
    bad = dict(EXAMPLES[0], secret="not allowed")
    with pytest.raises(ValidationError):
        validate(bad, SCHEMA)


def test_span_and_text_semantics_are_checked_against_injected_report():
    report_texts = {
        "rep_001_inj": "Harbor Works Ltd. opened its second plant in Windsor in 2019. The plant employs 420 people and produces 1,200 pumps per month.",
        "rep_002_inj": "Harbor Works Ltd. opened its second plant in London in 2019.",
        "rep_003_inj": "Harbor Works Ltd. opened its second plant in Windsor in 2019. The company won a national design award in 2024.",
    }

    for record in EXAMPLES:
        report_text = report_texts[record["report_id"]]
        assert record["end"] >= record["start"]
        assert report_text[record["start"] : record["end"]] == record["injected_text"]

        if record["original_text"] is None:
            assert record["error_type"] == "unsupported_claim"
        else:
            assert record["original_text"] != record["injected_text"]


def test_unsupported_claim_can_have_no_original_text():
    record = EXAMPLES[2]
    assert record["error_type"] == "unsupported_claim"
    assert record["original_text"] is None
