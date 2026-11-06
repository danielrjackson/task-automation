"""Compatibility diagnostics follow the same section aliases as the model."""

from copy import deepcopy

import pytest

from taskautomation.task_validator import validate_schema_compatibility


@pytest.mark.parametrize("labels", [
    ("critical", "high", "medium", "low"),
    ("Critical", "High", "Medium", "Low"),
    ("critical", "High", "medium", "Low"),
])
def test_present_alias_sections_are_not_reported_missing(labels):
    """Canonical, display and mixed accepted aliases receive equivalent diagnostics."""
    data = {label: [] for label in labels}
    data.update(archive=[], metadata={"version": "1.0"})
    before = deepcopy(data)
    result = validate_schema_compatibility(data)
    assert result.is_valid
    assert result.warnings == []
    assert data == before


def test_missing_section_diagnostic_names_only_absent_sections():
    """Existing display aliases must not appear in the missing-section warning."""
    result = validate_schema_compatibility({"High": [], "Medium": []})
    assert result.is_valid
    assert result.warnings == ["Missing priority sections: Critical, Low, archive"]


def test_metadata_warning_is_not_obscured_by_false_missing_sections():
    """An otherwise complete alias document reports only its missing version."""
    data = dict(Critical=[], High=[], Medium=[], Low=[], archive=[], metadata={})
    result = validate_schema_compatibility(data)
    assert result.is_valid
    assert result.warnings == ["No version information in metadata"]


def test_alias_diagnostics_do_not_accept_ambiguous_or_invalid_data():
    """Better warnings preserve the model's rejection of conflicting aliases."""
    for data in ({"High": [], "high": []}, {"High": "invalid"}, {"HIGH": [], "tasks": []}):
        assert not validate_schema_compatibility(data).is_valid


def test_invalid_metadata_error_identifies_its_field():
    """The blocking metadata diagnostic identifies the field consistently."""
    result = validate_schema_compatibility({"metadata": "invalid"})
    assert not result.is_valid
    assert result.errors == ["Field 'metadata' must be a dictionary"]
