"""Task table of the current list (``TODO_TABLE``): rows, selection, sort, check boxes, keyboard."""

import logging
from typing import Final

from concentrator.application.ports.clock_port import ClockPort
from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.todo.link_detector import LinkDetector
from concentrator.domain.todo.task_sort_key_enum import TaskSortKeyEnum
from concentrator.domain.todo.tasks_collection import TasksCollection
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.date_time_formatter import DateTimeFormatter
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.common.table_snapshot import TableRowSnapshot, TableSnapshot
from concentrator.presentation.todo.task_actions import TaskActions
from concentrator.presentation.todo.task_menu_builder import TaskMenuBuilder
from concentrator.presentation.todo.task_row_formatter import (
    COLUMN_SORT_KEYS,
    LIST_COLUMN,
    STATE_COLUMN,
    TaskRowFormatter,
)
from concentrator.presentation.todo.task_table_snapshot import TaskTableSnapshot
from concentrator.presentation.todo.todo_tabs_presenter import TODO_SECTIONS
from concentrator.presentation.todo.todo_view import TodoView

_logger = logging.getLogger(__name__)

SELECTION_SECTIONS: Final = (
    RenderSectionEnum.TODO_TOOLBAR,
    RenderSectionEnum.TODO_TABLE,
    RenderSectionEnum.TODO_DETAILS,
    RenderSectionEnum.TODO_HISTORY,
)
"""Sections that depend on the selected tasks."""


class TaskTablePresenter:
    """Builds ``TODO_TABLE`` from the current list; the selection is kept by task id across renders.

    Rows show the due marks of the current minute: ``on_tick`` re-renders when the local minute changes,
    so a task becomes overdue on time.
    """

    def __init__(
        self,
        translator: TranslatorPort,
        gate: ActionGate,
        renderer: RenderCoordinator,
        *,
        view: TodoView,
        actions: TaskActions,
        clock: ClockPort,
        menu: TaskMenuBuilder,
        links: LinkDetector,
    ) -> None:
        """Create the presenter.

        Args:
            translator: Current-language translator.
            gate: Runs every user action.
            renderer: Receives the render requests.
            view: Current list, filters, sort and selection.
            actions: Task actions (check boxes, keyboard, context menu).
            clock: Current local time (due marks).
            menu: Builds the context menu (same actions as the toolbar).
            links: Finds the links of the texts.
        """
        self._translator = translator
        self._gate = gate
        self._renderer = renderer
        self._view = view
        self._actions = actions
        self._clock = clock
        self._menu = menu
        self._rows = TaskRowFormatter(translator, DateTimeFormatter(translator, clock), links)
        self._minute = self._current_minute()

    def build_snapshot(self) -> TaskTableSnapshot:
        """Describe the table now.

        Returns:
            The snapshot.
        """
        state = self._view.state
        tasks = self._view.visible()
        selected = set(state.selected_ids)
        selection = tuple(index for index, task in enumerate(tasks) if task.id in selected)
        table = TableSnapshot(
            columns=self._rows.columns(),
            rows=self._table_rows(tasks, all_lists=state.query().all_lists),
            selection=selection,
            empty_text=self._translator.tr("todo.table.empty"),
            check_column=STATE_COLUMN,
            sort_column=COLUMN_SORT_KEYS.index(state.sort_key) if state.sort_key in COLUMN_SORT_KEYS else -1,
            sort_descending=state.descending,
            hidden_columns=() if state.query().all_lists else (LIST_COLUMN,),
        )
        menu = self._menu.build(self._view.selected(), self._view.lists(), state.list_id)
        return TaskTableSnapshot(table=table, menu=menu)

    def _table_rows(self, tasks: TasksCollection, *, all_lists: bool) -> tuple[TableRowSnapshot, ...]:
        """Describe the rows.

        Args:
            tasks: Tasks shown, in display order.
            all_lists: Whether the List column is shown.

        Returns:
            One row per task.
        """
        now = self._clock.now_local()
        names = {item.id: item.name for item in self._view.lists()} if all_lists else {}
        return tuple(self._rows.row(task, now, names.get(task.list_id, "")) for task in tasks)

    def on_selection_changed(self, task_ids: tuple[str, ...]) -> None:
        """Remember the selected tasks; the toolbar and the details follow.

        Args:
            task_ids: Keys of the selected rows, in table order.
        """
        if self._view.state.select_tasks(task_ids):
            self._renderer.request(*SELECTION_SECTIONS)

    def on_sort_requested(self, column: int) -> None:
        """Sort by a column (a second click reverses the order; ``TODO_SORT``); some columns do not sort.

        Args:
            column: Header clicked.
        """
        if not 0 <= column < len(COLUMN_SORT_KEYS):
            _logger.warning("Sort column %d is not handled", column)
            return
        key = COLUMN_SORT_KEYS[column]
        if key is not None:
            self._gate.run(ActionIdEnum.TODO_SORT, lambda: self._sorted(key))
        self._renderer.request(RenderSectionEnum.TODO_TABLE)

    def on_check_toggled(self, task_id: str) -> None:
        """Complete or reopen a task from its check box or with Space.

        Args:
            task_id: Task of the row.
        """
        self._actions.toggle_done(task_id)
        self._renderer.request(*TODO_SECTIONS)

    def on_selection_toggled(self) -> None:
        """Space: complete the open selected tasks, or reopen the done ones when none is open."""
        self._actions.toggle_selection()
        self._renderer.request(*TODO_SECTIONS)

    def on_activated(self, task_id: str) -> None:
        """Open the task dialog (double click or Enter on a row).

        Args:
            task_id: Task of the row.
        """
        self._actions.edit(task_id)
        self._renderer.request(*TODO_SECTIONS)

    def on_tick(self) -> None:
        """Re-render when the local minute changes (overdue and today marks)."""
        minute = self._current_minute()
        if minute != self._minute:
            self._minute = minute
            self._renderer.request(RenderSectionEnum.TODO_TABLE)

    def _sorted(self, key: TaskSortKeyEnum) -> ValidationResult:
        """Apply a sort.

        Args:
            key: Sort key of the column.

        Returns:
            Success.
        """
        self._view.state.sort_by(key)
        return ValidationResult.success()

    def _current_minute(self) -> tuple[int, int, int, int, int]:
        """Local minute, for the tick check.

        Returns:
            Year, month, day, hour and minute.
        """
        now = self._clock.now_local()
        return (now.year, now.month, now.day, now.hour, now.minute)
