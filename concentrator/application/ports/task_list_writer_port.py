"""Writes the lists: the generic write operations and changes of several lists in one write."""

from collections.abc import Sequence
from typing import Protocol

from concentrator.application.ports.entity_writer_port import EntityWriterPort
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.todo.task_list import TaskList


class TaskListWriterPort(EntityWriterPort[TaskList], Protocol):
    """Write side of the lists: the nine operations of ``AGENTS.md`` section 6.2, plus bulk changes."""

    def update_many(self, entities: Sequence[TaskList]) -> DataResult[tuple[TaskList, ...]]:
        """Replace several lists in one write, all or nothing.

        Args:
            entities: New versions of existing lists.

        Returns:
            The lists, or ``ENTITY_NOT_FOUND`` (nothing written).
        """
        ...

    def delete_many(self, entity_ids: Sequence[str]) -> DataResult[tuple[TaskList, ...]]:
        """Remove several lists in one write, all or nothing.

        Args:
            entity_ids: Ids of the lists to remove.

        Returns:
            The removed lists, or ``ENTITY_NOT_FOUND`` (nothing written).
        """
        ...
