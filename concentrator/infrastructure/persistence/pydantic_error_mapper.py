"""Pydantic ``ValidationError`` -> coded issues (``AGENTS.md`` section 7.1)."""

from typing import Final

from pydantic import ValidationError
from pydantic_core import ErrorDetails

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.severity_enum import SeverityEnum
from concentrator.domain.common.validation_issue import ValidationIssue
from concentrator.domain.common.validation_result import ValidationResult

_EXACT_CODES: Final = {
    "missing": ErrorCodeEnum.STORAGE_FIELD_MISSING,
    "extra_forbidden": ErrorCodeEnum.STORAGE_FIELD_UNEXPECTED,
}
_TYPE_SUFFIXES: Final = ("_type", "_parsing")


def code_for_error_type(error_type: str) -> ErrorCodeEnum:
    """Choose the storage code of one pydantic error type.

    Args:
        error_type: ``type`` of a pydantic error, for example ``int_parsing``.

    Returns:
        ``STORAGE_FIELD_MISSING``, ``STORAGE_FIELD_UNEXPECTED``, ``STORAGE_FIELD_INVALID_TYPE`` (types
        ending in ``_type`` or ``_parsing``) or ``STORAGE_FIELD_INVALID_VALUE`` (anything else).
    """
    exact = _EXACT_CODES.get(error_type)
    if exact is not None:
        return exact
    if error_type.endswith(_TYPE_SUFFIXES):
        return ErrorCodeEnum.STORAGE_FIELD_INVALID_TYPE
    return ErrorCodeEnum.STORAGE_FIELD_INVALID_VALUE


def issue_from_error(error: ErrorDetails) -> ValidationIssue:
    """Convert one pydantic error.

    Args:
        error: One entry of ``ValidationError.errors()``.

    Returns:
        The issue; ``field`` is the joined ``loc`` (``task_lists.0.name``).
    """
    field_path = ".".join(str(part) for part in error["loc"])
    return ValidationIssue(code=code_for_error_type(error["type"]), severity=SeverityEnum.ERROR, field=field_path)


def validation_from_error(error: ValidationError) -> ValidationResult:
    """Convert a whole ``ValidationError``: one issue per pydantic error, in order.

    Args:
        error: The exception caught right after ``model_validate_json``.

    Returns:
        The failure.
    """
    return ValidationResult.of(*(issue_from_error(item) for item in error.errors(include_url=False)))
