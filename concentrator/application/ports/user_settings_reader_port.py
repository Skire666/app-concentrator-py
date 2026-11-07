"""Reads the ``UserSettings`` singleton."""

from typing import Protocol

from concentrator.domain.common.data_result import DataResult
from concentrator.domain.settings.user_settings import UserSettings


class UserSettingsReaderPort(Protocol):
    """Read side of the user settings."""

    def read(self) -> DataResult[UserSettings]:
        """Return the settings of the open data file.

        Returns:
            The settings.
        """
        ...
