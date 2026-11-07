"""Everything stored in the user data file, as one immutable snapshot."""

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Final, Self

from concentrator.domain.settings.user_settings import UserSettings

CURRENT_SCHEMA_VERSION: Final = 1


@dataclass(frozen=True, slots=True, kw_only=True)
class UserData:
    """The whole content of the user data file. Later phases add sections with defaults.

    Attributes:
        schema_version: Version of the file layout (``CURRENT_SCHEMA_VERSION`` for new files).
        settings: Personal settings.
    """

    schema_version: int
    settings: UserSettings

    @classmethod
    def initial(cls, settings: UserSettings) -> Self:
        """Content of a new data file.

        Args:
            settings: Settings of the new file.

        Returns:
            The data, at the current schema version.
        """
        return cls(schema_version=CURRENT_SCHEMA_VERSION, settings=settings)

    def with_settings(self, settings: UserSettings) -> Self:
        """Return a copy with other settings.

        Args:
            settings: New settings.

        Returns:
            The changed data.
        """
        return replace(self, settings=settings)


@dataclass(frozen=True, slots=True, kw_only=True)
class StoredUserData:
    """User data together with the instant it was saved (``saved_at`` of the file).

    Attributes:
        data: The content.
        saved_at: When the file was written, timezone-aware UTC.
    """

    data: UserData
    saved_at: datetime
