"""Edits not stored yet (settings page), resolved before leaving the page, switching files or quitting."""

from dataclasses import dataclass
from typing import Final, Protocol

from concentrator.domain.common.validation_result import ValidationResult
from concentrator.presentation.ports.dialog_port import DialogPort

SAVE_ANSWER: Final = 0
DISCARD_ANSWER: Final = 1
CANCEL_ANSWER: Final = 2


class PendingEdits(Protocol):
    """A form that may hold changes the user has not saved."""

    def has_unsaved_edits(self) -> bool:
        """Tell whether the form differs from the stored values.

        Returns:
            Whether there are unsaved changes.
        """
        ...

    def save_edits(self) -> ValidationResult:
        """Store the changes.

        Returns:
            Success, or the rule or write failure (already shown to the user).
        """
        ...

    def discard_edits(self) -> None:
        """Forget the changes."""
        ...


@dataclass(frozen=True, slots=True, kw_only=True)
class PendingEditsQuestion:
    """Translated texts of the Save / Discard / Cancel question.

    Attributes:
        title: Window title.
        message: Question.
        answers: Labels of Save, Discard and Cancel, in this order.
    """

    title: str
    message: str
    answers: tuple[str, str, str]


def resolve_pending_edits(edits: PendingEdits, dialogs: DialogPort, question: PendingEditsQuestion) -> ValidationResult:
    """Ask what to do with unsaved changes, then do it.

    Args:
        edits: The form.
        dialogs: Shows the question.
        question: Its texts.

    Returns:
        Success to go on (nothing pending, saved or discarded), skipped when the user cancelled, or the
        save failure.
    """
    if not edits.has_unsaved_edits():
        return ValidationResult.success()
    answer = dialogs.choose(question.title, question.message, question.answers, CANCEL_ANSWER)
    if answer == SAVE_ANSWER:
        return edits.save_edits()
    if answer == DISCARD_ANSWER:
        edits.discard_edits()
        return ValidationResult.success()
    return ValidationResult.skipped()
