"""Boolean completion and integer identity fields must not silently coerce."""

import pytest

from taskautomation.task_schema import Subtask, Task, ValidationError, validate_integer


@pytest.mark.parametrize("value", ["false", "true", "", None, 0, 1, []])
def test_subtask_completion_rejects_nonboolean_input(value):
    """A string spelling false must never become a completed subtask."""
    with pytest.raises(ValidationError, match="completed.*boolean"):
        Subtask(dict(name="Synthetic subtask", completed=value))


@pytest.mark.parametrize("value", [False, True])
def test_subtask_completion_preserves_actual_booleans(value):
    """Actual booleans and the omitted-field default retain their meaning."""
    assert Subtask(dict(name="Synthetic subtask", completed=value)).completed is value
    assert Subtask(dict(name="Synthetic subtask")).completed is False


@pytest.mark.parametrize("value", [False, True])
def test_boolean_is_not_an_integer_task_identity(value):
    """Python's bool/int inheritance must not admit a boolean task ID."""
    with pytest.raises(ValidationError, match="integer"):
        validate_integer(value, "id")
    with pytest.raises(ValidationError, match="integer"):
        Task(dict(id=value, title="Synthetic task"))


@pytest.mark.parametrize("value", [-1, 0, 1])
def test_integer_validation_preserves_integer_values(value):
    """Generic integer validation keeps its existing range behavior."""
    assert validate_integer(value, "field") == value
