import json
from pathlib import Path

import pytest
from jsonschema import ValidationError, validate

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas" / "source_doc.schema.json").read_text(encoding="utf-8"))
EXAMPLE = json.loads((ROOT / "data" / "examples" / "source_001.json").read_text(encoding="utf-8"))


def test_example_is_valid():
    validate(EXAMPLE, SCHEMA)


def test_missing_text_is_rejected():
    bad = dict(EXAMPLE)
    del bad["text"]
    with pytest.raises(ValidationError):
        validate(bad, SCHEMA)


def test_extra_field_is_rejected():
    bad = dict(EXAMPLE, secret="not allowed")
    with pytest.raises(ValidationError):
        validate(bad, SCHEMA)
