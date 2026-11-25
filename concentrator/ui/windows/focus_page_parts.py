"""Panels of the Focus page, created in their containers (the page lays them out and wires them)."""

from PySide6.QtWidgets import QSplitter, QTabWidget, QVBoxLayout, QWidget

from concentrator.presentation.timer.timer_layout import TimerLayout
from concentrator.presentation.todo.todo_layout import TodoLayout
from concentrator.ui.panels.presets_panel import PresetsPanel
from concentrator.ui.panels.quick_add_panel import QuickAddPanel
from concentrator.ui.panels.special_options_panel import SpecialOptionsPanel
from concentrator.ui.panels.task_details_panel import TaskDetailsPanel
from concentrator.ui.panels.task_filter_panel import TaskFilterPanel
from concentrator.ui.panels.task_history_panel import TaskHistoryPanel
from concentrator.ui.panels.task_table_panel import TaskTablePanel
from concentrator.ui.panels.timer_panel import TimerPanel
from concentrator.ui.panels.todo_tabs_panel import TodoTabsPanel
from concentrator.ui.panels.todo_toggles_panel import TodoTogglesPanel
from concentrator.ui.panels.todo_toolbar_panel import TodoToolbarPanel


def zone1_bars(zone1: QWidget) -> tuple[TodoTabsPanel, TodoToolbarPanel, QuickAddPanel, TaskFilterPanel]:
    """Create the bars above the task table.

    Args:
        zone1: Container of zone 1.

    Returns:
        List tabs, toolbar, quick add field and filter bar.
    """
    return TodoTabsPanel(zone1), TodoToolbarPanel(zone1), QuickAddPanel(zone1), TaskFilterPanel(zone1)


def table_pane(splitter: QSplitter, todo_layout: TodoLayout) -> tuple[QWidget, TaskTablePanel, TodoTogglesPanel]:
    """Create the task table and the bar of toggles attached to its bottom, in the upper pane of the splitter.

    Args:
        splitter: Table / details splitter.
        todo_layout: Default column widths and share of the task text.

    Returns:
        The pane, the table and the toggles.
    """
    pane = QWidget(splitter)
    table = TaskTablePanel(todo_layout.column_widths_px, todo_layout.text_width_percent, pane)
    toggles = TodoTogglesPanel(pane)
    stack = QVBoxLayout(pane)
    stack.setContentsMargins(0, 0, 0, 0)
    stack.setSpacing(0)
    stack.addWidget(table, 1)
    stack.addWidget(toggles)
    return pane, table, toggles


def info_tabs(splitter: QSplitter) -> tuple[QTabWidget, TaskDetailsPanel, TaskHistoryPanel]:
    """Create the Details and History tabs under the task table.

    Args:
        splitter: Table / details splitter.

    Returns:
        The tab widget and its two panels.
    """
    tabs = QTabWidget(splitter)
    return tabs, TaskDetailsPanel(tabs), TaskHistoryPanel(tabs)


def zone2_panels(timer_layout: TimerLayout, zone2: QWidget) -> tuple[TimerPanel, PresetsPanel, SpecialOptionsPanel]:
    """Create the panels of zone 2.

    Args:
        timer_layout: Font of the timer digits and spacing of the favorites.
        zone2: Container of zone 2.

    Returns:
        Timer, favorites and special options.
    """
    return TimerPanel(timer_layout, zone2), PresetsPanel(timer_layout, zone2), SpecialOptionsPanel(zone2)
