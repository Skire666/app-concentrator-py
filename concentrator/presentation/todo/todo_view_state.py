"""What the TODO manager shows: current list, sort, filters, search and selected tasks.

The list, the sort, the toggles, the due date filter, the scope and the search are layout keys of
``ui-state.ini`` (``layout/todo/*``, ADR-040), so "Reset layout" brings back the defaults. The selection lasts
for the session only.
"""

import logging
from collections.abc import Iterable
from typing import Final

from concentrator.application.todo.due_filter_enum import DueFilterEnum
from concentrator.application.todo.task_filter import TaskFilter
from concentrator.application.todo.task_query import TaskQuery
from concentrator.application.todo.task_scope_enum import TaskScopeEnum
from concentrator.application.todo.todo_defaults import TodoDefaults
from concentrator.domain.todo.task_lists_collection import TaskListsCollection
from concentrator.domain.todo.task_sort_key_enum import TaskSortKeyEnum
from concentrator.presentation.common.layout_keys import (
    LAYOUT_TODO_DUE_FILTER,
    LAYOUT_TODO_LIST,
    LAYOUT_TODO_RECURRING_ONLY,
    LAYOUT_TODO_SCOPE,
    LAYOUT_TODO_SEARCH,
    LAYOUT_TODO_SHOW_ARCHIVED,
    LAYOUT_TODO_SHOW_DONE,
    LAYOUT_TODO_SORT,
    LAYOUT_TODO_SORT_DESCENDING,
)
from concentrator.presentation.common.layout_state_keeper import LayoutStateKeeper
from concentrator.presentation.common.text_search import TextSearch

_logger = logging.getLogger(__name__)

FLAG_ON: Final = "1"
FLAG_OFF: Final = "0"
DEFAULT_SHOW_DONE: Final = True
DEFAULT_SHOW_ARCHIVED: Final = False
DEFAULT_TASK_FILTER: Final = TaskFilter()
DEFAULT_SCOPE: Final = TaskScopeEnum.THIS_LIST


def _flag(value: bool) -> str:
    """Text of a stored toggle.

    Args:
        value: Toggle.

    Returns:
        ``1`` or ``0``.
    """
    return FLAG_ON if value else FLAG_OFF


def _stored_enum[E: (DueFilterEnum, TaskScopeEnum)](stored: str | None, kind: type[E], default: E) -> E:
    """Read a stored enum value.

    Args:
        stored: Text of the layout key, ``None`` when absent.
        kind: Enum class.
        default: Value when nothing, or something not understood, is stored.

    Returns:
        The member.
    """
    if stored is None:
        return default
    member = kind.parse(int(stored)) if stored.isdigit() else None
    if member is None or not member.is_set:
        _logger.warning("Stored %s ignored: %r", kind.__name__, stored)
        return default
    return member


class TodoViewState:
    """Current list, sort, toggles, due date filter, scope, search and the selected tasks."""

    def __init__(self, layout: LayoutStateKeeper, defaults: TodoDefaults) -> None:
        """Create the state with the ``[todo]`` defaults; ``load`` reads the stored values.

        Args:
            layout: ``layout/*`` keys of ``ui-state.ini``.
            defaults: Default sort.
        """
        self._layout = layout
        self._defaults = defaults
        self._list_id = ""
        self._sort_key = defaults.sort_key
        self._descending = defaults.sort_descending
        self._show_done = DEFAULT_SHOW_DONE
        self._show_archived = DEFAULT_SHOW_ARCHIVED
        self._task_filter = DEFAULT_TASK_FILTER
        self._scope = DEFAULT_SCOPE
        self._search = TextSearch()
        self._selected: tuple[str, ...] = ()

    @property
    def list_id(self) -> str:
        """Current list, ``""`` before the first ``follow_lists``."""
        return self._list_id

    @property
    def sort_key(self) -> TaskSortKeyEnum:
        """Column the tasks are sorted by."""
        return self._sort_key

    @property
    def descending(self) -> bool:
        """Whether the highest values come first."""
        return self._descending

    @property
    def show_done(self) -> bool:
        """Whether done tasks are shown."""
        return self._show_done

    @property
    def show_archived(self) -> bool:
        """Whether archived tasks are shown."""
        return self._show_archived

    @property
    def task_filter(self) -> TaskFilter:
        """Due date filter and "Recurring only"."""
        return self._task_filter

    @property
    def scope(self) -> TaskScopeEnum:
        """The current list, or every list."""
        return self._scope

    @property
    def search(self) -> TextSearch:
        """Search typed in the filter bar (empty: every task)."""
        return self._search

    @property
    def selected_ids(self) -> tuple[str, ...]:
        """Selected tasks, in table order."""
        return self._selected

    def load(self) -> None:
        """Read the stored list, sort and toggles; a value not understood takes its default."""
        self._list_id = self._layout.load(LAYOUT_TODO_LIST) or ""
        stored_sort = self._layout.load(LAYOUT_TODO_SORT)
        sort_key = TaskSortKeyEnum.parse(int(stored_sort)) if stored_sort and stored_sort.isdigit() else None
        if stored_sort is not None and (sort_key is None or not sort_key.is_set):
            _logger.warning("Stored task sort ignored: %r", stored_sort)
            sort_key = None
        self._sort_key = sort_key or self._defaults.sort_key
        self._descending = self._stored_flag(LAYOUT_TODO_SORT_DESCENDING, default=self._defaults.sort_descending)
        self._show_done = self._stored_flag(LAYOUT_TODO_SHOW_DONE, default=DEFAULT_SHOW_DONE)
        self._show_archived = self._stored_flag(LAYOUT_TODO_SHOW_ARCHIVED, default=DEFAULT_SHOW_ARCHIVED)
        self._load_filters()

    def _load_filters(self) -> None:
        """Read the stored due date filter, "Recurring only", scope and search."""
        due = _stored_enum(self._layout.load(LAYOUT_TODO_DUE_FILTER), DueFilterEnum, DEFAULT_TASK_FILTER.due)
        recurring = self._stored_flag(LAYOUT_TODO_RECURRING_ONLY, default=DEFAULT_TASK_FILTER.recurring_only)
        self._task_filter = TaskFilter(due=due, recurring_only=recurring)
        self._scope = _stored_enum(self._layout.load(LAYOUT_TODO_SCOPE), TaskScopeEnum, DEFAULT_SCOPE)
        self._search = TextSearch.parse(self._layout.load(LAYOUT_TODO_SEARCH) or "")

    def reset(self) -> None:
        """Back to the defaults after "Reset layout" (the current list stays shown)."""
        self._sort_key = self._defaults.sort_key
        self._descending = self._defaults.sort_descending
        self._show_done = DEFAULT_SHOW_DONE
        self._show_archived = DEFAULT_SHOW_ARCHIVED
        self._task_filter = DEFAULT_TASK_FILTER
        self._scope = DEFAULT_SCOPE
        self._search = TextSearch()

    def follow_lists(self, lists: TaskListsCollection) -> bool:
        """Keep the current list if it still exists, otherwise show the first tab.

        Args:
            lists: Current lists.

        Returns:
            Whether the current list changed.
        """
        if lists.contains(self._list_id):
            return False
        first = lists.first()
        return self.select_list("" if first is None else first.id)

    def select_list(self, list_id: str) -> bool:
        """Show another list; the selection is cleared.

        Args:
            list_id: List to show.

        Returns:
            Whether it changed.
        """
        if list_id == self._list_id:
            return False
        self._list_id = list_id
        self._selected = ()
        self._layout.save(LAYOUT_TODO_LIST, list_id)
        return True

    def sort_by(self, key: TaskSortKeyEnum) -> None:
        """Sort by a column: a new column sorts ascending, the same column reverses the order.

        Args:
            key: Column clicked.
        """
        self._descending = not self._descending if key is self._sort_key else False
        self._sort_key = key
        self._layout.save(LAYOUT_TODO_SORT, str(int(key)))
        self._layout.save(LAYOUT_TODO_SORT_DESCENDING, _flag(self._descending))

    def toggle_show_done(self) -> None:
        """Show or hide the done tasks."""
        self._show_done = not self._show_done
        self._layout.save(LAYOUT_TODO_SHOW_DONE, _flag(self._show_done))

    def toggle_show_archived(self) -> None:
        """Show or hide the archived tasks."""
        self._show_archived = not self._show_archived
        self._layout.save(LAYOUT_TODO_SHOW_ARCHIVED, _flag(self._show_archived))

    def filter_due(self, due: DueFilterEnum) -> None:
        """Show the tasks due in a period.

        Args:
            due: Due date filter.
        """
        self._task_filter = TaskFilter(due=due, recurring_only=self._task_filter.recurring_only)
        self._layout.save(LAYOUT_TODO_DUE_FILTER, str(int(due)))

    def toggle_recurring_only(self) -> None:
        """Show only the tasks that repeat, or every task again."""
        recurring = not self._task_filter.recurring_only
        self._task_filter = TaskFilter(due=self._task_filter.due, recurring_only=recurring)
        self._layout.save(LAYOUT_TODO_RECURRING_ONLY, _flag(recurring))

    def set_scope(self, scope: TaskScopeEnum) -> None:
        """Show the tasks of the current list or of every list.

        Args:
            scope: Lists shown.
        """
        self._scope = scope
        self._layout.save(LAYOUT_TODO_SCOPE, str(int(scope)))

    def set_search(self, query: str) -> bool:
        """Search the tasks.

        Args:
            query: Text typed.

        Returns:
            Whether the search changed.
        """
        if query == self._search.query:
            return False
        self._search = TextSearch.parse(query)
        self._layout.save(LAYOUT_TODO_SEARCH, query)
        return True

    def select_tasks(self, task_ids: Iterable[str]) -> bool:
        """Remember the selected tasks.

        Args:
            task_ids: Selected tasks, in table order.

        Returns:
            Whether the selection changed.
        """
        selected = tuple(dict.fromkeys(task_ids))
        if selected == self._selected:
            return False
        self._selected = selected
        return True

    def reveal(self, list_id: str, task_id: str) -> None:
        """Show a task in the table: its list, no filter, no search, the task selected ("Show in list").

        Args:
            list_id: List of the task.
            task_id: Task to select.
        """
        self.select_list(list_id)
        if self._task_filter != DEFAULT_TASK_FILTER:
            self._task_filter = DEFAULT_TASK_FILTER
            self._layout.save(LAYOUT_TODO_DUE_FILTER, str(int(DEFAULT_TASK_FILTER.due)))
            self._layout.save(LAYOUT_TODO_RECURRING_ONLY, _flag(DEFAULT_TASK_FILTER.recurring_only))
        self.set_search("")
        self._selected = (task_id,)

    def keep_visible(self, visible_ids: Iterable[str]) -> None:
        """Drop from the selection the tasks the table no longer shows (deleted, moved or filtered out).

        Args:
            visible_ids: Tasks of the table.
        """
        visible = set(visible_ids)
        self._selected = tuple(task_id for task_id in self._selected if task_id in visible)

    def query(self) -> TaskQuery:
        """Return the selection and order of the table.

        Returns:
            The query of the current list.
        """
        return TaskQuery(
            list_id=self._list_id,
            show_done=self._show_done,
            show_archived=self._show_archived,
            sort_key=self._sort_key,
            descending=self._descending,
            task_filter=self._task_filter,
            scope=self._scope,
        )

    def _stored_flag(self, key: str, *, default: bool) -> bool:
        """Read a stored toggle.

        Args:
            key: Layout key.
            default: Value when nothing (or something not understood) is stored.

        Returns:
            The toggle.
        """
        stored = self._layout.load(key)
        if stored == FLAG_ON:
            return True
        if stored == FLAG_OFF:
            return False
        if stored is not None:
            _logger.warning("Stored TODO toggle %s ignored: %r", key, stored)
        return default
