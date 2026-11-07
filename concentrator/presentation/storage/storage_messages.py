"""Storage failures as translated lines: ``error.<code>`` plus the field label (``AGENTS.md`` section 10)."""

from typing import Final

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.domain.common.validation_issue import ValidationIssue
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.presentation.common.ui_texts import UiTexts

MAX_ISSUES_SHOWN: Final = 5
FIELD_LABEL_PREFIX: Final = "field."
FIELD_SEPARATOR: Final = "."


def field_label_key(field: str) -> str:
    """Catalog key of a field label: the dotted path without list indexes.

    Args:
        field: Dotted path such as ``task_lists.0.name``.

    Returns:
        ``field.task_lists.name``.
    """
    parts = [part for part in field.split(FIELD_SEPARATOR) if part and not part.isdigit()]
    return FIELD_LABEL_PREFIX + FIELD_SEPARATOR.join(parts)


class StorageMessages:
    """Builds the lines of a storage problem in the current language."""

    def __init__(self, translator: TranslatorPort) -> None:
        """Create the helper.

        Args:
            translator: Current-language translator.
        """
        self._translator = translator
        self._texts = UiTexts(translator)

    def lines(self, result: ValidationResult) -> tuple[str, ...]:
        """Describe the first failing issues, then how many more there are.

        Args:
            result: A failed load or save.

        Returns:
            One line per issue (``Language: A value has the wrong type.``), at most ``MAX_ISSUES_SHOWN``
            plus a final "and N more" line.
        """
        failures = [issue for issue in result.issues if issue.is_failure]
        lines = [self.line(issue) for issue in failures[:MAX_ISSUES_SHOWN]]
        hidden = len(failures) - MAX_ISSUES_SHOWN
        if hidden > 0:
            lines.append(self._translator.tr_plural("storage.issue.more", hidden))
        return tuple(lines)

    def first(self, result: ValidationResult) -> str:
        """Describe the first failing issue (status bar).

        Args:
            result: A failed save.

        Returns:
            The line, ``""`` when nothing failed.
        """
        issue = result.first_failure
        return self.line(issue) if issue is not None else ""

    def line(self, issue: ValidationIssue) -> str:
        """Describe one issue, prefixed with its field label when it has a field.

        Args:
            issue: The issue.

        Returns:
            The translated line.
        """
        message = self._texts.issue_message(issue)
        if not issue.field:
            return message
        key = field_label_key(issue.field)
        label = self._translator.tr(key) if self._translator.has(key) else issue.field
        return self._translator.tr("storage.issue.with_field", field=label, message=message)
