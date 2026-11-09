"""The favorites of the timer, ordered by position."""

from typing import Final, Self

from concentrator.domain.common.entity_collection import EntityCollection
from concentrator.domain.timer.duration import Duration
from concentrator.domain.timer.timer_preset import TimerPreset

FIRST_POSITION: Final = 0


class TimerPresetsCollection(EntityCollection[TimerPreset]):
    """Group logic of the favorites: display order, next position, duration lookup.

    Readers use ``ordered()`` (by position); a new favorite goes last. Favorites are not moved (owner
    decision at the phase 3 review). ``TimerPresetRules`` checks the limit and the unique durations.
    """

    def ordered(self) -> Self:
        """Sort by position (stable: equal positions keep the stored order).

        Returns:
            The favorites in display order.
        """
        return self.sorted_by(lambda preset: preset.position)

    def next_position(self) -> int:
        """Return the position of a favorite added at the end.

        Returns:
            One more than the highest position, ``0`` when empty.
        """
        return max((preset.position for preset in self), default=FIRST_POSITION - 1) + 1

    def with_duration(self, duration: Duration, except_id: str = "") -> TimerPreset | None:
        """Find the favorite with a duration.

        Args:
            duration: Duration to look for.
            except_id: Favorite to ignore (the one being edited).

        Returns:
            The favorite, or ``None``.
        """
        return next((preset for preset in self if preset.duration == duration and preset.id != except_id), None)
