"""User settings reader and writer over one in-memory value, with scripted failures."""

from typing import override

from concentrator.application.ports.user_settings_reader_port import UserSettingsReaderPort
from concentrator.application.ports.user_settings_writer_port import UserSettingsWriterPort
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.settings.user_settings import UserSettings


class InMemoryUserSettings(UserSettingsReaderPort, UserSettingsWriterPort):
    """``read_failure`` / ``write_failure`` make the next calls fail."""

    def __init__(self, settings: UserSettings) -> None:
        self.settings = settings
        self.read_failure: ValidationResult | None = None
        self.write_failure: ValidationResult | None = None
        self.updates = 0

    @override
    def read(self) -> DataResult[UserSettings]:
        if self.read_failure is not None:
            return DataResult.fail(self.read_failure)
        return DataResult.ok(self.settings)

    @override
    def update(self, settings: UserSettings) -> DataResult[UserSettings]:
        if self.write_failure is not None:
            return DataResult.fail(self.write_failure)
        self.updates += 1
        self.settings = settings
        return DataResult.ok(settings)
