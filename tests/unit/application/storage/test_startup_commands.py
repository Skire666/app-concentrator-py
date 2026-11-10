from datetime import timedelta
from pathlib import Path

import pytest

from concentrator.application.common.event_bus import EventBus
from concentrator.application.storage.external_change_commands import ExternalChangeCommands
from concentrator.application.storage.recovery_source_enum import RecoverySourceEnum
from concentrator.application.storage.save_coordinator import SaveCoordinator
from concentrator.application.storage.save_state_enum import SaveStateEnum
from concentrator.application.storage.startup_commands import DATA_FILE_PATH_KEY, StartupCommands
from concentrator.application.storage.startup_reason_enum import StartupReasonEnum
from concentrator.application.storage.startup_step_enum import StartupStepEnum
from concentrator.application.storage.user_data import StoredUserData
from concentrator.application.storage.user_data_defaults import UserDataDefaults
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.settings.language_enum import LanguageEnum
from tests.fakes.app_config_factory import make_storage_section
from tests.fakes.fake_clock import FakeClock
from tests.fakes.fake_id_generator import FakeIdGenerator
from tests.fakes.fake_user_data_file import FakeUserDataFile, invalid, report, valid
from tests.fakes.in_memory_session import InMemorySession
from tests.fakes.in_memory_view_preferences import InMemoryViewPreferences
from tests.fakes.manual_scheduler import ManualScheduler
from tests.fakes.recording_error_reporter import RecordingErrorReporter
from tests.fakes.timer_extras_factory import DEFAULT_SECTIONS
from tests.fakes.user_data_factory import SAVED_AT, make_stored, make_user_data

PATH = Path("D:/sync/concentrator.toml")
DEFAULT = Path("C:/Users/me/AppData/Roaming/Concentrator/concentrator.toml")
NEWER = SAVED_AT + timedelta(minutes=1)


class Setup:
    def __init__(self) -> None:
        bus = EventBus(RecordingErrorReporter())
        self.session = InMemorySession(bus)
        self.file = FakeUserDataFile(saved_at=NEWER)
        self.preferences = InMemoryViewPreferences()
        self.clock = FakeClock()
        self.coordinator = SaveCoordinator(
            session=self.session,
            file=self.file,
            scheduler=ManualScheduler(),
            event_bus=bus,
            storage=make_storage_section(),
        )
        ids = FakeIdGenerator()
        self.defaults = UserDataDefaults(ids, self.clock, DEFAULT_SECTIONS)
        self.commands = StartupCommands(
            file=self.file,
            session=self.session,
            coordinator=self.coordinator,
            preferences=self.preferences,
            defaults=self.defaults,
            default_path=DEFAULT,
        )

    def external(self) -> ExternalChangeCommands:
        return ExternalChangeCommands(self.file, self.session, self.coordinator, self.defaults)

    def remember(self, path: Path = PATH) -> None:
        self.preferences.values[DATA_FILE_PATH_KEY] = path.as_posix()

    @property
    def remembered(self) -> str | None:
        return self.preferences.get_text(DATA_FILE_PATH_KEY)


@pytest.fixture
def setup() -> Setup:
    return Setup()


@pytest.mark.parametrize("stored_path", [None, "  "])
def test_first_run_without_remembered_path(setup: Setup, stored_path: str | None) -> None:
    if stored_path is not None:
        setup.preferences.values[DATA_FILE_PATH_KEY] = stored_path
    setup.file.existing.add(DEFAULT)

    plan = setup.commands.resolve_startup()

    assert (plan.step, plan.reason, plan.path) == (StartupStepEnum.NEEDS_LOCATION, StartupReasonEnum.FIRST_RUN, None)
    assert plan.default_path == DEFAULT
    assert plan.default_exists
    assert setup.file.calls == []


def test_remembered_valid_file_opens(setup: Setup) -> None:
    setup.remember()
    setup.file.reports[PATH] = report(PATH, valid(make_stored(LanguageEnum.ENGLISH)))

    plan = setup.commands.resolve_startup()

    assert (plan.step, plan.reason, plan.path) == (StartupStepEnum.READY, StartupReasonEnum.OPENED, PATH)
    assert setup.session.data == make_user_data(LanguageEnum.ENGLISH)
    assert setup.coordinator.status.state is SaveStateEnum.SAVED
    assert setup.coordinator.status.saved_at == SAVED_AT
    assert setup.coordinator.status.path == PATH
    assert setup.remembered == PATH.as_posix()


def test_damaged_file_is_neither_opened_nor_remembered(setup: Setup) -> None:
    plan = setup.commands.inspect(PATH)

    assert plan.step is StartupStepEnum.NEEDS_LOCATION
    assert plan.reason is StartupReasonEnum.FILE_NOT_FOUND
    assert setup.session.resets == 0
    assert setup.remembered is None


def test_probe_failure_is_fatal(setup: Setup) -> None:
    setup.file.probe_failure = ValidationResult.failure(ErrorCodeEnum.STORAGE_FILE_UNREADABLE)

    plan = setup.commands.inspect(PATH)

    assert (plan.step, plan.reason) == (StartupStepEnum.FATAL, StartupReasonEnum.FILE_UNREADABLE)
    assert plan.problem.error_codes == (ErrorCodeEnum.STORAGE_FILE_UNREADABLE,)


def test_create_at_writes_new_settings_and_opens(setup: Setup) -> None:
    result = setup.commands.create_at(PATH, LanguageEnum.FRENCH)

    assert result.data is not None
    assert result.data.step is StartupStepEnum.READY
    settings = setup.session.data.settings
    assert settings.id == "id-0001"
    assert settings.language is LanguageEnum.FRENCH
    assert settings.created_at == setup.clock.now_utc()
    assert setup.coordinator.status.saved_at == NEWER
    assert setup.remembered == PATH.as_posix()


def test_create_at_failure_opens_nothing(setup: Setup) -> None:
    setup.file.create_failure = ValidationResult.failure(ErrorCodeEnum.STORAGE_FILE_ALREADY_EXISTS)

    result = setup.commands.create_at(PATH, LanguageEnum.ENGLISH)

    assert result.validation.error_codes == (ErrorCodeEnum.STORAGE_FILE_ALREADY_EXISTS,)
    assert setup.session.resets == 0
    assert setup.remembered is None


def test_create_at_refuses_an_invalid_language(setup: Setup) -> None:
    result = setup.commands.create_at(PATH, LanguageEnum.UNKNOWN)

    assert result.validation.error_codes == (ErrorCodeEnum.ENUM_VALUE_UNKNOWN,)
    assert setup.file.calls == []


def test_restore_opens_the_restored_data(setup: Setup) -> None:
    setup.file.reports[PATH] = report(PATH, invalid(), backup=valid(make_stored(LanguageEnum.ENGLISH)))

    result = setup.commands.restore(PATH, RecoverySourceEnum.BACKUP)

    assert result.data is not None
    assert result.data.step is StartupStepEnum.READY
    assert setup.session.data == make_user_data(LanguageEnum.ENGLISH)
    assert ("restore:BACKUP", PATH) in setup.file.calls


def test_restore_failure_opens_nothing(setup: Setup) -> None:
    setup.file.restore_failure = ValidationResult.failure(ErrorCodeEnum.STORAGE_SYNTAX_INVALID, line=1, column=1)

    assert setup.commands.restore(PATH, RecoverySourceEnum.TEMPORARY).data is None
    assert setup.session.resets == 0


def test_keep_current_discards_the_tmp_then_opens_the_file(setup: Setup) -> None:
    setup.file.reports[PATH] = report(PATH, valid(make_stored()))

    result = setup.commands.keep_current(PATH)

    assert result.data is not None
    assert result.data.step is StartupStepEnum.READY
    assert [name for name, _path in setup.file.calls] == ["discard", "probe"]


def test_keep_current_rename_failure_is_returned(setup: Setup) -> None:
    setup.file.rename_failure = ValidationResult.failure(ErrorCodeEnum.STORAGE_REPLACE_FAILED)

    assert setup.commands.keep_current(PATH).validation.error_codes == (ErrorCodeEnum.STORAGE_REPLACE_FAILED,)
    assert setup.session.resets == 0


def test_start_empty_quarantines_an_existing_file_first(setup: Setup) -> None:
    setup.file.existing.add(PATH)

    result = setup.commands.start_empty(PATH, LanguageEnum.ENGLISH)

    assert result.data is not None
    assert [name for name, _path in setup.file.calls] == ["quarantine", "create"]


def test_start_empty_without_a_file_only_creates(setup: Setup) -> None:
    setup.commands.start_empty(PATH, LanguageEnum.ENGLISH)

    assert [name for name, _path in setup.file.calls] == ["create"]


def test_start_empty_never_creates_when_the_quarantine_fails(setup: Setup) -> None:
    setup.file.existing.add(PATH)
    setup.file.rename_failure = ValidationResult.failure(ErrorCodeEnum.STORAGE_REPLACE_FAILED)

    result = setup.commands.start_empty(PATH, LanguageEnum.ENGLISH)

    assert result.validation.error_codes == (ErrorCodeEnum.STORAGE_REPLACE_FAILED,)
    assert [name for name, _path in setup.file.calls] == ["quarantine"]


def test_reload_after_an_external_change_resets_the_session(setup: Setup) -> None:
    setup.commands.create_at(PATH, LanguageEnum.ENGLISH)
    setup.file.loads[PATH] = DataResult.ok(StoredUserData(data=make_user_data(LanguageEnum.FRENCH), saved_at=NEWER))
    reloaded = setup.external().reload()

    assert reloaded.data is not None
    assert setup.session.data == make_user_data(LanguageEnum.FRENCH)
    assert setup.coordinator.status.state is SaveStateEnum.SAVED
    assert setup.coordinator.status.saved_at == NEWER


def test_reload_failure_leaves_the_session_alone(setup: Setup) -> None:
    setup.commands.create_at(PATH, LanguageEnum.ENGLISH)
    resets = setup.session.resets

    result = setup.external().reload()

    assert result.validation.error_codes == (ErrorCodeEnum.STORAGE_FILE_NOT_FOUND,)
    assert setup.session.resets == resets


def test_reload_without_open_file_fails(setup: Setup) -> None:
    result = setup.external().reload()

    assert result.validation.error_codes == (ErrorCodeEnum.STORAGE_FILE_NOT_FOUND,)


def test_keep_concentrator_version_delegates_to_the_coordinator(setup: Setup) -> None:
    assert setup.external().keep_concentrator_version().is_success
