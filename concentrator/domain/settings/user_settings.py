"""Personal settings stored in the user data file (singleton aggregate)."""

from dataclasses import dataclass, replace
from datetime import datetime
from typing import NewType, Self

from concentrator.domain.settings.general_settings import GeneralSettings
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.settings.log_level_enum import LogLevelEnum

UserSettingsId = NewType("UserSettingsId", str)


@dataclass(frozen=True, slots=True, kw_only=True)
class UserSettings:
    """The user's personal settings.

    Attributes:
        id: UUIDv7 identifying the settings.
        created_at: Creation instant, timezone-aware UTC.
        updated_at: Last change instant, timezone-aware UTC.
        language: UI language.
        log_level: Lowest severity of the records written to the log and shown in the journal.
        notify_when_inactive: Whether a timer that rings unseen makes the taskbar button flash.
    """

    id: UserSettingsId
    created_at: datetime
    updated_at: datetime
    language: LanguageEnum
    log_level: LogLevelEnum
    notify_when_inactive: bool

    @classmethod
    def create(cls, new_id: UserSettingsId, now: datetime, general: GeneralSettings) -> Self:
        """Create the settings of a new data file.

        Args:
            new_id: Id from ``IdGeneratorPort``.
            now: Creation instant (timezone-aware UTC).
            general: Initial values (chosen language, ``[settings]`` defaults of the ini).

        Returns:
            The settings; validate them with ``UserSettingsRules``.
        """
        return cls(
            id=new_id,
            created_at=now,
            updated_at=now,
            language=general.language,
            log_level=general.log_level,
            notify_when_inactive=general.notify_when_inactive,
        )

    @property
    def general(self) -> GeneralSettings:
        """The values edited in the General section of the settings page."""
        return GeneralSettings(
            language=self.language, log_level=self.log_level, notify_when_inactive=self.notify_when_inactive
        )

    def with_language(self, language: LanguageEnum, now: datetime) -> Self:
        """Return a copy with another UI language.

        Args:
            language: New language.
            now: Change instant (timezone-aware UTC).

        Returns:
            The changed settings.
        """
        return replace(self, language=language, updated_at=now)

    def with_general(self, general: GeneralSettings, now: datetime) -> Self:
        """Return a copy with other General values.

        Args:
            general: New values.
            now: Change instant (timezone-aware UTC).

        Returns:
            The changed settings.
        """
        return replace(
            self,
            language=general.language,
            log_level=general.log_level,
            notify_when_inactive=general.notify_when_inactive,
            updated_at=now,
        )
