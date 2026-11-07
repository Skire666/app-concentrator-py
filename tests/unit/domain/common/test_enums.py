import pytest

from concentrator.domain.common.error_category_enum import ErrorCategoryEnum
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.severity_enum import SeverityEnum


@pytest.mark.parametrize(
    ("value", "expected"),
    [(4, SeverityEnum.ERROR), (-1, SeverityEnum.UNKNOWN), (0, SeverityEnum.UNSET), (99, SeverityEnum.UNKNOWN)],
)
def test_base_int_enum_parse_maps_unrecognized_values_to_unknown(value: int, expected: SeverityEnum) -> None:
    assert SeverityEnum.parse(value) is expected


@pytest.mark.parametrize(
    ("member", "expected"), [(SeverityEnum.UNKNOWN, False), (SeverityEnum.UNSET, False), (SeverityEnum.SKIPPED, True)]
)
def test_base_int_enum_is_set_excludes_unknown_and_unset(member: SeverityEnum, expected: bool) -> None:
    assert member.is_set is expected


@pytest.mark.parametrize(
    ("member", "expected"),
    [
        (SeverityEnum.UNKNOWN, True),
        (SeverityEnum.UNSET, True),
        (SeverityEnum.SKIPPED, False),
        (SeverityEnum.SUCCESS, False),
        (SeverityEnum.WARNING, False),
        (SeverityEnum.ERROR, True),
        (SeverityEnum.CRITICAL, True),
    ],
)
def test_severity_is_failure(member: SeverityEnum, expected: bool) -> None:
    assert member.is_failure is expected


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (ErrorCodeEnum.UNKNOWN, ErrorCategoryEnum.UNKNOWN),
        (ErrorCodeEnum.UNSET, ErrorCategoryEnum.UNSET),
        (ErrorCodeEnum.REQUIRED_VALUE_MISSING, ErrorCategoryEnum.COMMON),
        (ErrorCodeEnum.STORAGE_FILE_NOT_FOUND, ErrorCategoryEnum.STORAGE),
        (ErrorCodeEnum.STORAGE_FILE_CHANGED_EXTERNALLY, ErrorCategoryEnum.STORAGE),
        (ErrorCodeEnum.CONFIG_KEY_UNEXPECTED, ErrorCategoryEnum.CONFIG),
        (ErrorCodeEnum.CATALOG_KEY_MISSING, ErrorCategoryEnum.CONFIG),
        (ErrorCodeEnum.APP_USER_MODEL_ID_FAILED, ErrorCategoryEnum.SYSTEM),
    ],
)
def test_error_code_category_comes_from_range(code: ErrorCodeEnum, expected: ErrorCategoryEnum) -> None:
    assert code.category is expected


def test_every_set_error_code_has_a_known_category() -> None:
    assert all(code.category.is_set for code in ErrorCodeEnum if code.is_set)
