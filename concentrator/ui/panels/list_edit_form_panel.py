"""Fields of the list dialog: name, description and priority."""

from PySide6.QtCore import QSignalBlocker, Signal
from PySide6.QtWidgets import QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QVBoxLayout, QWidget

from concentrator.presentation.todo.list_edit_snapshot import ListEditSnapshot
from concentrator.ui.support.styles import INVALID_INPUT_STYLE, INVALID_PROPERTY, set_dynamic_property
from concentrator.ui.widgets.field_error_label import FieldErrorLabel
from concentrator.ui.widgets.snapshot_button import SnapshotButton
from concentrator.ui.widgets.snapshot_combo_box import SnapshotComboBox
from concentrator.ui.widgets.text_fields import apply_text


class ListEditFormPanel(QWidget):
    """Emits the edits of the fields and ``action_requested(int)`` for Save and Cancel.

    Signals:
        name_changed(str): Name as typed.
        description_changed(str): Description as typed.
        priority_selected(int): Index of the chosen priority.
    """

    name_changed = Signal(str)
    description_changed = Signal(str)
    priority_selected = Signal(int)
    action_requested = Signal(int)

    def __init__(self, spacing_px: int, parent: QWidget | None = None) -> None:
        """Build the fields.

        Args:
            spacing_px: Space between the parts of the dialog.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setStyleSheet(INVALID_INPUT_STYLE)
        self._name = QLineEdit(self)
        self._name.setClearButtonEnabled(True)
        self._name_caption = QLabel(self)
        self._name_error = FieldErrorLabel(self)
        self._description = QPlainTextEdit(self)
        self._description_caption = QLabel(self)
        self._description_error = FieldErrorLabel(self)
        self._priority = SnapshotComboBox(self)
        self._priority_caption = QLabel(self)
        self._save = SnapshotButton(self)
        self._cancel = SnapshotButton(self)
        self._name.textEdited.connect(self.name_changed.emit)
        self._description.textChanged.connect(lambda: self.description_changed.emit(self._description.toPlainText()))
        self._priority.index_selected.connect(self.priority_selected.emit)
        self._save.action_requested.connect(self.action_requested.emit)
        self._cancel.action_requested.connect(self.action_requested.emit)
        self._build_layout(spacing_px)

    @property
    def name_input(self) -> QLineEdit:
        """Name field (for tests and focus)."""
        return self._name

    @property
    def description_input(self) -> QPlainTextEdit:
        """Description field (for tests)."""
        return self._description

    @property
    def priority_input(self) -> SnapshotComboBox:
        """Priority field (for tests)."""
        return self._priority

    @property
    def name_error(self) -> FieldErrorLabel:
        """Inline error of the name (for tests)."""
        return self._name_error

    @property
    def buttons(self) -> tuple[SnapshotButton, SnapshotButton]:
        """Save and Cancel (for tests)."""
        return self._save, self._cancel

    def render_snapshot(self, snapshot: ListEditSnapshot) -> None:
        """Show the draft without emitting the field signals.

        Args:
            snapshot: Dialog state.
        """
        self.setUpdatesEnabled(False)
        name = snapshot.name
        self._name_caption.setText(name.label)
        if self._name.text() != name.text:
            blocker = QSignalBlocker(self._name)
            self._name.setText(name.text)
            blocker.unblock()
        self._name.setPlaceholderText(name.placeholder)
        set_dynamic_property(self._name, INVALID_PROPERTY, bool(name.error))
        self._name_error.set_error(name.error)
        self._description_caption.setText(snapshot.description.label)
        apply_text(self._description, self._description_error, snapshot.description)
        self._priority_caption.setText(snapshot.priority.label)
        self._priority.apply(snapshot.priority)
        self._save.apply(snapshot.save)
        self._cancel.apply(snapshot.cancel)
        self.setUpdatesEnabled(True)

    def _build_layout(self, spacing_px: int) -> None:
        """Name, description, priority, buttons.

        Args:
            spacing_px: Space between the parts.
        """
        form = QFormLayout()
        form.addRow(self._name_caption, self._name)
        form.addRow(QLabel(self), self._name_error)
        form.addRow(self._priority_caption, self._priority)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self._save)
        buttons.addWidget(self._cancel)
        layout = QVBoxLayout(self)
        layout.setSpacing(spacing_px)
        layout.addLayout(form)
        layout.addWidget(self._description_caption)
        layout.addWidget(self._description, 1)
        layout.addWidget(self._description_error)
        layout.addLayout(buttons)
