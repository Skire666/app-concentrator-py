"""Writes the tasks: the generic write operations and changes of several tasks in one write."""

from collections.abc import Sequence
from typing import Protocol

from concentrator.application.ports.entity_writer_port import EntityWriterPort
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.todo.task import Task


class TaskWriterPort(EntityWriterPort[Task], Protocol):
    """Write side of the tasks: the nine operations of ``AGENTS.md`` section 6.2, plus bulk changes."""

    def update_many(self, entities: Sequence[Task]) -> DataResult[tuple[Task, ...]]:
        """Replace several tasks in one write, all or nothing.

        Args:
            entities: New versions of existing tasks.

        Returns:
            The tasks, or ``ENTITY_NOT_FOUND`` (nothing written).
        """
        ...

    def delete_many(self, entity_ids: Sequence[str]) -> DataResult[tuple[Task, ...]]:
        """Remove several tasks in one write, all or nothing.

        Args:
            entity_ids: Ids of the tasks to remove.

        Returns:
            The removed tasks, or ``ENTITY_NOT_FOUND`` (nothing written).
        """
        ...
