from datetime import timedelta

import pytest

from concentrator.application.storage.save_state_enum import SaveStateEnum
from concentrator.application.storage.storage_events import SaveStatusChangedEvent
from concentrator.application.storage.user_data import StoredUserData
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.presentation.storage.external_change_presenter import ExternalChangePresenter
from concentrator.presentation.storage.shutdown_presenter import ShutdownPresenter
from tests.fakes.storage_stack import DATA_PATH, StorageStack
from tests.fakes.user_data_factory import SAVED_AT, make_user_data

CHANGED = ValidationResult.failure(ErrorCodeEnum.STORAGE_FILE_CHANGED_EXTERNALLY)
LATER = SAVED_AT + timedelta(minutes=2)


class Setup:
    def __init__(self) -> None:
        self.stack = StorageStack()
        self.presenter = ExternalChangePresenter(
            self.stack.external, self.stack.dialogs, self.stack.translator, self.stack.scheduler, self.stack.switcher
        )
        self.stack.bus.subscribe(SaveStatusChangedEvent, self.presenter.on_save_status_changed)
        self.stack.session.reset(make_user_data(LanguageEnum.ENGLISH))
        self.stack.coordinator.attach(DATA_PATH, SAVED_AT)

    def conflict(self) -> None:
        self.stack.session.change()
        self.stack.scheduler.advance(500)
        self.stack.file.complete(CHANGED)


@pytest.fixture
def setup() -> Setup:
    return Setup()


def test_question_is_asked_on_the_next_turn_once(setup: Setup) -> None:
    setup.stack.dialogs.confirm_answer = False
    setup.conflict()
    setup.presenter.on_save_status_changed(setup.stack.coordinator.status)

    assert setup.stack.dialogs.calls == []
    setup.stack.scheduler.run_pending()

    assert setup.stack.dialogs.texts("confirm") == [
        (
            "en:external_change.title",
            "en:external_change.message",
            "en:dialog.button.reload_file",
            "en:dialog.button.keep_version",
        )
    ]


def test_other_failures_ask_nothing(setup: Setup) -> None:
    setup.stack.session.change()
    setup.stack.scheduler.advance(500)
    setup.stack.file.complete(ValidationResult.failure(ErrorCodeEnum.STORAGE_REPLACE_FAILED))
    setup.stack.scheduler.run_pending()

    assert setup.stack.dialogs.calls == []


def test_keep_concentrator_version_overwrites(setup: Setup) -> None:
    setup.stack.dialogs.confirm_answer = False
    setup.conflict()

    setup.stack.scheduler.run_pending()

    assert [save.overwrite_external for save in setup.stack.file.pending] == [True]


def test_reload_resets_the_data_and_follows_its_language(setup: Setup) -> None:
    setup.stack.file.loads[DATA_PATH] = DataResult.ok(
        StoredUserData(data=make_user_data(LanguageEnum.FRENCH), saved_at=LATER)
    )
    setup.conflict()

    setup.stack.scheduler.run_pending()

    assert setup.stack.session.data == make_user_data(LanguageEnum.FRENCH)
    assert setup.stack.coordinator.status.state is SaveStateEnum.SAVED
    assert setup.stack.coordinator.status.saved_at == LATER
    assert setup.stack.translator.language is LanguageEnum.FRENCH
    assert setup.stack.hint.read() is LanguageEnum.FRENCH


def test_reload_failure_explains_and_asks_again(setup: Setup) -> None:
    setup.stack.dialogs.confirm_answers = [True, False]
    setup.conflict()

    setup.stack.scheduler.run_pending()

    assert setup.stack.dialogs.kinds() == ["confirm", "error", "confirm"]
    title, message, _button = setup.stack.dialogs.texts("error")[0]
    assert title == "en:external_change.title"
    assert message.splitlines() == ["en:external_change.reload_failed", "en:error.storage_file_not_found"]
    assert [save.overwrite_external for save in setup.stack.file.pending] == [True]


def _shutdown(setup: Setup) -> ShutdownPresenter:
    presenter = ShutdownPresenter(setup.stack.coordinator, setup.stack.translator)
    presenter.attach(setup.stack.dialogs)
    setup.stack.session.change()
    setup.stack.file.blocking_validations.append(CHANGED)
    return presenter


def test_conflict_found_when_closing_is_left_to_the_shutdown_question(setup: Setup) -> None:
    shutdown = _shutdown(setup)
    setup.stack.dialogs.confirm_answer = True  # "Quit without saving"

    assert shutdown.can_close()
    setup.stack.scheduler.run_pending()

    assert [texts[1] for texts in setup.stack.dialogs.texts("confirm")] == ["en:shutdown.changed.message"]


def test_conflict_found_at_session_end_is_asked_if_the_session_goes_on(setup: Setup) -> None:
    shutdown = _shutdown(setup)
    setup.stack.dialogs.confirm_answer = False

    shutdown.flush_on_session_end()
    setup.stack.scheduler.run_pending()

    assert [texts[1] for texts in setup.stack.dialogs.texts("confirm")] == ["en:external_change.message"]


def test_session_end_is_known_after_the_commit_data_flush(setup: Setup) -> None:
    shutdown = _shutdown(setup)
    assert not shutdown.is_session_ending()

    shutdown.flush_on_session_end()

    assert shutdown.is_session_ending()
