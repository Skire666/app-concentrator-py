import pytest

from concentrator.application.common.event_bus import EventBus
from concentrator.application.settings.settings_commands import SettingsCommands
from concentrator.application.settings.settings_events import UserSettingsChangedEvent
from concentrator.application.settings.settings_queries import SettingsQueries
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.settings.general_settings import GeneralSettings
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.settings.log_level_enum import LogLevelEnum
from tests.fakes.fake_clock import FakeClock
from tests.fakes.in_memory_user_settings import InMemoryUserSettings
from tests.fakes.recording_error_reporter import RecordingErrorReporter
from tests.fakes.user_data_factory import make_settings


class Setup:
    def __init__(self) -> None:
        self.clock = FakeClock()
        self.settings = InMemoryUserSettings(make_settings(LanguageEnum.ENGLISH))
        self.bus = EventBus(RecordingErrorReporter())
        self.events: list[UserSettingsChangedEvent] = []
        self.bus.subscribe(UserSettingsChangedEvent, self.events.append)
        self.commands = SettingsCommands(self.settings, self.settings, self.clock, self.bus)


@pytest.fixture
def setup() -> Setup:
    return Setup()


def test_change_language_stores_it_with_the_change_time_and_publishes(setup: Setup) -> None:
    result = setup.commands.change_language(LanguageEnum.FRENCH)

    assert result.is_success
    assert setup.settings.settings.language is LanguageEnum.FRENCH
    assert setup.settings.settings.updated_at == setup.clock.now_utc()
    assert [event.settings.language for event in setup.events] == [LanguageEnum.FRENCH]


def test_same_language_changes_nothing(setup: Setup) -> None:
    assert setup.commands.change_language(LanguageEnum.ENGLISH).is_success
    assert setup.settings.updates == 0
    assert setup.events == []


@pytest.mark.parametrize(
    ("language", "code"),
    [(LanguageEnum.UNKNOWN, ErrorCodeEnum.ENUM_VALUE_UNKNOWN), (LanguageEnum.UNSET, ErrorCodeEnum.ENUM_VALUE_UNSET)],
)
def test_invalid_language_is_refused_and_nothing_is_written(
    setup: Setup, language: LanguageEnum, code: ErrorCodeEnum
) -> None:
    result = setup.commands.change_language(language)

    assert result.error_codes == (code,)
    assert setup.settings.updates == 0
    assert setup.events == []


def test_read_failure_is_returned(setup: Setup) -> None:
    setup.settings.read_failure = ValidationResult.failure(ErrorCodeEnum.ENTITY_NOT_FOUND)

    assert setup.commands.change_language(LanguageEnum.FRENCH).error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)


def test_write_failure_is_returned_without_event(setup: Setup) -> None:
    setup.settings.write_failure = ValidationResult.failure(ErrorCodeEnum.ENTITY_NOT_FOUND)

    result = setup.commands.change_language(LanguageEnum.FRENCH)

    assert result.error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)
    assert setup.events == []


def test_queries_return_the_current_settings(setup: Setup) -> None:
    assert SettingsQueries(setup.settings).current_settings().data == make_settings(LanguageEnum.ENGLISH)


def _general(log_level: LogLevelEnum = LogLevelEnum.DEBUG, *, notify: bool = False) -> GeneralSettings:
    return GeneralSettings(language=LanguageEnum.FRENCH, log_level=log_level, notify_when_inactive=notify)


def test_save_general_stores_the_three_values_once_and_publishes(setup: Setup) -> None:
    result = setup.commands.save_general(_general())

    assert result.is_success
    assert setup.settings.settings.general == _general()
    assert setup.settings.settings.updated_at == setup.clock.now_utc()
    assert setup.settings.updates == 1
    assert [event.settings.log_level for event in setup.events] == [LogLevelEnum.DEBUG]


def test_save_general_without_change_writes_nothing(setup: Setup) -> None:
    assert setup.commands.save_general(make_settings(LanguageEnum.ENGLISH).general).is_success
    assert setup.settings.updates == 0
    assert setup.events == []


def test_save_general_refuses_an_unset_level(setup: Setup) -> None:
    result = setup.commands.save_general(_general(LogLevelEnum.UNSET))

    assert result.error_codes == (ErrorCodeEnum.ENUM_VALUE_UNSET,)
    assert setup.settings.updates == 0


def test_save_general_returns_the_read_failure(setup: Setup) -> None:
    setup.settings.read_failure = ValidationResult.failure(ErrorCodeEnum.ENTITY_NOT_FOUND)

    assert setup.commands.save_general(_general()).error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)


def test_notify_when_inactive_follows_the_stored_switch(setup: Setup) -> None:
    queries = SettingsQueries(setup.settings)
    assert queries.notify_when_inactive() is True

    setup.commands.save_general(_general(notify=False))
    assert queries.notify_when_inactive() is False

    setup.settings.read_failure = ValidationResult.failure(ErrorCodeEnum.ENTITY_NOT_FOUND)
    assert queries.notify_when_inactive() is True
