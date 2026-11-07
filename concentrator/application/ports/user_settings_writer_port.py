"""Writes the ``UserSettings`` singleton."""

from typing import Protocol

from concentrator.domain.common.data_result import DataResult
from concentrator.domain.settings.user_settings import UserSettings


class UserSettingsWriterPort(Protocol):
    """Write side of the user settings."""

    def update(self, settings: UserSettings) -> DataResult[UserSettings]:
        """Replace the settings (in memory; the save follows through the save coordinator).

        Args:
            settings: Validated settings with the id of the current ones.

        Returns:
            The stored settings, or ``ENTITY_NOT_FOUND`` when the id differs.
        """
        ...
