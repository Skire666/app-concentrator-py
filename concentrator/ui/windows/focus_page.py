"""Menu A page: zone 1 (TODO manager) and zone 2 (timer, focus queue later, favorites, options)."""

from typing import Final

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QSplitter, QTabWidget, QVBoxLayout, QWidget

from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.timer.timer_layout import TimerLayout
from concentrator.presentation.todo.task_details_snapshot import TaskDetailsSnapshot
from concentrator.presentation.todo.task_history_snapshot import TaskHistorySnapshot
from concentrator.presentation.todo.todo_layout import TodoLayout
from concentrator.presentation.todo.todo_presenters import TodoPresenters
from concentrator.ui.panels.presets_panel import PresetsPanel
from concentrator.ui.panels.quick_add_panel import QuickAddPanel
from concentrator.ui.panels.special_options_panel import SpecialOptionsPanel
from concentrator.ui.panels.task_details_panel import TaskDetailsPanel
from concentrator.ui.panels.task_filter_panel import TaskFilterPanel
from concentrator.ui.panels.task_history_panel import TaskHistoryPanel
from concentrator.ui.panels.task_table_panel import TaskTablePanel
from concentrator.ui.panels.timer_panel import TimerPanel
from concentrator.ui.panels.todo_tabs_panel import TodoTabsPanel
from concentrator.ui.panels.todo_toolbar_panel import TodoToolbarPanel

_PERCENT: Final = 100
_DETAILS_TAB: Final = 0
_HISTORY_TAB: Final = 1


def _zone1_bars(zone1: QWidget) -> tuple[TodoTabsPanel, TodoToolbarPanel, QuickAddPanel, TaskFilterPanel]:
    """Create the bars above the task table.

    Args:
        zone1: Container of zone 1.

    Returns:
        List tabs, toolbar, quick add field and filter bar.
    """
    return TodoTabsPanel(zone1), TodoToolbarPanel(zone1), QuickAddPanel(zone1), TaskFilterPanel(zone1)


def _info_tabs(splitter: QSplitter) -> tuple[QTabWidget, TaskDetailsPanel, TaskHistoryPanel]:
    """Create the Details and History tabs under the task table.

    Args:
        splitter: Table / details splitter.

    Returns:
        The tab widget and its two panels.
    """
    tabs = QTabWidget(splitter)
    return tabs, TaskDetailsPanel(tabs), TaskHistoryPanel(tabs)


def _zone2_panels(timer_layout: TimerLayout, zone2: QWidget) -> tuple[TimerPanel, PresetsPanel, SpecialOptionsPanel]:
    """Create the panels of zone 2.

    Args:
        timer_layout: Font of the timer digits and spacing of the favorites.
        zone2: Container of zone 2.

    Returns:
        Timer, favorites and special options.
    """
    return TimerPanel(timer_layout, zone2), PresetsPanel(timer_layout, zone2), SpecialOptionsPanel(zone2)


class FocusPage(QWidget):
    """Zone 1 and zone 2 in a horizontal splitter.

    Zone 1, top to bottom: list tabs, toolbar, quick add, filter bar, then the task table above the details
    pane in a vertical splitter (the details pane can be collapsed). Zone 2, top to bottom: timer, the room of the
    focus queue (phase 7), favorites, special options.
    """

    def __init__(
        self,
        zone1_ratio_percent: int,
        timer_layout: TimerLayout,
        todo_layout: TodoLayout,
        parent: QWidget | None = None,
    ) -> None:
        """Build the page.

        Args:
            zone1_ratio_percent: Initial share of zone 1 (``ui.zone1_ratio_percent``).
            timer_layout: Font of the timer digits and spacing of the favorites.
            todo_layout: Table and details split, default column widths and spacing of zone 1.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._ratio = zone1_ratio_percent
        self._todo_layout = todo_layout
        self._splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self._splitter.setChildrenCollapsible(False)
        zone1 = QWidget(self._splitter)
        self._new_task = QShortcut(zone1)
        self._tabs, self._toolbar, self._quick_add, self._filters = _zone1_bars(zone1)
        self._todo_splitter = QSplitter(Qt.Orientation.Vertical, zone1)
        self._table = TaskTablePanel(todo_layout.column_widths_px, todo_layout.text_width_percent, self._todo_splitter)
        self._info, self._details, self._history = _info_tabs(self._todo_splitter)
        zone2 = QWidget(self._splitter)
        self._timer, self._presets, self._options = _zone2_panels(timer_layout, zone2)
        self._build_zone1(zone1, todo_layout.spacing_px)
        self._build_zone2(zone2, timer_layout.spacing_px)
        self._build_splitter(zone1, zone2)
        self.reset_splitter()
        self.reset_todo_splitter()

    @property
    def timer_panel(self) -> TimerPanel:
        """Timer at the top of zone 2."""
        return self._timer

    @property
    def presets_panel(self) -> PresetsPanel:
        """Favorites, below the room of the focus queue."""
        return self._presets

    @property
    def special_options_panel(self) -> SpecialOptionsPanel:
        """Special options at the bottom of zone 2."""
        return self._options

    @property
    def new_task_shortcut(self) -> QShortcut:
        """Ctrl+N anywhere in zone 1 (for tests)."""
        return self._new_task

    @property
    def tabs_panel(self) -> TodoTabsPanel:
        """List tabs of zone 1."""
        return self._tabs

    @property
    def toolbar_panel(self) -> TodoToolbarPanel:
        """Task toolbar of zone 1."""
        return self._toolbar

    @property
    def quick_add_panel(self) -> QuickAddPanel:
        """Quick add field of zone 1."""
        return self._quick_add

    @property
    def filter_panel(self) -> TaskFilterPanel:
        """Filter bar of zone 1."""
        return self._filters

    @property
    def table_panel(self) -> TaskTablePanel:
        """Task table of zone 1."""
        return self._table

    @property
    def details_panel(self) -> TaskDetailsPanel:
        """Details tab of zone 1."""
        return self._details

    @property
    def history_panel(self) -> TaskHistoryPanel:
        """History tab of zone 1."""
        return self._history

    @property
    def info_tabs(self) -> QTabWidget:
        """Details and History tabs under the table."""
        return self._info

    def connect_todo(self, todo: TodoPresenters, renderer: RenderCoordinator) -> None:
        """Connect the zone 1 panels to their presenters and register their sections.

        Args:
            todo: Presenters of the TODO manager.
            renderer: Render coordinator.
        """
        self._tabs.action_requested.connect(todo.tabs.on_action_requested)
        self._tabs.list_action_requested.connect(todo.tabs.on_list_action_requested)
        self._toolbar.action_requested.connect(todo.toolbar.on_action_requested)
        self._toolbar.move_requested.connect(todo.toolbar.on_move_requested)
        self._quick_add.text_changed.connect(todo.quick_add.on_text_changed)
        self._quick_add.submitted.connect(todo.quick_add.on_submitted)
        self._connect_filters(todo)
        self._connect_table(todo)
        self._register_todo(todo, renderer)

    def _connect_filters(self, todo: TodoPresenters) -> None:
        """Connect the filter bar to its presenter.

        Args:
            todo: Presenters of the TODO manager.
        """
        filters = todo.filters
        self._filters.due_selected.connect(filters.on_due_selected)
        self._filters.scope_selected.connect(filters.on_scope_selected)
        self._filters.action_requested.connect(filters.on_action_requested)
        self._filters.search_changed.connect(filters.on_search_changed)

    def _register_todo(self, todo: TodoPresenters, renderer: RenderCoordinator) -> None:
        """Register the sections of zone 1.

        Args:
            todo: Presenters of the TODO manager.
            renderer: Render coordinator.
        """
        renderer.register(RenderSectionEnum.TODO_TABS, todo.tabs.build_snapshot, self._tabs.render_snapshot)
        renderer.register(RenderSectionEnum.TODO_TOOLBAR, todo.toolbar.build_snapshot, self._toolbar.render_snapshot)
        renderer.register(RenderSectionEnum.QUICK_ADD, todo.quick_add.build_snapshot, self._quick_add.render_snapshot)
        renderer.register(RenderSectionEnum.TODO_FILTERS, todo.filters.build_snapshot, self._filters.render_snapshot)
        renderer.register(RenderSectionEnum.TODO_TABLE, todo.table.build_snapshot, self._table.render_snapshot)
        renderer.register(RenderSectionEnum.TODO_DETAILS, todo.details.build_snapshot, self._render_details)
        renderer.register(RenderSectionEnum.TODO_HISTORY, todo.history.build_snapshot, self._render_history)

    def _render_details(self, snapshot: TaskDetailsSnapshot) -> None:
        """Show the Details tab and its caption.

        Args:
            snapshot: Details state.
        """
        self._details.render_snapshot(snapshot)
        self._info.setTabText(_DETAILS_TAB, snapshot.title)

    def _render_history(self, snapshot: TaskHistorySnapshot) -> None:
        """Show the History tab and its caption.

        Args:
            snapshot: History state.
        """
        self._history.render_snapshot(snapshot)
        self._info.setTabText(_HISTORY_TAB, snapshot.title)

    def splitter_state(self) -> QByteArray:
        """Return the zone 1 / zone 2 splitter blob to persist."""
        return self._splitter.saveState()

    def restore_splitter_state(self, state: QByteArray) -> bool:
        """Restore a persisted zone splitter blob.

        Args:
            state: Blob from ``splitter_state``.

        Returns:
            Whether Qt accepted it.
        """
        return self._splitter.restoreState(state)

    def reset_splitter(self) -> None:
        """Apply the ini ratio (sizes are distributed proportionally to the available width)."""
        self._splitter.setSizes([self._ratio, _PERCENT - self._ratio])

    def todo_splitter_state(self) -> QByteArray:
        """Return the table / details splitter blob to persist."""
        return self._todo_splitter.saveState()

    def restore_todo_splitter_state(self, state: QByteArray) -> bool:
        """Restore a persisted table / details splitter blob.

        Args:
            state: Blob from ``todo_splitter_state``.

        Returns:
            Whether Qt accepted it.
        """
        return self._todo_splitter.restoreState(state)

    def reset_todo_splitter(self) -> None:
        """Apply the ini share of the task table (``todo.default_table_ratio_percent``)."""
        ratio = self._todo_layout.table_ratio_percent
        self._todo_splitter.setSizes([ratio, _PERCENT - ratio])

    def splitter_sizes(self) -> list[int]:
        """Return the current zone widths (for tests).

        Returns:
            Width of zone 1 and zone 2 in pixels.
        """
        return self._splitter.sizes()

    def _connect_table(self, todo: TodoPresenters) -> None:
        """Connect the task table, and Ctrl+N of zone 1, to their presenters.

        Args:
            todo: Presenters of the TODO manager.
        """
        table = self._table
        table.selection_changed.connect(todo.table.on_selection_changed)
        table.sort_requested.connect(todo.table.on_sort_requested)
        table.check_toggled.connect(todo.table.on_check_toggled)
        table.activated.connect(todo.table.on_activated)
        table.toggle_requested.connect(todo.table.on_selection_toggled)
        table.action_requested.connect(todo.toolbar.on_action_requested)
        table.move_requested.connect(todo.toolbar.on_move_requested)
        table.link_activated.connect(todo.links.on_table_link)
        table.link_requested.connect(todo.links.on_selected_link)
        self._details.link_activated.connect(todo.links.on_selected_link)
        self._new_task.activated.connect(lambda: todo.toolbar.on_action_requested(int(ActionIdEnum.TASK_NEW)))

    def _build_splitter(self, zone1: QWidget, zone2: QWidget) -> None:
        """Zone 1 and zone 2 side by side, shared by the ini ratio.

        Args:
            zone1: Container of zone 1.
            zone2: Container of zone 2.
        """
        self._splitter.addWidget(zone1)
        self._splitter.addWidget(zone2)
        self._splitter.setStretchFactor(0, self._ratio)
        self._splitter.setStretchFactor(1, _PERCENT - self._ratio)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._splitter)

    def _build_zone1(self, zone1: QWidget, spacing_px: int) -> None:
        """Tabs, toolbar, quick add, filters, then table and details.

        Args:
            zone1: Container of zone 1.
            spacing_px: Space between its parts.
        """
        self._new_task.setKey(QKeySequence(QKeySequence.StandardKey.New))
        self._new_task.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self._todo_splitter.addWidget(self._table)
        self._info.addTab(self._details, "")
        self._info.addTab(self._history, "")
        self._todo_splitter.addWidget(self._info)
        self._todo_splitter.setCollapsible(0, False)
        stack = QVBoxLayout(zone1)
        stack.setSpacing(spacing_px)
        stack.addWidget(self._tabs)
        stack.addWidget(self._toolbar)
        stack.addWidget(self._quick_add)
        stack.addWidget(self._filters)
        stack.addWidget(self._todo_splitter, 1)

    def _build_zone2(self, zone2: QWidget, spacing_px: int) -> None:
        """Timer, the room of the focus queue, favorites, special options.

        Args:
            zone2: Container of zone 2.
            spacing_px: Space between its parts.
        """
        stack = QVBoxLayout(zone2)
        stack.setSpacing(spacing_px)
        stack.addWidget(self._timer)
        stack.addStretch(1)
        stack.addWidget(self._presets)
        stack.addWidget(self._options)
