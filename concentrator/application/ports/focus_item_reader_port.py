"""Reads the focus queue: the generic read operations, typed with ``FocusItemsCollection``."""

from typing import Protocol

from concentrator.application.ports.entity_reader_port import EntityQueryPort
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.focus.focus_item import FocusItem
from concentrator.domain.focus.focus_items_collection import FocusItemsCollection


class FocusItemReaderPort(Protocol):
    """Read side of the focus queue (``AGENTS.md`` section 6.2)."""

    def exists(self, entity_id: str) -> DataResult[bool]:
        """Tell whether an item exists.

        Args:
            entity_id: Id to look for.

        Returns:
            Whether it exists.
        """
        ...

    def read_item(self, entity_id: str) -> DataResult[FocusItem]:
        """Return one item.

        Args:
            entity_id: Id to look for.

        Returns:
            The item, or ``ENTITY_NOT_FOUND``.
        """
        ...

    def all_items(self) -> DataResult[FocusItemsCollection]:
        """Return the whole queue.

        Returns:
            The items in stored order (``ordered()`` gives the queue order).
        """
        ...

    def find(self, query: EntityQueryPort[FocusItem]) -> DataResult[FocusItemsCollection]:
        """Return the items matching a query, in stored order.

        Args:
            query: Selection.

        Returns:
            The matching items.
        """
        ...
