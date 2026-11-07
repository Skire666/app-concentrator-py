"""Persisted timer configuration (singleton aggregate)."""

from dataclasses import dataclass, replace
from datetime import datetime
from typing import NewType, Self

from concentrator.domain.timer.timer_settings import TimerSettings

TimerConfigId = NewType("TimerConfigId", str)


@dataclass(frozen=True, slots=True, kw_only=True)
class TimerConfig:
    """The timer configuration stored in the ``[timer]`` section of the user data file.

    Attributes:
        id: UUIDv7 identifying the configuration.
        created_at: Creation instant, timezone-aware UTC.
        updated_at: Last change instant, timezone-aware UTC.
        settings: Duration and alarm.
    """

    id: TimerConfigId
    created_at: datetime
    updated_at: datetime
    settings: TimerSettings

    @classmethod
    def create(cls, new_id: TimerConfigId, now: datetime, settings: TimerSettings) -> Self:
        """Create the configuration of a new data file.

        Args:
            new_id: Id from ``IdGeneratorPort``.
            now: Creation instant (timezone-aware UTC).
            settings: Initial values (the ``concentrator.ini`` defaults).

        Returns:
            The configuration; validate it with ``TimerConfigRules``.
        """
        return cls(id=new_id, created_at=now, updated_at=now, settings=settings)

    def with_settings(self, settings: TimerSettings, now: datetime) -> Self:
        """Return a copy with other settings.

        Args:
            settings: New values.
            now: Change instant (timezone-aware UTC).

        Returns:
            The changed configuration.
        """
        return replace(self, settings=settings, updated_at=now)
