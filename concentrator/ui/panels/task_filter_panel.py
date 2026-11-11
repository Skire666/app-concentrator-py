"""Filter bar above the task table: due date filter, "Recurring only", search, scope and counter."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from concentrator.presentation.todo.task_filter_snapshot import TaskFilterSnapshot
from concentrator.ui.widgets.search_box_widget import SearchBoxWidget
from concentrator.ui.widgets.snapshot_check_box import SnapshotCheckBox
from concentrator.ui.widgets.snapshot_combo_box import SnapshotComboBox


class TaskFilterPanel(QWidget):
    """Emits the intents of the filter bar; ``render_snapshot`` shows a ``TaskFilterSnapshot``.

    Signals:
        due_selected(int): Index of the due date filter chosen.
        scope_selected(int): Index of the scope chosen.
        action_requested(int): "Recurring only" clicked.
        search_changed(str): Text of the search field, on every change.
    """

    due_selected = Signal(int)
    scope_selected = Signal(int)
    action_requested = Signal(int)
    search_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build the bar.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._due = SnapshotComboBox(self)
        self._recurring = SnapshotCheckBox(self)
        self._search = SearchBoxWidget(self)
        self._scope = SnapshotComboBox(self)
        self._counter = QLabel(self)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._due)
        layout.addWidget(self._recurring)
        layout.addWidget(self._search, 1)
        layout.addWidget(self._scope)
        layout.addWidget(self._counter)
        self._due.index_selected.connect(self.due_selected.emit)
        self._scope.index_selected.connect(self.scope_selected.emit)
        self._recurring.action_requested.connect(self.action_requested.emit)
        self._search.search_changed.connect(self.search_changed.emit)

    @property
    def due_box(self) -> SnapshotComboBox:
        """Due date filter (for tests)."""
        return self._due

    @property
    def scope_box(self) -> SnapshotComboBox:
        """Scope (for tests)."""
        return self._scope

    @property
    def recurring_box(self) -> SnapshotCheckBox:
        """The "Recurring only" toggle (for tests)."""
        return self._recurring

    @property
    def search_box(self) -> SearchBoxWidget:
        """Search field (for tests)."""
        return self._search

    @property
    def counter_label(self) -> QLabel:
        """Counter (for tests)."""
        return self._counter

    def render_snapshot(self, snapshot: TaskFilterSnapshot) -> None:
        """Show the filters and the counter (idempotent).

        Args:
            snapshot: Filter bar state.
        """
        self.setUpdatesEnabled(False)
        self._due.apply(snapshot.due)
        self._recurring.apply(snapshot.recurring_only)
        self._search.apply(snapshot.search)
        self._scope.apply(snapshot.scope)
        self._counter.setText(snapshot.counter)
        self.setUpdatesEnabled(True)
