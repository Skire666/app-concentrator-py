"""Writes the focus queue: the generic write operations and changes of several items in one write."""

from collections.abc import Sequence
from typing import Protocol

from concentrator.application.ports.entity_writer_port import EntityWriterPort
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.focus.focus_item import FocusItem


class FocusItemWriterPort(EntityWriterPort[FocusItem], Protocol):
    """Write side of the focus queue: the nine operations of ``AGENTS.md`` section 6.2, plus bulk changes."""

    def update_many(self, entities: Sequence[FocusItem]) -> DataResult[tuple[FocusItem, ...]]:
        """Replace several items in one write, all or nothing (a move renumbers the queue).

        Args:
            entities: New versions of existing items.

        Returns:
            The items, or ``ENTITY_NOT_FOUND`` (nothing written).
        """
        ...

    def delete_many(self, entity_ids: Sequence[str]) -> DataResult[tuple[FocusItem, ...]]:
        """Remove several items in one write, all or nothing.

        Args:
            entity_ids: Ids of the items to remove.

        Returns:
            The removed items, or ``ENTITY_NOT_FOUND`` (nothing written).
        """
        ...
