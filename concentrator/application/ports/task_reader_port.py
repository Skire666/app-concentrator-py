"""Reads the tasks: the generic read operations, typed with ``TasksCollection``."""

from typing import Protocol

from concentrator.application.ports.entity_reader_port import EntityQueryPort
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.todo.task import Task
from concentrator.domain.todo.tasks_collection import TasksCollection


class TaskReaderPort(Protocol):
    """Read side of the tasks (``AGENTS.md`` section 6.2)."""

    def exists(self, entity_id: str) -> DataResult[bool]:
        """Tell whether a task exists.

        Args:
            entity_id: Id to look for.

        Returns:
            Whether it exists.
        """
        ...

    def read_item(self, entity_id: str) -> DataResult[Task]:
        """Return one task.

        Args:
            entity_id: Id to look for.

        Returns:
            The task, or ``ENTITY_NOT_FOUND``.
        """
        ...

    def all_items(self) -> DataResult[TasksCollection]:
        """Return every task.

        Returns:
            The tasks in stored order.
        """
        ...

    def find(self, query: EntityQueryPort[Task]) -> DataResult[TasksCollection]:
        """Return the tasks matching a query, in stored order.

        Args:
            query: Selection.

        Returns:
            The matching tasks.
        """
        ...
