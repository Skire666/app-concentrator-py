"""What the TODO manager shows: current list, sort, filters and selected tasks.

The list, the sort and the two toggles are layout keys of ``ui-state.ini`` (``layout/todo/*``, ADR-040), so
"Reset layout" brings back the ``[todo]`` defaults. The selection lasts for the session only.
"""

import logging
from collections.abc import Iterable
from typing import Final

from concentrator.application.todo.task_query import TaskQuery
from concentrator.application.todo.todo_defaults import TodoDefaults
from concentrator.domain.todo.task_lists_collection import TaskListsCollection
from concentrator.domain.todo.task_sort_key_enum import TaskSortKeyEnum
from concentrator.presentation.common.layout_keys import (
    LAYOUT_TODO_LIST,
    LAYOUT_TODO_SHOW_ARCHIVED,
    LAYOUT_TODO_SHOW_DONE,
    LAYOUT_TODO_SORT,
    LAYOUT_TODO_SORT_DESCENDING,
)
from concentrator.presentation.common.layout_state_keeper import LayoutStateKeeper

_logger = logging.getLogger(__name__)

FLAG_ON: Final = "1"
FLAG_OFF: Final = "0"
DEFAULT_SHOW_DONE: Final = True
DEFAULT_SHOW_ARCHIVED: Final = False


def _flag(value: bool) -> str:
    """Text of a stored toggle.

    Args:
        value: Toggle.

    Returns:
        ``1`` or ``0``.
    """
    return FLAG_ON if value else FLAG_OFF


class TodoViewState:
    """Current list, sort key and direction, Show done, Show archived, and the selected tasks."""

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

    def reset(self) -> None:
        """Back to the defaults after "Reset layout" (the current list stays shown)."""
        self._sort_key = self._defaults.sort_key
        self._descending = self._defaults.sort_descending
        self._show_done = DEFAULT_SHOW_DONE
        self._show_archived = DEFAULT_SHOW_ARCHIVED

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
