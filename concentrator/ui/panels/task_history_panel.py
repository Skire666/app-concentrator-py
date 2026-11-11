"""History tab of the details pane: the events of the selected task, newest first."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QListWidget, QVBoxLayout, QWidget

from concentrator.presentation.todo.task_history_snapshot import TaskHistorySnapshot


class TaskHistoryPanel(QWidget):
    """Read-only list of lines; ``render_snapshot`` shows a ``TaskHistorySnapshot``."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build the tab.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._lines = QListWidget(self)
        self._lines.setWordWrap(True)
        self._empty = QLabel(self)
        self._empty.setTextFormat(Qt.TextFormat.PlainText)
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout = QVBoxLayout(self)
        layout.addWidget(self._empty)
        layout.addWidget(self._lines, 1)

    @property
    def lines(self) -> tuple[str, ...]:
        """Lines shown (for tests)."""
        return tuple(self._lines.item(row).text() for row in range(self._lines.count()))

    def render_snapshot(self, snapshot: TaskHistorySnapshot) -> None:
        """Show the events or the hint (idempotent).

        Args:
            snapshot: Tab state.
        """
        self.setUpdatesEnabled(False)
        if self.lines != snapshot.lines:
            self._lines.clear()
            self._lines.addItems(list(snapshot.lines))
        has_task = not snapshot.empty_text
        self._lines.setVisible(has_task)
        self._empty.setText(snapshot.empty_text)
        self._empty.setVisible(not has_task)
        self.setUpdatesEnabled(True)
