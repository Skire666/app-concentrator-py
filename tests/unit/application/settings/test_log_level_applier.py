from pathlib import Path
from typing import override

from concentrator.application.ports.logging_control_port import LoggingControlPort
from concentrator.application.settings.log_level_applier import LogLevelApplier
from concentrator.application.settings.settings_events import UserSettingsChangedEvent
from concentrator.application.settings.settings_queries import SettingsQueries
from concentrator.application.storage.storage_events import UserDataReplacedEvent
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.settings.log_level_enum import LogLevelEnum
from tests.fakes.in_memory_user_settings import InMemoryUserSettings
from tests.fakes.user_data_factory import make_settings

PATH = Path("D:/data/concentrator.toml")


class _Control(LoggingControlPort):
    def __init__(self) -> None:
        self.levels: list[LogLevelEnum] = []

    @override
    def set_level(self, level: LogLevelEnum) -> None:
        self.levels.append(level)


def test_opened_file_applies_its_level() -> None:
    control = _Control()
    settings = InMemoryUserSettings(make_settings(LanguageEnum.ENGLISH, LogLevelEnum.WARNING))

    LogLevelApplier(SettingsQueries(settings), control).on_user_data_replaced(UserDataReplacedEvent(path=PATH))

    assert control.levels == [LogLevelEnum.WARNING]


def test_unreadable_settings_leave_the_level_alone() -> None:
    control = _Control()
    settings = InMemoryUserSettings(make_settings())
    settings.read_failure = ValidationResult.failure(ErrorCodeEnum.ENTITY_NOT_FOUND)

    LogLevelApplier(SettingsQueries(settings), control).on_user_data_replaced(UserDataReplacedEvent(path=PATH))

    assert control.levels == []


def test_changed_settings_apply_their_level() -> None:
    control = _Control()
    applier = LogLevelApplier(SettingsQueries(InMemoryUserSettings(make_settings())), control)

    applier.on_settings_changed(UserSettingsChangedEvent(make_settings(log_level=LogLevelEnum.DEBUG)))

    assert control.levels == [LogLevelEnum.DEBUG]
