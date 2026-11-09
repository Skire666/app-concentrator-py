"""Persisted hourly chime (singleton aggregate)."""

from dataclasses import dataclass, replace
from datetime import datetime
from typing import NewType, Self

from concentrator.domain.timer.chime_settings import ChimeSettings

HourlyChimeId = NewType("HourlyChimeId", str)


@dataclass(frozen=True, slots=True, kw_only=True)
class HourlyChime:
    """The chime stored in the ``[hourly_chime]`` section of the user data file.

    Attributes:
        id: UUIDv7 identifying the chime.
        created_at: Creation instant, timezone-aware UTC.
        updated_at: Last change instant, timezone-aware UTC.
        enabled: Whether it chimes ("Chime every hour").
        settings: Sound, volume and active hours.
    """

    id: HourlyChimeId
    created_at: datetime
    updated_at: datetime
    enabled: bool
    settings: ChimeSettings

    @classmethod
    def create(cls, new_id: HourlyChimeId, now: datetime, *, enabled: bool, settings: ChimeSettings) -> Self:
        """Create the chime of a new data file.

        Args:
            new_id: Id from ``IdGeneratorPort``.
            now: Creation instant (timezone-aware UTC).
            enabled: Initial switch (``chime.default_enabled``).
            settings: Initial values (the ``[chime]`` defaults of the ini).

        Returns:
            The chime; validate it with ``HourlyChimeRules``.
        """
        return cls(id=new_id, created_at=now, updated_at=now, enabled=enabled, settings=settings)

    def with_enabled(self, enabled: bool, now: datetime) -> Self:
        """Return a copy switched on or off.

        Args:
            enabled: New switch.
            now: Change instant (timezone-aware UTC).

        Returns:
            The changed chime.
        """
        return replace(self, enabled=enabled, updated_at=now)

    def with_settings(self, settings: ChimeSettings, now: datetime) -> Self:
        """Return a copy with other settings.

        Args:
            settings: New values.
            now: Change instant (timezone-aware UTC).

        Returns:
            The changed chime.
        """
        return replace(self, settings=settings, updated_at=now)
