"""Snapshot of the list dialog (``LIST_EDIT``)."""

from dataclasses import dataclass

from concentrator.presentation.common.button_snapshot import ButtonSnapshot
from concentrator.presentation.settings.settings_snapshot import ChoiceFieldSnapshot
from concentrator.presentation.todo.task_edit_snapshot import TextFieldSnapshot


@dataclass(frozen=True, slots=True, kw_only=True)
class ListEditSnapshot:
    """Everything the list dialog shows.

    Attributes:
        title: Window title ("New list" or "Edit list").
        name: Name (one line).
        description: Description (several lines).
        priority: Priority.
        save: Save button.
        cancel: Cancel button.
    """

    title: str
    name: TextFieldSnapshot
    description: TextFieldSnapshot
    priority: ChoiceFieldSnapshot
    save: ButtonSnapshot
    cancel: ButtonSnapshot
