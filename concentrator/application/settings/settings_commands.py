"""Write use cases of the user settings."""

import logging

from concentrator.application.common.event_bus import EventBus
from concentrator.application.ports.clock_port import ClockPort
from concentrator.application.ports.user_settings_reader_port import UserSettingsReaderPort
from concentrator.application.ports.user_settings_writer_port import UserSettingsWriterPort
from concentrator.application.settings.settings_events import UserSettingsChangedEvent
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.settings.user_settings_rules import UserSettingsRules

_logger = logging.getLogger(__name__)


class SettingsCommands:
    """Changes the user settings: read, change with ``now``, validate, write, publish."""

    def __init__(
        self, reader: UserSettingsReaderPort, writer: UserSettingsWriterPort, clock: ClockPort, event_bus: EventBus
    ) -> None:
        """Create the use cases.

        Args:
            reader: Settings reader.
            writer: Settings writer.
            clock: Change instants.
            event_bus: Receives ``UserSettingsChangedEvent``.
        """
        self._reader = reader
        self._writer = writer
        self._clock = clock
        self._event_bus = event_bus

    def change_language(self, language: LanguageEnum) -> ValidationResult:
        """Store a new UI language.

        Args:
            language: Chosen language.

        Returns:
            Success (also when the language is already the current one), or the rule or write failure.
        """
        current = self._reader.read()
        if current.data is None:
            return current.validation
        if current.data.language is language:
            return ValidationResult.success()
        changed = current.data.with_language(language, self._clock.now_utc())
        validation = UserSettingsRules.validate(changed)
        if validation.is_failure:
            return validation
        written = self._writer.update(changed)
        if written.data is None:
            return written.validation
        _logger.info("UI language stored: %s", language.iso_code)
        self._event_bus.publish(UserSettingsChangedEvent(settings=written.data))
        return written.validation
