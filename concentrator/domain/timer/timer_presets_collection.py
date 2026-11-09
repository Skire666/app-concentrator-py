"""The favorites of the timer, ordered by position."""

from datetime import datetime
from typing import Final, Self

from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.entity_collection import ID_FIELD, EntityCollection
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.timer.duration import Duration
from concentrator.domain.timer.timer_preset import TimerPreset

FIRST_POSITION: Final = 0


class TimerPresetsCollection(EntityCollection[TimerPreset]):
    """Group logic of the favorites: display order, next position, duration lookup, moves.

    The stored order of the items is not the display order: a move changes positions only, so readers
    use ``ordered()``. ``TimerPresetRules.validate_collection`` checks the limit and the unique durations.
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

    def moved(self, preset_id: str, offset: int, now: datetime) -> DataResult[tuple[TimerPreset, ...]]:
        """Move a favorite in the display order and renumber the positions ``0, 1, 2...``.

        Args:
            preset_id: Favorite to move.
            offset: ``-1`` to move it earlier, ``+1`` later.
            now: Change instant of the favorites whose position changes.

        Returns:
            The changed favorites (usually the two that swap places); skipped, without data, when the
            favorite is already at that end; ``ENTITY_NOT_FOUND`` for an unknown id.
        """
        order = list(self.ordered())
        index = next((position for position, preset in enumerate(order) if preset.id == preset_id), None)
        if index is None:
            return DataResult.fail(ValidationResult.failure(ErrorCodeEnum.ENTITY_NOT_FOUND, field=ID_FIELD))
        target = index + offset
        if not FIRST_POSITION <= target < len(order):
            return DataResult.fail(ValidationResult.skipped())
        order.insert(target, order.pop(index))
        changed = tuple(
            preset.with_position(position, now) for position, preset in enumerate(order) if preset.position != position
        )
        return DataResult.ok(changed)
