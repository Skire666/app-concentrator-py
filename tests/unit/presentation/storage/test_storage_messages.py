import pytest

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.severity_enum import SeverityEnum
from concentrator.domain.common.validation_issue import ValidationIssue
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.presentation.storage.storage_messages import MAX_ISSUES_SHOWN, StorageMessages, field_label_key
from tests.fakes.fake_translator import FakeTranslator


@pytest.mark.parametrize(
    ("field", "key"),
    [
        ("settings.language", "field.settings.language"),
        ("task_lists.0.name", "field.task_lists.name"),
        ("tasks.12.links.3.target", "field.tasks.links.target"),
        ("schema_version", "field.schema_version"),
    ],
)
def test_field_label_key_drops_indexes(field: str, key: str) -> None:
    assert field_label_key(field) == key


def test_line_with_field_uses_its_label() -> None:
    issue = ValidationIssue(ErrorCodeEnum.STORAGE_FIELD_INVALID_TYPE, SeverityEnum.ERROR, "settings.language")

    line = StorageMessages(FakeTranslator()).line(issue)

    assert line == (
        "en:storage.issue.with_field(field=en:field.settings.language,message=en:error.storage_field_invalid_type)"
    )


def test_line_without_label_falls_back_to_the_path() -> None:
    translator = FakeTranslator(missing=frozenset({"field.tasks.title"}))
    issue = ValidationIssue(ErrorCodeEnum.STORAGE_FIELD_MISSING, SeverityEnum.ERROR, "tasks.3.title")

    assert "field=tasks.3.title" in StorageMessages(translator).line(issue)


def test_global_issue_is_the_message_with_its_parameters() -> None:
    result = ValidationResult.failure(ErrorCodeEnum.STORAGE_SYNTAX_INVALID, line=3, column=6)

    assert StorageMessages(FakeTranslator()).lines(result) == ("en:error.storage_syntax_invalid(line=3,column=6)",)


def test_lines_show_the_first_failures_then_how_many_more() -> None:
    issues = [ValidationIssue(ErrorCodeEnum.STORAGE_FIELD_MISSING, SeverityEnum.ERROR, f"f{n}") for n in range(8)]
    warning = ValidationIssue(ErrorCodeEnum.STORAGE_BACKUP_FAILED, SeverityEnum.WARNING)

    lines = StorageMessages(FakeTranslator()).lines(ValidationResult.of(warning, *issues))

    assert len(lines) == MAX_ISSUES_SHOWN + 1
    assert "field=en:field.f0" in lines[0]
    assert lines[-1] == "en:storage.issue.more.other(count=3)"


def test_first_describes_the_first_failure_or_nothing() -> None:
    messages = StorageMessages(FakeTranslator())

    assert messages.first(ValidationResult.failure(ErrorCodeEnum.STORAGE_DISK_FULL)) == "en:error.storage_disk_full"
    assert not messages.first(ValidationResult.success())
