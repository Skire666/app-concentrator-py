"""Everything stored in the user data file, as one immutable snapshot."""

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Final, Self

from concentrator.domain.settings.user_settings import UserSettings
from concentrator.domain.timer.hourly_chime import HourlyChime
from concentrator.domain.timer.timer_config import TimerConfig
from concentrator.domain.timer.timer_limits import TimerLimits
from concentrator.domain.timer.timer_presets_collection import TimerPresetsCollection

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
        timer_presets: Favorites (``[[timer_presets]]``, phase 3); ``None`` when the file has no
            ``timer_presets`` key, an empty collection when the user deleted every favorite.
        hourly_chime: Hourly chime (``[hourly_chime]``, phase 3).
    """

    schema_version: int
    settings: UserSettings
    timer: TimerConfig | None = None
    timer_presets: TimerPresetsCollection | None = None
    hourly_chime: HourlyChime | None = None

    @classmethod
    def initial(
        cls,
        settings: UserSettings,
        timer: TimerConfig,
        timer_presets: TimerPresetsCollection,
        hourly_chime: HourlyChime,
    ) -> Self:
        """Content of a new data file.

        Args:
            settings: Settings of the new file.
            timer: Timer configuration of the new file.
            timer_presets: Favorites of the new file.
            hourly_chime: Hourly chime of the new file.

        Returns:
            The data, at the current schema version.
        """
        return cls(
            schema_version=CURRENT_SCHEMA_VERSION,
            settings=settings,
            timer=timer,
            timer_presets=timer_presets,
            hourly_chime=hourly_chime,
        )

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

    def with_timer_presets(self, timer_presets: TimerPresetsCollection) -> Self:
        """Return a copy with other favorites.

        Args:
            timer_presets: New favorites.

        Returns:
            The changed data.
        """
        return replace(self, timer_presets=timer_presets)

    def with_hourly_chime(self, hourly_chime: HourlyChime) -> Self:
        """Return a copy with another hourly chime.

        Args:
            hourly_chime: New chime.

        Returns:
            The changed data.
        """
        return replace(self, hourly_chime=hourly_chime)


@dataclass(frozen=True, slots=True, kw_only=True)
class UserDataLimits:
    """Limits from ``concentrator.ini`` that the domain rules apply when a file is read.

    Attributes:
        timer: Bounds of the timer configuration and of the favorites.
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
