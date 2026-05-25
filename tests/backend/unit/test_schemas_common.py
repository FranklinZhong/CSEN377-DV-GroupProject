"""Unit tests for backend.schemas.common response helpers."""

from backend.schemas.common import ok, err


def test_ok_default_meta():
    # SCHEMA-U-01
    result = ok({"key": "value"})
    assert result["success"] is True
    assert result["meta"]["confidence"] == "medium"
    assert result["warnings"] == []
    assert result["data"] == {"key": "value"}


def test_ok_custom_source_and_confidence():
    result = ok([], source="FAERS", confidence="high", report_count=42)
    assert result["meta"]["source"] == "FAERS"
    assert result["meta"]["confidence"] == "high"
    assert result["meta"]["report_count"] == 42


def test_ok_warnings_passed_through():
    result = ok({}, warnings=["Data is incomplete"])
    assert "Data is incomplete" in result["warnings"]


def test_err_shape():
    # SCHEMA-U-02
    result = err("NOT_FOUND", "Drug not found.", suggestions=["Try fuzzy search"])
    assert result["success"] is False
    assert result["error"]["code"] == "NOT_FOUND"
    assert result["error"]["message"] == "Drug not found."
    assert "Try fuzzy search" in result["suggestions"]


def test_err_empty_suggestions_by_default():
    result = err("SOME_ERR", "Something went wrong.")
    assert result["suggestions"] == []
