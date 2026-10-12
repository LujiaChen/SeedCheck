import json
from pathlib import Path

import pytest
from jsonschema import ValidationError, validate

ROOT = Path(__file__).resolve().parents[1]


def load(relative_path):
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


SCHEMA = load("schemas/report.schema.json")
CLEAN = load("data/examples/report_001_clean.json")
INJECTED = load("data/examples/report_001_inj.json")


def test_clean_example_is_valid():
    validate(CLEAN, SCHEMA)


def test_injected_example_is_valid():
    validate(INJECTED, SCHEMA)


def test_missing_variant_is_rejected():
    bad = dict(CLEAN)
    del bad["variant"]
    with pytest.raises(ValidationError):
        validate(bad, SCHEMA)


def test_bad_report_id_is_rejected():
    bad = dict(CLEAN, report_id="rep_1_clean")
    with pytest.raises(ValidationError):
        validate(bad, SCHEMA)


def test_variant_must_match_report_id():
    bad = dict(CLEAN, variant="injected")
    with pytest.raises(ValidationError):
        validate(bad, SCHEMA)


def test_extra_field_is_rejected():
    bad = dict(CLEAN, secret="not allowed")
    with pytest.raises(ValidationError):
        validate(bad, SCHEMA)
