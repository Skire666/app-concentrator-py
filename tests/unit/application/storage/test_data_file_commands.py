from pathlib import Path

import pytest

from concentrator.application.common.event_bus import EventBus
from concentrator.application.storage.data_file_commands import DataFileCommands, MovedDataFile
from concentrator.application.storage.save_coordinator import SaveCoordinator
from concentrator.application.storage.save_state_enum import SaveStateEnum
from concentrator.application.storage.startup_commands import DATA_FILE_PATH_KEY, StartupCommands
from concentrator.application.storage.startup_reason_enum import StartupReasonEnum
from concentrator.application.storage.startup_step_enum import StartupStepEnum
from concentrator.application.storage.storage_events import UserDataReplacedEvent
from concentrator.application.storage.user_data import StoredUserData
from concentrator.application.storage.user_data_defaults import UserDataDefaults
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.settings.language_enum import LanguageEnum
from tests.fakes.app_config_factory import make_storage_section
from tests.fakes.fake_clock import FakeClock
from tests.fakes.fake_id_generator import FakeIdGenerator
from tests.fakes.fake_translator import FakeTranslator
from tests.fakes.fake_user_data_file import FakeUserDataFile, invalid, report, valid
from tests.fakes.in_memory_session import InMemorySession
from tests.fakes.in_memory_view_preferences import InMemoryViewPreferences
from tests.fakes.manual_scheduler import ManualScheduler
from tests.fakes.recording_error_reporter import RecordingErrorReporter
from tests.fakes.timer_extras_factory import DEFAULT_SECTIONS
from tests.fakes.user_data_factory import SAVED_AT, make_stored, make_user_data

CURRENT = Path("C:/Users/me/concentrator.toml")
OTHER = Path("D:/sync/other.toml")
TARGET = Path("D:/Concentrator/concentrator.toml")
WRITE_FAILED = ValidationResult.failure(ErrorCodeEnum.STORAGE_WRITE_FAILED)


class Setup:
    def __init__(self, *, attached: bool = True) -> None:
        self.bus = EventBus(RecordingErrorReporter())
        self.replaced: list[UserDataReplacedEvent] = []
        self.bus.subscribe(UserDataReplacedEvent, self.replaced.append)
        self.session = InMemorySession(self.bus, make_user_data(LanguageEnum.ENGLISH))
        self.file = FakeUserDataFile()
        self.preferences = InMemoryViewPreferences({DATA_FILE_PATH_KEY: CURRENT.as_posix()})
        self.coordinator = SaveCoordinator(
            session=self.session,
            file=self.file,
            scheduler=ManualScheduler(),
            event_bus=self.bus,
            storage=make_storage_section(),
        )
        startup = StartupCommands(
            file=self.file,
            session=self.session,
            coordinator=self.coordinator,
            preferences=self.preferences,
            defaults=UserDataDefaults(FakeIdGenerator(), FakeClock(), DEFAULT_SECTIONS, FakeTranslator()),
            default_path=CURRENT,
            event_bus=self.bus,
        )
        self.commands = DataFileCommands(
            file=self.file,
            session=self.session,
            coordinator=self.coordinator,
            startup=startup,
            preferences=self.preferences,
        )
        if attached:
            self.coordinator.attach(CURRENT, SAVED_AT)

    @property
    def remembered(self) -> str | None:
        return self.preferences.get_text(DATA_FILE_PATH_KEY)

    def touched(self) -> list[Path]:
        return [path for _name, path in self.file.calls]


@pytest.fixture
def setup() -> Setup:
    return Setup()


def test_switch_to_a_valid_file_opens_it_and_remembers_it(setup: Setup) -> None:
    setup.file.reports[OTHER] = report(OTHER, valid(make_stored(LanguageEnum.FRENCH)))

    result = setup.commands.switch_to(OTHER)

    assert result.data is not None
    assert result.data.step is StartupStepEnum.READY
    assert setup.session.data == make_user_data(LanguageEnum.FRENCH)
    assert setup.commands.current_path == OTHER
    assert setup.remembered == OTHER.as_posix()
    assert setup.replaced == [UserDataReplacedEvent(path=OTHER)]


def test_switch_to_a_damaged_file_returns_the_recovery_plan_and_keeps_the_current_file(setup: Setup) -> None:
    setup.file.reports[OTHER] = report(OTHER, invalid())

    result = setup.commands.switch_to(OTHER)

    assert result.data is not None
    assert (result.data.step, result.data.reason) == (StartupStepEnum.NEEDS_RECOVERY, StartupReasonEnum.FILE_DAMAGED)
    assert setup.session.resets == 0
    assert setup.commands.current_path == CURRENT
    assert setup.remembered == CURRENT.as_posix()
    assert setup.replaced == []


def test_switch_to_the_current_file_is_refused_before_anything_is_done(setup: Setup) -> None:
    setup.session.change()

    result = setup.commands.switch_to(Path("c:/users/ME/Concentrator.TOML"))

    assert result.validation.error_codes == (ErrorCodeEnum.STORAGE_TARGET_IS_CURRENT_FILE,)
    assert setup.file.calls == []
    assert setup.file.blocking == []


def test_switch_saves_the_pending_changes_first(setup: Setup) -> None:
    setup.session.change()
    revision = setup.session.revision()
    setup.file.reports[OTHER] = report(OTHER, valid(make_stored()))

    setup.commands.switch_to(OTHER)

    assert setup.file.blocking == [(revision, False)]
    assert setup.touched()[0] == CURRENT


def test_switch_stops_when_the_pending_changes_cannot_be_saved(setup: Setup) -> None:
    setup.session.change()
    setup.file.blocking_validation = WRITE_FAILED

    result = setup.commands.switch_to(OTHER)

    assert result.validation.error_codes == (ErrorCodeEnum.STORAGE_WRITE_FAILED,)
    assert OTHER not in setup.touched()
    assert setup.commands.current_path == CURRENT


def test_create_new_creates_and_opens_a_default_file(setup: Setup) -> None:
    result = setup.commands.create_new(OTHER, LanguageEnum.FRENCH)

    assert result.data is not None
    assert result.data.step is StartupStepEnum.READY
    assert setup.session.data.settings.language is LanguageEnum.FRENCH
    assert setup.commands.current_path == OTHER
    assert setup.remembered == OTHER.as_posix()


def test_create_new_refuses_the_current_file(setup: Setup) -> None:
    result = setup.commands.create_new(CURRENT, LanguageEnum.FRENCH)

    assert result.validation.error_codes == (ErrorCodeEnum.STORAGE_TARGET_IS_CURRENT_FILE,)
    assert setup.file.calls == []


def test_move_writes_the_current_data_and_switches_without_touching_the_old_file(setup: Setup) -> None:
    setup.session.change()

    result = setup.commands.move_to(TARGET)

    assert result.data == MovedDataFile(previous=CURRENT, current=TARGET)
    assert setup.file.calls == [("create", TARGET), ("load", TARGET)]
    assert setup.file.blocking == []
    assert setup.commands.current_path == TARGET
    assert setup.remembered == TARGET.as_posix()
    assert setup.coordinator.status.state is SaveStateEnum.SAVED
    assert not setup.coordinator.has_unsaved_changes
    assert setup.session.resets == 0
    assert setup.replaced == []


def test_move_to_the_current_file_is_refused(setup: Setup) -> None:
    result = setup.commands.move_to(CURRENT)

    assert result.validation.error_codes == (ErrorCodeEnum.STORAGE_TARGET_IS_CURRENT_FILE,)
    assert setup.file.calls == []


def test_move_write_failure_keeps_the_current_file(setup: Setup) -> None:
    setup.file.create_failure = ValidationResult.failure(ErrorCodeEnum.STORAGE_FILE_ALREADY_EXISTS)

    result = setup.commands.move_to(TARGET)

    assert result.validation.error_codes == (ErrorCodeEnum.STORAGE_FILE_ALREADY_EXISTS,)
    assert setup.commands.current_path == CURRENT
    assert setup.remembered == CURRENT.as_posix()


@pytest.mark.parametrize("loaded_back", ["other data", "unreadable"])
def test_move_that_does_not_load_back_the_same_data_fails(setup: Setup, loaded_back: str) -> None:
    other = StoredUserData(data=make_user_data(LanguageEnum.FRENCH), saved_at=SAVED_AT)
    setup.file.loads[TARGET] = DataResult.ok(other) if loaded_back == "other data" else DataResult.fail(WRITE_FAILED)

    result = setup.commands.move_to(TARGET)

    assert result.validation.error_codes == (ErrorCodeEnum.STORAGE_MOVE_FAILED,)
    assert setup.commands.current_path == CURRENT
    assert setup.remembered == CURRENT.as_posix()


def test_move_without_open_file_fails() -> None:
    setup = Setup(attached=False)

    assert setup.commands.move_to(TARGET).validation.error_codes == (ErrorCodeEnum.STORAGE_FILE_NOT_FOUND,)
