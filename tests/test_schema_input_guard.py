"""Regression coverage for rejecting malformed input before dictionary access."""

import pytest

from taskautomation.validation_utils import validate_task_schema


@pytest.mark.parametrize("value", [None, [], "not a dictionary", 123])
def test_nondictionary_input_returns_structured_validation_error(value):
    """Reject an invalid container without leaking an AttributeError."""
    result = validate_task_schema(value)
    assert result.is_valid is False
    assert result.errors == ["Task data must be a dictionary"]
    assert result.warnings == []
    assert result.context == {
        "validation_type": "schema",
        "task_data_type": str(type(value)),
    }


def test_dictionary_like_object_does_not_get_its_keys_called():
    """A keys method is insufficient to qualify as a dictionary input."""

    class NotADictionary:
        def keys(self):
            raise AssertionError("keys must not be accessed before the type guard")

    result = validate_task_schema(NotADictionary())
    assert result.is_valid is False
    assert result.errors == ["Task data must be a dictionary"]


def test_valid_dictionary_retains_key_context():
    """The early invalid-type return must not change valid dictionary behavior."""
    result = validate_task_schema({"title": "Synthetic task", "task_id": 1})
    assert result.is_valid is True
    assert result.context == {
        "validation_type": "schema",
        "task_data_keys": ["title", "task_id"],
    }
