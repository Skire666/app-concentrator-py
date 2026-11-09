"""Read use cases of the timer favorites."""

from concentrator.application.ports.timer_preset_reader_port import TimerPresetReaderPort
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.timer.timer_limits import TimerLimits
from concentrator.domain.timer.timer_preset import TimerPreset
from concentrator.domain.timer.timer_presets_collection import TimerPresetsCollection


class PresetQueries:
    """Favorites in display order, one favorite, and their limits."""

    def __init__(self, reader: TimerPresetReaderPort, limits: TimerLimits) -> None:
        """Create the queries.

        Args:
            reader: Favorites reader.
            limits: Bounds from ``concentrator.ini``.
        """
        self._reader = reader
        self._limits = limits

    @property
    def limits(self) -> TimerLimits:
        """Bounds of the favorites (label length, number, duration range)."""
        return self._limits

    def presets(self) -> TimerPresetsCollection:
        """Return the favorites.

        Returns:
            The favorites in display order (empty if they cannot be read, never after startup).
        """
        return self._reader.all_items().value_or(TimerPresetsCollection()).ordered()

    def preset(self, preset_id: str) -> DataResult[TimerPreset]:
        """Return one favorite.

        Args:
            preset_id: Id of the favorite.

        Returns:
            The favorite, or ``ENTITY_NOT_FOUND``.
        """
        return self._reader.read_item(preset_id)
