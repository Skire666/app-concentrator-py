import pytest

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.severity_enum import SeverityEnum
from concentrator.domain.common.validation_issue import ValidationIssue
from concentrator.domain.common.validation_result import ValidationResult


def _issue(
    severity: SeverityEnum, code: ErrorCodeEnum = ErrorCodeEnum.FORMAT_INVALID, field: str = ""
) -> ValidationIssue:
    return ValidationIssue(code=code, severity=severity, field=field)


def test_success_has_no_issue_and_is_success() -> None:
    result = ValidationResult.success()

    assert result.issues == ()
    assert result.severity == SeverityEnum.SUCCESS
    assert result.is_success
    assert not result.is_failure
    assert not result.is_skipped
    assert not result.has_warnings
    assert not result.is_success_with_warnings
    assert result.first_failure is None


def test_skipped_is_neither_success_nor_failure() -> None:
    result = ValidationResult.skipped()

    assert result.severity == SeverityEnum.SKIPPED
    assert result.is_skipped
    assert not result.is_success
    assert not result.is_failure


def test_failure_builds_error_issue_with_text_params() -> None:
    result = ValidationResult.failure(ErrorCodeEnum.VALUE_OUT_OF_RANGE, field="ui.width", min=40, max=400)

    assert result.is_failure
    assert not result.is_success
    assert result.severity == SeverityEnum.ERROR
    assert result.issues == (
        ValidationIssue(
            code=ErrorCodeEnum.VALUE_OUT_OF_RANGE,
            severity=SeverityEnum.ERROR,
            field="ui.width",
            params=(("min", "40"), ("max", "400")),
        ),
    )


def test_warning_is_success_with_warnings() -> None:
    result = ValidationResult.warning(ErrorCodeEnum.TEXT_TOO_LONG, max=10)

    assert result.is_success
    assert result.has_warnings
    assert result.is_success_with_warnings
    assert result.severity == SeverityEnum.WARNING
    assert not result.issues[0].field


def test_of_without_issue_is_success() -> None:
    assert ValidationResult.of().is_success


@pytest.mark.parametrize(
    ("severities", "expected"),
    [
        ((SeverityEnum.WARNING, SeverityEnum.ERROR, SeverityEnum.SUCCESS), SeverityEnum.ERROR),
        ((SeverityEnum.CRITICAL, SeverityEnum.ERROR), SeverityEnum.CRITICAL),
        ((SeverityEnum.WARNING, SeverityEnum.UNKNOWN), SeverityEnum.UNKNOWN),
        ((SeverityEnum.UNKNOWN, SeverityEnum.ERROR), SeverityEnum.ERROR),
        ((SeverityEnum.SKIPPED, SeverityEnum.SUCCESS), SeverityEnum.SUCCESS),
    ],
)
def test_severity_is_worst_rank(severities: tuple[SeverityEnum, ...], expected: SeverityEnum) -> None:
    result = ValidationResult.of(*(_issue(severity) for severity in severities))

    assert result.severity == expected


@pytest.mark.parametrize("severity", [SeverityEnum.UNKNOWN, SeverityEnum.UNSET])
def test_severity_not_understood_is_failure(severity: SeverityEnum) -> None:
    result = ValidationResult.of(_issue(severity))

    assert result.is_failure
    assert not result.is_success
    assert result.first_failure == _issue(severity)


def test_queries_select_codes_fields_and_first_failure() -> None:
    warning = _issue(SeverityEnum.WARNING, ErrorCodeEnum.TEXT_TOO_LONG, "name")
    error = _issue(SeverityEnum.ERROR, ErrorCodeEnum.REQUIRED_VALUE_MISSING, "name")
    other = _issue(SeverityEnum.ERROR, ErrorCodeEnum.FORMAT_INVALID, "path")
    result = ValidationResult.of(warning, error, other)

    assert result.error_codes == (
        ErrorCodeEnum.TEXT_TOO_LONG,
        ErrorCodeEnum.REQUIRED_VALUE_MISSING,
        ErrorCodeEnum.FORMAT_INVALID,
    )
    assert result.issues_for("name") == (warning, error)
    assert result.issues_for("missing") == ()
    assert result.first_failure == error
    assert result.has_warnings
    assert not result.is_success_with_warnings


def test_merge_concatenates_issues_in_order() -> None:
    first = ValidationResult.warning(ErrorCodeEnum.TEXT_TOO_LONG)
    second = ValidationResult.failure(ErrorCodeEnum.FORMAT_INVALID)

    merged = first.merge(ValidationResult.success(), second)

    assert merged.error_codes == (ErrorCodeEnum.TEXT_TOO_LONG, ErrorCodeEnum.FORMAT_INVALID)
    assert merged.is_failure


def test_merge_of_skipped_results_stays_skipped() -> None:
    merged = ValidationResult.skipped().merge(ValidationResult.skipped())

    assert merged.is_skipped


def test_merge_skipped_with_success_is_success() -> None:
    merged = ValidationResult.skipped().merge(ValidationResult.success())

    assert merged.is_success


def test_merge_skipped_with_failure_is_failure() -> None:
    merged = ValidationResult.skipped().merge(ValidationResult.failure(ErrorCodeEnum.FORMAT_INVALID))

    assert merged.is_failure


def test_constructor_rejects_impossible_baseline() -> None:
    with pytest.raises(ValueError, match="baseline"):
        ValidationResult(baseline=SeverityEnum.ERROR)


def test_prefixed_places_issues_under_the_parent_field() -> None:
    result = ValidationResult.of(
        _issue(SeverityEnum.ERROR, field="language"),
        _issue(SeverityEnum.WARNING),
        _issue(SeverityEnum.ERROR, field="a.b"),
    )

    prefixed = result.prefixed("settings")

    assert [issue.field for issue in prefixed.issues] == ["settings.language", "settings", "settings.a.b"]
    assert prefixed.error_codes == result.error_codes
    assert [issue.severity for issue in prefixed.issues] == [issue.severity for issue in result.issues]


def test_prefixed_keeps_the_baseline_and_ignores_an_empty_prefix() -> None:
    skipped = ValidationResult.skipped()
    failure = ValidationResult.failure(ErrorCodeEnum.FORMAT_INVALID, field="x")

    assert skipped.prefixed("settings").is_skipped
    assert failure.prefixed("") is failure
