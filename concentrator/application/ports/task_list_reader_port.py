"""Reads the lists: the generic read operations, typed with ``TaskListsCollection``."""

from typing import Protocol

from concentrator.application.ports.entity_reader_port import EntityQueryPort
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.todo.task_list import TaskList
from concentrator.domain.todo.task_lists_collection import TaskListsCollection


class TaskListReaderPort(Protocol):
    """Read side of the lists (``AGENTS.md`` section 6.2)."""

    def exists(self, entity_id: str) -> DataResult[bool]:
        """Tell whether a list exists.

        Args:
            entity_id: Id to look for.

        Returns:
            Whether it exists.
        """
        ...

    def read_item(self, entity_id: str) -> DataResult[TaskList]:
        """Return one list.

        Args:
            entity_id: Id to look for.

        Returns:
            The list, or ``ENTITY_NOT_FOUND``.
        """
        ...

    def all_items(self) -> DataResult[TaskListsCollection]:
        """Return every list.

        Returns:
            The lists in stored order.
        """
        ...

    def find(self, query: EntityQueryPort[TaskList]) -> DataResult[TaskListsCollection]:
        """Return the lists matching a query, in stored order.

        Args:
            query: Selection.

        Returns:
            The matching lists.
        """
        ...
