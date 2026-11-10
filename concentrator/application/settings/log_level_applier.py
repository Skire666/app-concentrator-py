"""Keeps the log level in line with the user settings of the open data file."""

from concentrator.application.ports.logging_control_port import LoggingControlPort
from concentrator.application.settings.settings_events import UserSettingsChangedEvent
from concentrator.application.settings.settings_queries import SettingsQueries
from concentrator.application.storage.storage_events import UserDataReplacedEvent


class LogLevelApplier:
    """Applies ``log_level`` when a data file opens and when the settings change.

    Before a data file is open, ``logging.level`` of ``concentrator.ini`` applies.
    """

    def __init__(self, queries: SettingsQueries, control: LoggingControlPort) -> None:
        """Create the applier; bootstrap subscribes its handlers to the event bus.

        Args:
            queries: Settings of the open data file.
            control: Root logger level.
        """
        self._queries = queries
        self._control = control

    def on_user_data_replaced(self, _event: UserDataReplacedEvent) -> None:
        """Apply the level of the data file just opened or reloaded.

        Args:
            _event: The replacement (the settings are read from the session).
        """
        settings = self._queries.current_settings()
        if settings.data is not None:
            self._control.set_level(settings.data.log_level)

    def on_settings_changed(self, event: UserSettingsChangedEvent) -> None:
        """Apply the level of changed settings.

        Args:
            event: The new settings.
        """
        self._control.set_level(event.settings.log_level)
