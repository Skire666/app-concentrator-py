import pytest

from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult


def test_ok_holds_data_and_success() -> None:
    result = DataResult.ok(42)

    assert result.is_success
    assert result.data == 42
    assert result.validation == ValidationResult.success()
    assert result.value_or(0) == 42


def test_ok_keeps_warnings() -> None:
    warning = ValidationResult.warning(ErrorCodeEnum.TEXT_TOO_LONG)

    result = DataResult.ok("text", warning)

    assert result.is_success
    assert result.validation.is_success_with_warnings


def test_ok_with_false_value_is_success() -> None:
    result = DataResult.ok(False)

    assert result.is_success
    assert result.value_or(True) is False


def test_fail_has_no_data_and_returns_default() -> None:
    result: DataResult[int] = DataResult.fail(ValidationResult.failure(ErrorCodeEnum.ENTITY_NOT_FOUND))

    assert not result.is_success
    assert result.data is None
    assert result.validation.error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)
    assert result.value_or(7) == 7


def test_fail_accepts_skipped_validation() -> None:
    result: DataResult[int] = DataResult.fail(ValidationResult.skipped())

    assert not result.is_success
    assert result.validation.is_skipped


def test_ok_rejects_failed_validation() -> None:
    with pytest.raises(ValueError, match="successful"):
        DataResult.ok(1, ValidationResult.failure(ErrorCodeEnum.FORMAT_INVALID))


def test_fail_rejects_successful_validation() -> None:
    with pytest.raises(ValueError, match="failed or skipped"):
        DataResult.fail(ValidationResult.success())
