"""Personal settings stored in the user data file (singleton aggregate)."""

from dataclasses import dataclass, replace
from datetime import datetime
from typing import NewType, Self

from concentrator.domain.settings.language_enum import LanguageEnum

UserSettingsId = NewType("UserSettingsId", str)


@dataclass(frozen=True, slots=True, kw_only=True)
class UserSettings:
    """The user's personal settings.

    Attributes:
        id: UUIDv7 identifying the settings.
        created_at: Creation instant, timezone-aware UTC.
        updated_at: Last change instant, timezone-aware UTC.
        language: UI language.
    """

    id: UserSettingsId
    created_at: datetime
    updated_at: datetime
    language: LanguageEnum

    @classmethod
    def create(cls, new_id: UserSettingsId, now: datetime, language: LanguageEnum) -> Self:
        """Create the settings of a new data file.

        Args:
            new_id: Id from ``IdGeneratorPort``.
            now: Creation instant (timezone-aware UTC).
            language: Initial UI language.

        Returns:
            The settings; validate them with ``UserSettingsRules``.
        """
        return cls(id=new_id, created_at=now, updated_at=now, language=language)

    def with_language(self, language: LanguageEnum, now: datetime) -> Self:
        """Return a copy with another UI language.

        Args:
            language: New language.
            now: Change instant (timezone-aware UTC).

        Returns:
            The changed settings.
        """
        return replace(self, language=language, updated_at=now)
