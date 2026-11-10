"""Multi-line text fields driven by a ``TextFieldSnapshot``."""

from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import QPlainTextEdit

from concentrator.presentation.todo.task_edit_snapshot import TextFieldSnapshot
from concentrator.ui.support.styles import INVALID_PROPERTY, set_dynamic_property
from concentrator.ui.widgets.field_error_label import FieldErrorLabel


def apply_text(edit: QPlainTextEdit, error: FieldErrorLabel, field: TextFieldSnapshot) -> None:
    """Show a multi-line text field without moving the cursor of the user.

    Args:
        edit: Text field.
        error: Its inline error.
        field: Field state.
    """
    if edit.toPlainText() != field.text:
        blocker = QSignalBlocker(edit)
        edit.setPlainText(field.text)
        blocker.unblock()
    edit.setPlaceholderText(field.placeholder)
    set_dynamic_property(edit, INVALID_PROPERTY, bool(field.error))
    error.set_error(field.error)
