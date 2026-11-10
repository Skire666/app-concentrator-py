"""One-line field above the table: Enter adds the task to the current list."""

from PySide6.QtCore import QSignalBlocker, Signal
from PySide6.QtWidgets import QLineEdit, QVBoxLayout, QWidget

from concentrator.presentation.todo.quick_add_snapshot import QuickAddSnapshot
from concentrator.ui.support.styles import INVALID_PROPERTY, set_dynamic_property
from concentrator.ui.widgets.field_error_label import FieldErrorLabel


class QuickAddPanel(QWidget):
    """Emits ``text_changed(str)`` while typing and ``submitted(str)`` on Enter."""

    text_changed = Signal(str)
    submitted = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build the field.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._input = QLineEdit(self)
        self._input.setClearButtonEnabled(True)
        self._error = FieldErrorLabel(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._input)
        layout.addWidget(self._error)
        self._input.textEdited.connect(self.text_changed.emit)
        self._input.returnPressed.connect(lambda: self.submitted.emit(self._input.text()))

    @property
    def input(self) -> QLineEdit:
        """The field (for tests and focus)."""
        return self._input

    @property
    def error_text(self) -> str:
        """Message shown under the field (for tests)."""
        return self._error.text() if self._error.isVisibleTo(self) else ""

    def render_snapshot(self, snapshot: QuickAddSnapshot) -> None:
        """Show the text, the hint and the message (idempotent).

        Args:
            snapshot: Field state.
        """
        blocker = QSignalBlocker(self._input)
        if self._input.text() != snapshot.text:
            self._input.setText(snapshot.text)
        self._input.setPlaceholderText(snapshot.placeholder)
        self._input.setToolTip(snapshot.tooltip)
        self._input.setEnabled(snapshot.enabled)
        blocker.unblock()
        self._error.set_error(snapshot.error)
        set_dynamic_property(self._input, INVALID_PROPERTY, bool(snapshot.error))
