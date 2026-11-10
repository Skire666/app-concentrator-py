"""Write use cases of the hourly chime."""

import logging

from concentrator.application.common.event_bus import EventBus
from concentrator.application.ports.clock_port import ClockPort
from concentrator.application.ports.hourly_chime_reader_port import HourlyChimeReaderPort
from concentrator.application.ports.hourly_chime_writer_port import HourlyChimeWriterPort
from concentrator.application.timer.timer_events import HourlyChimeChangedEvent
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.timer.chime_settings import ChimeSettings
from concentrator.domain.timer.hourly_chime import HourlyChime
from concentrator.domain.timer.hourly_chime_rules import HourlyChimeRules

_logger = logging.getLogger(__name__)


class ChimeCommands:
    """Switch the chime on or off ("Chime every hour") and store its settings (chime dialog)."""

    def __init__(
        self, reader: HourlyChimeReaderPort, writer: HourlyChimeWriterPort, clock: ClockPort, event_bus: EventBus
    ) -> None:
        """Create the use cases.

        Args:
            reader: Chime reader.
            writer: Chime writer.
            clock: Change instants.
            event_bus: Receives ``HourlyChimeChangedEvent``.
        """
        self._reader = reader
        self._writer = writer
        self._clock = clock
        self._event_bus = event_bus

    def set_enabled(self, enabled: bool) -> ValidationResult:
        """Switch the chime on or off.

        Args:
            enabled: New switch.

        Returns:
            Success (also when nothing changed), or the read or write failure.
        """
        current = self._reader.read()
        if current.data is None:
            return current.validation
        if current.data.enabled == enabled:
            return ValidationResult.success()
        _logger.info("Hourly chime %s", "enabled" if enabled else "disabled")
        return self._store(current.data.with_enabled(enabled, self._clock.now_utc()))

    def update_settings(self, settings: ChimeSettings) -> ValidationResult:
        """Store new sound, volume and hours.

        Args:
            settings: Edited values.

        Returns:
            Success (also when nothing changed), or the rule or write failure.
        """
        current = self._reader.read()
        if current.data is None:
            return current.validation
        if current.data.settings == settings:
            return ValidationResult.success()
        validation = HourlyChimeRules.validate_settings(settings)
        if validation.is_failure:
            return validation
        _logger.info("Hourly chime settings stored")
        return self._store(current.data.with_settings(settings, self._clock.now_utc()))

    def save(self, *, enabled: bool, settings: ChimeSettings) -> ValidationResult:
        """Store the switch and the settings together (settings page): one write at most.

        Args:
            enabled: New switch.
            settings: Edited values.

        Returns:
            Success (also when nothing changed, then nothing is written), or the rule or write failure.
        """
        current = self._reader.read()
        if current.data is None:
            return current.validation
        if current.data.enabled == enabled and current.data.settings == settings:
            return ValidationResult.success()
        validation = HourlyChimeRules.validate_settings(settings)
        if validation.is_failure:
            return validation
        now = self._clock.now_utc()
        _logger.info("Hourly chime stored from the settings page (%s)", "enabled" if enabled else "disabled")
        return self._store(current.data.with_enabled(enabled, now).with_settings(settings, now))

    def _store(self, chime: HourlyChime) -> ValidationResult:
        """Write the chime and publish the change.

        Args:
            chime: Changed chime.

        Returns:
            The writer result.
        """
        written = self._writer.update(chime)
        if written.data is not None:
            self._event_bus.publish(HourlyChimeChangedEvent(chime=written.data))
        return written.validation
