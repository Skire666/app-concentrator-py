"""Everything stored in the user data file, as one immutable snapshot."""

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Final, Self

from concentrator.domain.settings.user_settings import UserSettings
from concentrator.domain.timer.timer_config import TimerConfig
from concentrator.domain.timer.timer_limits import TimerLimits

CURRENT_SCHEMA_VERSION: Final = 1


@dataclass(frozen=True, slots=True, kw_only=True)
class UserData:
    """The whole content of the user data file. Later phases add sections with defaults.

    A section missing from a file read from disk is ``None`` until ``UserDataDefaults`` fills it
    in with the ``concentrator.ini`` defaults, right after the file is opened.

    Attributes:
        schema_version: Version of the file layout (``CURRENT_SCHEMA_VERSION`` for new files).
        settings: Personal settings.
        timer: Timer configuration (``[timer]``, phase 2).
    """

    schema_version: int
    settings: UserSettings
    timer: TimerConfig | None = None

    @classmethod
    def initial(cls, settings: UserSettings, timer: TimerConfig) -> Self:
        """Content of a new data file.

        Args:
            settings: Settings of the new file.
            timer: Timer configuration of the new file.

        Returns:
            The data, at the current schema version.
        """
        return cls(schema_version=CURRENT_SCHEMA_VERSION, settings=settings, timer=timer)

    def with_settings(self, settings: UserSettings) -> Self:
        """Return a copy with other settings.

        Args:
            settings: New settings.

        Returns:
            The changed data.
        """
        return replace(self, settings=settings)

    def with_timer(self, timer: TimerConfig) -> Self:
        """Return a copy with another timer configuration.

        Args:
            timer: New configuration.

        Returns:
            The changed data.
        """
        return replace(self, timer=timer)


@dataclass(frozen=True, slots=True, kw_only=True)
class UserDataLimits:
    """Limits from ``concentrator.ini`` that the domain rules apply when a file is read.

    Attributes:
        timer: Bounds of the timer configuration.
    """

    timer: TimerLimits


@dataclass(frozen=True, slots=True, kw_only=True)
class StoredUserData:
    """User data together with the instant it was saved (``saved_at`` of the file).

    Attributes:
        data: The content.
        saved_at: When the file was written, timezone-aware UTC.
    """

    data: UserData
    saved_at: datetime
