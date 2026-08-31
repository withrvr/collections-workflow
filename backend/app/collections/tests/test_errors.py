import pytest

from app.collections.errors import PipelineError


def test_pipeline_error_is_a_real_exception() -> None:
    error = PipelineError(code="FILE_CORRUPT", stage="load", user_message="Bad file.")
    assert isinstance(error, Exception)
    with pytest.raises(PipelineError):
        raise error


def test_pipeline_error_str_includes_code_and_message() -> None:
    error = PipelineError(code="FILE_CORRUPT", stage="load", user_message="Bad file.")
    assert str(error) == "[FILE_CORRUPT] Bad file."


def test_pipeline_error_detail_defaults_to_empty_dict() -> None:
    error = PipelineError(code="X", stage="load", user_message="msg")
    assert error.detail == {}
