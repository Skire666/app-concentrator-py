"""Catalog keys built from enums: action labels and error messages.

Static keys are written as literals where they are used, so the catalog architecture test can check
them; the keys built here are checked by enum-driven tests.
"""

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_issue import ValidationIssue
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.field_error_snapshot import FieldErrorSnapshot


def action_label_key(action: ActionIdEnum) -> str:
    """Catalog key of the label of the controls bound to an action.

    Args:
        action: Action.

    Returns:
        ``action.<name_lowercase>``.
    """
    return f"action.{action.name.lower()}"


def action_tooltip_key(action: ActionIdEnum) -> str:
    """Catalog key of the optional tooltip of an action.

    Args:
        action: Action.

    Returns:
        ``action.<name_lowercase>.tooltip``.
    """
    return f"{action_label_key(action)}.tooltip"


def error_message_key(code: ErrorCodeEnum) -> str:
    """Catalog key of the message of an error code.

    Args:
        code: Error code.

    Returns:
        ``error.<name_lowercase>``.
    """
    return f"error.{code.name.lower()}"


class UiTexts:
    """Translates action labels and validation issues."""

    def __init__(self, translator: TranslatorPort) -> None:
        """Create the helper.

        Args:
            translator: Current-language translator.
        """
        self._translator = translator

    def action_label(self, action: ActionIdEnum, **params: object) -> str:
        """Return the translated label of an action.

        Args:
            action: Action.
            **params: Placeholder values of the label (``Snooze {minutes} min``).

        Returns:
            The label.
        """
        return self._translator.tr(action_label_key(action), **params)

    def action_tooltip(self, action: ActionIdEnum, **params: object) -> str:
        """Return the translated tooltip of an action.

        Args:
            action: Action.
            **params: Placeholder values of the tooltip.

        Returns:
            The tooltip, ``""`` when the catalog defines none.
        """
        key = action_tooltip_key(action)
        return self._translator.tr(key, **params) if self._translator.has(key) else ""

    def issue_message(self, issue: ValidationIssue) -> str:
        """Return the translated message of one issue, with its parameters filled in.

        Args:
            issue: Issue to describe.

        Returns:
            The message.
        """
        return self._translator.tr(error_message_key(issue.code), **dict(issue.params))

    def field_message(self, result: ValidationResult, field: str) -> str:
        """Return the inline message of a form field (failures and warnings).

        Args:
            result: Validation of a form draft.
            field: Field path of the rules; ``sound`` also covers ``sound.kind``.

        Returns:
            The message of the first issue of the field, ``""`` when the field is valid.
        """
        issue = next((issue for issue in result.issues if issue.field.split(".")[0] == field), None)
        return "" if issue is None else self.issue_message(issue)

    def field_errors(self, result: ValidationResult) -> tuple[FieldErrorSnapshot, ...]:
        """Return one inline error per failing issue.

        Args:
            result: Validation of a form draft.

        Returns:
            The inline errors, in issue order.
        """
        return tuple(
            FieldErrorSnapshot(field=issue.field, message=self.issue_message(issue))
            for issue in result.issues
            if issue.is_failure
        )
