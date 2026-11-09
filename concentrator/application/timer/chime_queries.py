"""Read use cases of the hourly chime."""

import logging

from concentrator.application.ports.hourly_chime_reader_port import HourlyChimeReaderPort
from concentrator.application.timer.chime_defaults import ChimeDefaults
from concentrator.domain.timer.chime_settings import ChimeSettings
from concentrator.domain.timer.hourly_chime import HourlyChime

_logger = logging.getLogger(__name__)


class ChimeQueries:
    """Whether the chime is on, and its settings."""

    def __init__(self, reader: HourlyChimeReaderPort, defaults: ChimeDefaults) -> None:
        """Create the queries.

        Args:
            reader: Chime reader.
            defaults: ``[chime]`` values, used if the chime cannot be read (never after startup).
        """
        self._reader = reader
        self._defaults = defaults

    @property
    def defaults(self) -> ChimeDefaults:
        """``[chime]`` values of ``concentrator.ini``."""
        return self._defaults

    def enabled(self) -> bool:
        """Tell whether the chime is switched on.

        Returns:
            The stored switch (``chime.default_enabled`` if it cannot be read).
        """
        chime = self._chime()
        return self._defaults.enabled if chime is None else chime.enabled

    def settings(self) -> ChimeSettings:
        """Return the sound, volume and hours.

        Returns:
            The stored settings (the ini defaults if they cannot be read).
        """
        chime = self._chime()
        return self._defaults.settings if chime is None else chime.settings

    def _chime(self) -> HourlyChime | None:
        """Read the chime.

        Returns:
            The chime, or ``None`` (logged at WARNING).
        """
        chime = self._reader.read()
        if chime.data is None:
            _logger.warning("Hourly chime unavailable: %s", [code.name for code in chime.validation.error_codes])
        return chime.data
