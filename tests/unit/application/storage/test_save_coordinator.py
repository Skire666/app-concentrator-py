from datetime import timedelta
from pathlib import Path

import pytest

from concentrator.application.common.event_bus import EventBus
from concentrator.application.storage.save_coordinator import SaveCoordinator
from concentrator.application.storage.save_state_enum import SaveStateEnum
from concentrator.application.storage.storage_events import SaveStatusChangedEvent
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.settings.language_enum import LanguageEnum
from tests.fakes.app_config_factory import make_storage_section
from tests.fakes.fake_user_data_file import FakeUserDataFile
from tests.fakes.in_memory_session import InMemorySession
from tests.fakes.manual_scheduler import ManualScheduler
from tests.fakes.recording_error_reporter import RecordingErrorReporter
from tests.fakes.user_data_factory import SAVED_AT, make_user_data

PATH = Path("C:/data/concentrator.toml")
LATER = SAVED_AT + timedelta(minutes=5)
REPLACE_FAILED = ValidationResult.failure(ErrorCodeEnum.STORAGE_REPLACE_FAILED)
CHANGED = ValidationResult.failure(ErrorCodeEnum.STORAGE_FILE_CHANGED_EXTERNALLY)


class Setup:
    def __init__(self) -> None:
        self.bus = EventBus(RecordingErrorReporter())
        self.statuses: list[SaveStatusChangedEvent] = []
        self.bus.subscribe(SaveStatusChangedEvent, self.statuses.append)
        self.session = InMemorySession(self.bus)
        self.file = FakeUserDataFile(saved_at=LATER)
        self.scheduler = ManualScheduler()
        self.coordinator = SaveCoordinator(
            session=self.session,
            file=self.file,
            scheduler=self.scheduler,
            event_bus=self.bus,
            storage=make_storage_section(),
        )

    def attach(self) -> None:
        self.session.reset(make_user_data())
        self.coordinator.attach(PATH, SAVED_AT)

    @property
    def state(self) -> SaveStateEnum:
        return self.coordinator.status.state

    @property
    def states(self) -> list[SaveStateEnum]:
        return [status.state for status in self.statuses]


@pytest.fixture
def setup() -> Setup:
    return Setup()


def test_without_file_changes_are_not_saved(setup: Setup) -> None:
    setup.session.change()
    setup.scheduler.advance(5000)

    assert setup.state is SaveStateEnum.NO_FILE
    assert setup.file.pending == []
    assert not setup.coordinator.has_unsaved_changes
    assert setup.coordinator.flush_for_shutdown().is_success


def test_attach_reports_the_file_saved_at(setup: Setup) -> None:
    setup.attach()

    assert setup.coordinator.status == SaveStatusChangedEvent(state=SaveStateEnum.SAVED, path=PATH, saved_at=SAVED_AT)
    assert setup.statuses == [setup.coordinator.status]


def test_debounce_coalesces_ten_changes_into_one_save(setup: Setup) -> None:
    setup.attach()

    for _ in range(10):
        setup.session.change()
        setup.scheduler.advance(100)

    assert setup.state is SaveStateEnum.PENDING
    assert setup.file.pending == []
    setup.scheduler.advance(400)
    assert len(setup.file.pending) == 1
    assert setup.file.pending[0].revision == setup.session.revision()
    assert setup.state is SaveStateEnum.SAVING

    setup.file.complete()

    assert setup.coordinator.status == SaveStatusChangedEvent(state=SaveStateEnum.SAVED, path=PATH, saved_at=LATER)
    assert not setup.coordinator.has_unsaved_changes
    assert setup.states == [SaveStateEnum.SAVED, SaveStateEnum.PENDING, SaveStateEnum.SAVING, SaveStateEnum.SAVED]


def test_continuous_changes_still_save_after_the_maximum_delay(setup: Setup) -> None:
    setup.attach()

    for _ in range(5):
        setup.session.change()
        setup.scheduler.advance(300)

    assert len(setup.file.pending) == 1
    assert setup.scheduler.now_ms == 1500


def test_twenty_fast_toggles_give_at_most_three_writes(setup: Setup) -> None:
    setup.attach()

    for _ in range(20):
        setup.session.change()
        setup.scheduler.advance(150)
        while setup.file.pending:
            setup.file.complete()
    setup.scheduler.advance(2000)
    while setup.file.pending:
        setup.file.complete()

    assert 1 <= sum(1 for call in setup.file.calls if call[0] == "save_async") <= 3
    assert setup.state is SaveStateEnum.SAVED


def test_change_during_a_save_triggers_a_second_save(setup: Setup) -> None:
    setup.attach()
    setup.session.change(make_user_data(LanguageEnum.ENGLISH))
    setup.scheduler.advance(500)
    first = setup.file.pending[0]

    setup.session.change(make_user_data(LanguageEnum.FRENCH))
    setup.scheduler.advance(500)
    assert len(setup.file.pending) == 1
    setup.file.complete()

    assert len(setup.file.pending) == 1
    second = setup.file.pending[0]
    assert second.revision > first.revision
    assert second.data == make_user_data(LanguageEnum.FRENCH)
    assert setup.state is SaveStateEnum.SAVING
    setup.file.complete()
    assert setup.state is SaveStateEnum.SAVED


def test_save_completed_while_changes_wait_reports_pending(setup: Setup) -> None:
    setup.attach()
    setup.session.change()
    setup.scheduler.advance(500)
    setup.session.change()

    setup.file.complete()

    assert setup.state is SaveStateEnum.PENDING
    setup.scheduler.advance(500)
    setup.file.complete()
    assert setup.state is SaveStateEnum.SAVED


def test_failure_keeps_data_and_retries_automatically(setup: Setup) -> None:
    setup.attach()
    setup.session.change()
    setup.scheduler.advance(500)

    setup.file.complete(REPLACE_FAILED)

    assert setup.state is SaveStateEnum.FAILED
    assert setup.coordinator.status.validation == REPLACE_FAILED
    assert setup.coordinator.status.saved_at == SAVED_AT
    assert setup.coordinator.has_unsaved_changes
    setup.scheduler.advance(9_999)
    assert setup.file.pending == []
    setup.scheduler.advance(1)
    assert len(setup.file.pending) == 1
    setup.file.complete()
    assert setup.state is SaveStateEnum.SAVED


def test_change_after_a_failure_keeps_showing_the_failure_until_the_next_save(setup: Setup) -> None:
    setup.attach()
    setup.session.change()
    setup.scheduler.advance(500)
    setup.file.complete(REPLACE_FAILED)

    setup.session.change()

    assert setup.state is SaveStateEnum.FAILED
    setup.scheduler.advance(500)
    assert setup.state is SaveStateEnum.SAVING


def test_warnings_are_kept_with_the_saved_state(setup: Setup) -> None:
    setup.attach()
    setup.session.change()
    setup.scheduler.advance(500)
    warning = ValidationResult.warning(ErrorCodeEnum.STORAGE_BACKUP_FAILED)

    setup.file.complete(warning)

    assert setup.state is SaveStateEnum.SAVED
    assert setup.coordinator.status.validation == warning


def test_external_change_fails_without_retry_until_the_user_decides(setup: Setup) -> None:
    setup.attach()
    setup.session.change()
    setup.scheduler.advance(500)

    setup.file.complete(CHANGED)
    setup.session.change()
    setup.scheduler.advance(60_000)

    assert setup.state is SaveStateEnum.FAILED
    assert setup.coordinator.status.validation == CHANGED
    assert setup.file.pending == []


def test_keep_local_version_overwrites_once(setup: Setup) -> None:
    setup.attach()
    setup.session.change()
    setup.scheduler.advance(500)
    setup.file.complete(CHANGED)

    setup.coordinator.keep_local_version()

    assert [save.overwrite_external for save in setup.file.pending] == [True]
    setup.file.complete()
    assert setup.state is SaveStateEnum.SAVED
    setup.session.change()
    setup.scheduler.advance(500)
    assert [save.overwrite_external for save in setup.file.pending] == [False]


def test_keep_local_version_without_conflict_does_nothing(setup: Setup) -> None:
    setup.attach()

    setup.coordinator.keep_local_version()

    assert setup.file.pending == []


def test_attach_after_a_reload_clears_the_conflict(setup: Setup) -> None:
    setup.attach()
    setup.session.change()
    setup.scheduler.advance(500)
    setup.file.complete(CHANGED)

    setup.session.reset(make_user_data(LanguageEnum.ENGLISH))
    setup.coordinator.attach(PATH, LATER)
    setup.session.change()
    setup.scheduler.advance(500)

    assert len(setup.file.pending) == 1
    assert not setup.file.pending[0].overwrite_external


def test_retry_timer_with_nothing_left_to_save_reports_saved(setup: Setup) -> None:
    setup.attach()
    setup.session.change()
    setup.scheduler.advance(500)
    setup.file.complete(REPLACE_FAILED)
    assert setup.coordinator.flush_for_shutdown().is_success
    assert setup.state is SaveStateEnum.SAVED

    setup.scheduler.advance(20_000)

    assert setup.file.pending == []
    assert setup.state is SaveStateEnum.SAVED


def test_flush_for_shutdown_saves_pending_changes_synchronously(setup: Setup) -> None:
    setup.attach()
    setup.session.change()

    result = setup.coordinator.flush_for_shutdown()

    assert result.is_success
    assert setup.file.blocking == [(setup.session.revision(), False)]
    assert setup.state is SaveStateEnum.SAVED
    assert setup.file.pending == []
    setup.scheduler.advance(5000)
    assert setup.file.pending == []


def test_flush_for_shutdown_with_nothing_pending_does_not_write(setup: Setup) -> None:
    setup.attach()

    assert setup.coordinator.flush_for_shutdown().is_success
    assert setup.file.blocking == []


def test_flush_for_shutdown_waits_behind_a_save_in_flight(setup: Setup) -> None:
    setup.attach()
    setup.session.change()
    setup.scheduler.advance(500)

    assert setup.coordinator.flush_for_shutdown().is_success

    assert setup.file.blocking == [(setup.session.revision(), False)]
    setup.file.complete()
    assert setup.state is SaveStateEnum.SAVED


def test_flush_for_shutdown_failure_is_returned_and_retried(setup: Setup) -> None:
    setup.attach()
    setup.session.change()
    setup.file.blocking_validation = REPLACE_FAILED

    result = setup.coordinator.flush_for_shutdown()

    assert result.error_codes == (ErrorCodeEnum.STORAGE_REPLACE_FAILED,)
    assert setup.state is SaveStateEnum.FAILED
    setup.scheduler.advance(10_000)
    assert len(setup.file.pending) == 1


def test_flush_for_shutdown_can_overwrite_an_external_change(setup: Setup) -> None:
    setup.attach()
    setup.session.change()

    setup.coordinator.flush_for_shutdown(overwrite_external=True)

    assert setup.file.blocking == [(setup.session.revision(), True)]


def test_close_ignores_late_results_and_stops_saving(setup: Setup) -> None:
    setup.attach()
    setup.session.change()
    setup.scheduler.advance(500)

    setup.coordinator.close()
    setup.file.complete(REPLACE_FAILED)
    setup.session.change()
    setup.scheduler.advance(20_000)

    assert setup.state is SaveStateEnum.SAVING
    assert setup.file.pending == []
    assert setup.coordinator.flush_for_shutdown().is_success
    assert setup.file.blocking == []


def test_stale_result_after_a_newer_save_is_ignored(setup: Setup) -> None:
    setup.attach()
    setup.session.change()
    setup.scheduler.advance(500)
    setup.session.change()
    setup.coordinator.flush_for_shutdown()

    setup.file.complete(REPLACE_FAILED)

    assert setup.state is SaveStateEnum.SAVED
