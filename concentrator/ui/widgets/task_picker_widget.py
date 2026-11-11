"""Search field proposing tasks in a drop-down (``QCompleter`` fed by the snapshot, no data access)."""

from typing import Final

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QCompleter, QLineEdit, QVBoxLayout, QWidget

from concentrator.presentation.focus.focus_queue_snapshot import FocusFieldSnapshot, PickerChoiceSnapshot

TASK_ID_ROLE: Final = Qt.ItemDataRole.UserRole + 1


class TaskPickerWidget(QWidget):
    """Emits ``text_changed(str)`` while typing and ``picked(str)`` with the task chosen.

    The presenter searches; the completer only shows the entries of the snapshot (unfiltered popup). The
    completer is attached with ``setWidget``, not ``QLineEdit.setCompleter``, so choosing an entry never
    writes its text in the field. Enter without a highlighted entry picks the first one.
    """

    text_changed = Signal(str)
    picked = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build the field and its drop-down.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._input = QLineEdit(self)
        self._input.setClearButtonEnabled(True)
        self._model = QStandardItemModel(self)
        self._completer = QCompleter(self._model, self)
        self._completer.setCompletionMode(QCompleter.CompletionMode.UnfilteredPopupCompletion)
        self._completer.setWidget(self._input)
        self._choices: tuple[PickerChoiceSnapshot, ...] = ()
        self._cleared = 0
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._input)
        self._input.textEdited.connect(self.text_changed.emit)
        self._input.returnPressed.connect(self._pick_first)
        self._completer.activated.connect(self._pick_current)

    @property
    def input(self) -> QLineEdit:
        """The field (for tests and focus)."""
        return self._input

    @property
    def completer(self) -> QCompleter:
        """The drop-down (for tests)."""
        return self._completer

    def apply(self, field: FocusFieldSnapshot, choices: tuple[PickerChoiceSnapshot, ...]) -> None:
        """Show the field and the entries (idempotent).

        Args:
            field: Text, hint and tooltip.
            choices: Tasks matching the text.
        """
        blocker = QSignalBlocker(self._input)
        if self._input.text() != field.text or field.cleared_count != self._cleared:
            self._input.setText(field.text)
        self._cleared = field.cleared_count
        self._input.setPlaceholderText(field.placeholder)
        self._input.setToolTip(field.tooltip)
        blocker.unblock()
        if choices == self._choices:
            return
        self._choices = choices
        self._model.clear()
        for choice in choices:
            entry = QStandardItem(choice.text)
            entry.setData(choice.task_id, TASK_ID_ROLE)
            entry.setEditable(False)
            self._model.appendRow(entry)
        self._show_popup()

    def _show_popup(self) -> None:
        """Open the drop-down while the field has the focus and entries match; close it otherwise."""
        popup = self._completer.popup()
        if self._choices and self._input.hasFocus():
            self._completer.complete()
        elif popup is not None:
            popup.hide()

    def _pick_current(self, _text: str) -> None:
        """Send the task of the entry chosen in the drop-down (the current entry of the popup).

        Args:
            _text: Text of the entry (texts may repeat; the entry carries the task id).
        """
        popup = self._completer.popup()
        task_id = None if popup is None else popup.currentIndex().data(TASK_ID_ROLE)
        if isinstance(task_id, str):
            self.picked.emit(task_id)

    def _pick_first(self) -> None:
        """Enter in the field: send the first entry, if any."""
        if self._choices:
            self.picked.emit(self._choices[0].task_id)
