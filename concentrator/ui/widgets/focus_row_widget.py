"""One row of the focus queue: check box, text, due badge, list name and remove button."""

from typing import override

from PySide6.QtCore import QPoint, QSignalBlocker, Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QToolButton, QWidget

from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.row_tone_enum import RowToneEnum
from concentrator.presentation.focus.focus_queue_snapshot import FocusRowSnapshot
from concentrator.ui.support.styles import ALERT_PROPERTY, FOCUS_ROW_STYLE, WARNING_PROPERTY, set_dynamic_property

_KEY_ACTIONS = {Qt.Key.Key_Up: ActionIdEnum.FOCUS_MOVE_UP, Qt.Key.Key_Down: ActionIdEnum.FOCUS_MOVE_DOWN}
"""Alt+Up and Alt+Down move the row."""


class FocusRowWidget(QWidget):
    """Shows a ``FocusRowSnapshot``; emits ``action_requested(int)`` and ``menu_requested(QPoint)``.

    The check box shows the stored state again after a click: the next snapshot removes the row once the
    task is done; a click ignored during the cooldown leaves it unchecked. The row takes the keyboard focus
    on a click, so Alt+Up and Alt+Down move it.
    """

    action_requested = Signal(int)
    menu_requested = Signal(QPoint)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build an empty row.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._snapshot: FocusRowSnapshot | None = None
        self._check = QCheckBox(self)
        self._text = QLabel(self)
        self._due = QLabel(self)
        self._list = QLabel(self)
        self._remove = QToolButton(self)
        self._build()
        self._check.clicked.connect(self._emit_complete)
        self._remove.clicked.connect(self._emit_remove)
        self.customContextMenuRequested.connect(self._emit_menu)

    @property
    def item_id(self) -> str:
        """Item shown, ``""`` before the first snapshot."""
        return "" if self._snapshot is None else self._snapshot.item_id

    @property
    def check_box(self) -> QCheckBox:
        """Completes the task (for tests)."""
        return self._check

    @property
    def remove_button(self) -> QToolButton:
        """Takes the task out of the queue (for tests)."""
        return self._remove

    @property
    def text_label(self) -> QLabel:
        """First line of the task (for tests)."""
        return self._text

    @property
    def due_label(self) -> QLabel:
        """Due date badge (for tests)."""
        return self._due

    def apply(self, snapshot: FocusRowSnapshot) -> None:
        """Show a row (idempotent).

        Args:
            snapshot: Row state.
        """
        self._snapshot = snapshot
        blocker = QSignalBlocker(self._check)
        self._check.setChecked(False)
        self._check.setEnabled(snapshot.complete.enabled)
        self._check.setToolTip(snapshot.complete.tooltip)
        blocker.unblock()
        self._text.setText(snapshot.text)
        self._text.setToolTip(snapshot.tooltip)
        self._due.setText(snapshot.due_text)
        self._due.setVisible(bool(snapshot.due_text))
        self._list.setText(snapshot.list_name)
        self._remove.setText(snapshot.remove.text)
        self._remove.setToolTip(snapshot.remove.tooltip)
        self._remove.setEnabled(snapshot.remove.enabled)
        for label in (self._text, self._due):
            set_dynamic_property(label, ALERT_PROPERTY, snapshot.tone is RowToneEnum.ERROR)
            set_dynamic_property(label, WARNING_PROPERTY, snapshot.tone is RowToneEnum.WARNING)

    @override
    def keyPressEvent(self, event: QKeyEvent) -> None:
        action = _KEY_ACTIONS.get(Qt.Key(event.key()))
        if action is None or event.modifiers() != Qt.KeyboardModifier.AltModifier or self._snapshot is None:
            super().keyPressEvent(event)
            return
        item = next((button for button in self._snapshot.menu if button.action is action), None)
        if item is not None and item.enabled:
            self.action_requested.emit(int(action))
        event.accept()

    def _build(self) -> None:
        """Lay out the controls: the text takes the free width."""
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setStyleSheet(FOCUS_ROW_STYLE)
        for label in (self._text, self._due, self._list):
            label.setTextFormat(Qt.TextFormat.PlainText)
        self._check.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._remove.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._remove.setAutoRaise(True)
        self._list.setEnabled(False)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self._check)
        row.addWidget(self._text, 1)
        row.addWidget(self._due)
        row.addWidget(self._list)
        row.addWidget(self._remove)

    def _emit_complete(self) -> None:
        """Send the check box click; the box shows the stored state again until the next snapshot."""
        blocker = QSignalBlocker(self._check)
        self._check.setChecked(False)
        blocker.unblock()
        self.action_requested.emit(int(ActionIdEnum.FOCUS_COMPLETE))

    def _emit_menu(self, pos: QPoint) -> None:
        """Send the screen position of a right click.

        Args:
            pos: Position in the row.
        """
        self.menu_requested.emit(self.mapToGlobal(pos))

    def _emit_remove(self) -> None:
        """Send the x button click."""
        self.action_requested.emit(int(ActionIdEnum.FOCUS_REMOVE))
