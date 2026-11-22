"""Show done / Show archived toggles, right-aligned in a bar attached to the bottom of the task table."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QWidget

from concentrator.presentation.todo.todo_toolbar_snapshot import TodoToolbarSnapshot
from concentrator.ui.widgets.snapshot_check_box import SnapshotCheckBox


class TodoTogglesPanel(QWidget):
    """Emits ``action_requested(int)`` when Show done or Show archived is clicked."""

    action_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build the bar: free space on the left, then the two toggles.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._show_done = SnapshotCheckBox(self)
        self._show_archived = SnapshotCheckBox(self)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch(1)
        for toggle in (self._show_done, self._show_archived):
            toggle.action_requested.connect(self.action_requested.emit)
            layout.addWidget(toggle)

    @property
    def toggles(self) -> tuple[SnapshotCheckBox, SnapshotCheckBox]:
        """Show done and Show archived (for tests)."""
        return self._show_done, self._show_archived

    def render_snapshot(self, snapshot: TodoToolbarSnapshot) -> None:
        """Show the two toggles of the toolbar section (idempotent).

        Args:
            snapshot: Toolbar state.
        """
        self.setUpdatesEnabled(False)
        self._show_done.apply(snapshot.show_done)
        self._show_archived.apply(snapshot.show_archived)
        self.setUpdatesEnabled(True)
