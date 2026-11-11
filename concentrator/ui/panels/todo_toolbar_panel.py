"""Task toolbar: the task actions, the "Move to list" menu and the Show done / Show archived toggles."""

from functools import partial

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QMenu, QToolButton, QWidget

from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.button_snapshot import ButtonSnapshot
from concentrator.presentation.todo.task_menu_snapshot import MoveTargetSnapshot
from concentrator.presentation.todo.todo_toolbar_snapshot import TodoToolbarSnapshot
from concentrator.ui.support.plain_text import without_mnemonic
from concentrator.ui.widgets.snapshot_button import SnapshotButton
from concentrator.ui.widgets.snapshot_check_box import SnapshotCheckBox


class TodoToolbarPanel(QWidget):
    """Emits ``action_requested(int)`` for a button or a toggle and ``move_requested(str)`` for a target list."""

    action_requested = Signal(int)
    move_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build the panel (the buttons are created by the first render).

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._buttons: dict[ActionIdEnum, SnapshotButton] = {}
        self._move = QToolButton(self)
        self._move.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._move_menu = QMenu(self._move)
        self._move.setMenu(self._move_menu)
        self._targets: tuple[MoveTargetSnapshot, ...] = ()
        self._show_done = SnapshotCheckBox(self)
        self._show_archived = SnapshotCheckBox(self)
        self._show_done.action_requested.connect(self.action_requested.emit)
        self._show_archived.action_requested.connect(self.action_requested.emit)

    @property
    def buttons(self) -> dict[ActionIdEnum, SnapshotButton]:
        """Buttons by action (for tests)."""
        return self._buttons

    @property
    def move_button(self) -> QToolButton:
        """The "Move to list" button (for tests)."""
        return self._move

    @property
    def toggles(self) -> tuple[SnapshotCheckBox, SnapshotCheckBox]:
        """Show done and Show archived (for tests)."""
        return self._show_done, self._show_archived

    def render_snapshot(self, snapshot: TodoToolbarSnapshot) -> None:
        """Show the buttons, the move targets and the toggles (idempotent).

        Args:
            snapshot: Toolbar state.
        """
        self.setUpdatesEnabled(False)
        if not self._buttons:
            self._create_buttons(snapshot.menu.buttons)
        for button in snapshot.menu.buttons:
            if button.action is ActionIdEnum.TASK_MOVE:
                self._render_move(button, snapshot.menu.move_targets)
            elif button.action in self._buttons:
                self._buttons[button.action].apply(button)
        self._show_done.apply(snapshot.show_done)
        self._show_archived.apply(snapshot.show_archived)
        self.setUpdatesEnabled(True)

    def _create_buttons(self, buttons: tuple[ButtonSnapshot, ...]) -> None:
        """Create one button per action, in snapshot order, then the toggles.

        Args:
            buttons: Buttons of the first snapshot.
        """
        for button in buttons:
            if button.action is ActionIdEnum.TASK_MOVE:
                self._layout.addWidget(self._move)
                continue
            widget = SnapshotButton(self)
            widget.action_requested.connect(self.action_requested.emit)
            self._buttons[button.action] = widget
            self._layout.addWidget(widget)
        self._layout.addStretch(1)
        self._layout.addWidget(self._show_done)
        self._layout.addWidget(self._show_archived)

    def _render_move(self, button: ButtonSnapshot, targets: tuple[MoveTargetSnapshot, ...]) -> None:
        """Show the "Move to list" button and rebuild its menu when the targets changed.

        Args:
            button: Its state.
            targets: Other lists.
        """
        self._move.setText(button.text)
        self._move.setToolTip(button.tooltip)
        self._move.setEnabled(button.enabled)
        if targets == self._targets:
            return
        self._targets = targets
        self._move_menu.clear()
        for target in targets:
            entry = self._move_menu.addAction(without_mnemonic(target.text))
            entry.setEnabled(target.enabled)
            entry.triggered.connect(partial(self.move_requested.emit, target.list_id))
