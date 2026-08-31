import pytest

from app.collections.ingest.resolver import ColumnResolutionError, resolve_columns

EXPECTED = {"a": "A_Col", "b": "B_Col"}


def test_exact_match_success() -> None:
    header = ("A_Col", "B_Col", "Extra")
    assert resolve_columns("Sheet", header, EXPECTED) == {"a": 0, "b": 1}


def test_missing_column_raises_with_all_missing_headers() -> None:
    header = ("A_Col", "Something_Else")
    with pytest.raises(ColumnResolutionError) as exc_info:
        resolve_columns("Sheet", header, EXPECTED)
    assert exc_info.value.missing_headers == ["B_Col"]


def test_multiple_missing_columns_all_reported() -> None:
    header = ("Unrelated",)
    with pytest.raises(ColumnResolutionError) as exc_info:
        resolve_columns("Sheet", header, EXPECTED)
    assert exc_info.value.missing_headers == ["A_Col", "B_Col"]
