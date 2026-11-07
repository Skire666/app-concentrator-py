"""Read use cases of the user settings."""

from concentrator.application.ports.user_settings_reader_port import UserSettingsReaderPort
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.settings.user_settings import UserSettings


class SettingsQueries:
    """Reads the user settings."""

    def __init__(self, reader: UserSettingsReaderPort) -> None:
        """Create the queries.

        Args:
            reader: Settings reader.
        """
        self._reader = reader

    def current_settings(self) -> DataResult[UserSettings]:
        """Return the settings of the open data file.

        Returns:
            The settings.
        """
        return self._reader.read()
