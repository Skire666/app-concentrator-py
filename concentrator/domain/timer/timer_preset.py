"""A saved timer duration: a favorite of zone 2."""

from dataclasses import dataclass, replace
from datetime import datetime
from typing import NewType, Self

from concentrator.domain.timer.duration import Duration

TimerPresetId = NewType("TimerPresetId", str)


def normalize_label(text: str) -> str:
    """Clean a favorite label: no leading or trailing spaces, one space between words, no line break.

    Args:
        text: Label as typed.

    Returns:
        The label to store; ``""`` means the automatic label ("15 min").
    """
    return " ".join(text.split())


@dataclass(frozen=True, slots=True, kw_only=True)
class TimerPreset:
    """One favorite (``[[timer_presets]]``); checked by ``TimerPresetRules``.

    Attributes:
        id: UUIDv7 identifying the favorite.
        created_at: Creation instant, timezone-aware UTC.
        updated_at: Last change instant, timezone-aware UTC.
        label: Text of the button, ``""`` for the automatic label built by the presentation layer.
        duration: Countdown duration started by the favorite.
        position: Sort key of the favorites (lowest first).
    """

    id: TimerPresetId
    created_at: datetime
    updated_at: datetime
    label: str
    duration: Duration
    position: int

    @classmethod
    def create(cls, new_id: TimerPresetId, now: datetime, *, label: str, duration: Duration, position: int) -> Self:
        """Create a favorite.

        Args:
            new_id: Id from ``IdGeneratorPort``.
            now: Creation instant (timezone-aware UTC).
            label: Label as typed (normalized here).
            duration: Countdown duration.
            position: Sort key (``TimerPresetsCollection.next_position()`` for a new last favorite).

        Returns:
            The favorite; validate it with ``TimerPresetRules``.
        """
        return cls(
            id=new_id,
            created_at=now,
            updated_at=now,
            label=normalize_label(label),
            duration=duration,
            position=position,
        )

    def with_values(self, label: str, duration: Duration, now: datetime) -> Self:
        """Return a copy with another label and duration (edit dialog).

        Args:
            label: Label as typed (normalized here).
            duration: New duration.
            now: Change instant (timezone-aware UTC).

        Returns:
            The changed favorite.
        """
        return replace(self, label=normalize_label(label), duration=duration, updated_at=now)

    def with_position(self, position: int, now: datetime) -> Self:
        """Return a copy at another position.

        Args:
            position: New sort key.
            now: Change instant (timezone-aware UTC).

        Returns:
            The moved favorite.
        """
        return replace(self, position=position, updated_at=now)

    def business_copy(self, new_id: str, now: datetime) -> Self:
        """Return a duplicate with a new identity (``BusinessCopyable``).

        Args:
            new_id: Id of the duplicate.
            now: Creation instant of the duplicate.

        Returns:
            The duplicate, same label, duration and position.
        """
        return replace(self, id=TimerPresetId(new_id), created_at=now, updated_at=now)
