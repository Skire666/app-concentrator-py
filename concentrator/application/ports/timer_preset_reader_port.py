"""Reads the timer favorites: the generic read operations, typed with ``TimerPresetsCollection``."""

from typing import Protocol

from concentrator.application.ports.entity_reader_port import EntityQueryPort
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.timer.timer_preset import TimerPreset
from concentrator.domain.timer.timer_presets_collection import TimerPresetsCollection


class TimerPresetReaderPort(Protocol):
    """Read side of the favorites (``AGENTS.md`` section 6.2)."""

    def exists(self, entity_id: str) -> DataResult[bool]:
        """Tell whether a favorite exists.

        Args:
            entity_id: Id to look for.

        Returns:
            Whether it exists.
        """
        ...

    def read_item(self, entity_id: str) -> DataResult[TimerPreset]:
        """Return one favorite.

        Args:
            entity_id: Id to look for.

        Returns:
            The favorite, or ``ENTITY_NOT_FOUND``.
        """
        ...

    def all_items(self) -> DataResult[TimerPresetsCollection]:
        """Return every favorite.

        Returns:
            The favorites in stored order (``ordered()`` gives the display order).
        """
        ...

    def find(self, query: EntityQueryPort[TimerPreset]) -> DataResult[TimerPresetsCollection]:
        """Return the favorites matching a query, in stored order.

        Args:
            query: Selection.

        Returns:
            The matching favorites.
        """
        ...
