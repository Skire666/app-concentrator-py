import pytest

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.presentation.storage.shutdown_presenter import ShutdownPresenter
from tests.fakes.storage_stack import DATA_PATH, StorageStack
from tests.fakes.user_data_factory import SAVED_AT, make_user_data

REPLACE_FAILED = ValidationResult.failure(ErrorCodeEnum.STORAGE_REPLACE_FAILED)
CHANGED = ValidationResult.failure(ErrorCodeEnum.STORAGE_FILE_CHANGED_EXTERNALLY)


class Setup:
    def __init__(self) -> None:
        self.stack = StorageStack()
        self.presenter = ShutdownPresenter(self.stack.coordinator, self.stack.translator)
        self.presenter.attach(self.stack.dialogs)
        self.stack.session.reset(make_user_data())
        self.stack.coordinator.attach(DATA_PATH, SAVED_AT)

    def changed(self) -> None:
        self.stack.session.change()

    def still_saving(self) -> bool:
        self.stack.session.change()
        self.stack.scheduler.advance(500)
        return bool(self.stack.file.pending)


@pytest.fixture
def setup() -> Setup:
    return Setup()


def test_nothing_pending_closes_without_writing(setup: Setup) -> None:
    assert setup.presenter.can_close()
    assert setup.stack.file.blocking == []
    assert not setup.still_saving()


def test_pending_changes_are_flushed_then_the_window_closes(setup: Setup) -> None:
    setup.changed()

    assert setup.presenter.can_close()
    assert len(setup.stack.file.blocking) == 1
    assert setup.stack.dialogs.calls == []


def test_failure_then_quit_without_saving(setup: Setup) -> None:
    setup.changed()
    setup.stack.file.blocking_validation = REPLACE_FAILED
    setup.stack.dialogs.confirm_answer = True

    assert setup.presenter.can_close()

    title, message, accept, reject = setup.stack.dialogs.texts("confirm")[0]
    assert title == "en:shutdown.failed.title"
    assert message == "en:shutdown.failed.message(reason=en:error.storage_replace_failed)"
    assert (accept, reject) == ("en:dialog.button.quit_without_saving", "en:dialog.button.retry")
    assert not setup.still_saving()


def test_failure_then_retry_keeps_the_window_open_and_saving_goes_on(setup: Setup) -> None:
    setup.changed()
    setup.stack.file.blocking_validation = REPLACE_FAILED
    setup.stack.dialogs.confirm_answer = False

    assert not setup.presenter.can_close()
    setup.stack.scheduler.advance(10_000)
    assert len(setup.stack.file.pending) == 1


def test_external_change_keep_version_overwrites_then_closes(setup: Setup) -> None:
    setup.changed()
    setup.stack.file.blocking_validations = [CHANGED, ValidationResult.success()]
    setup.stack.dialogs.confirm_answers = [False]

    assert setup.presenter.can_close()

    title, message, accept, reject = setup.stack.dialogs.texts("confirm")[0]
    assert (title, message) == ("en:external_change.title", "en:shutdown.changed.message")
    assert (accept, reject) == ("en:dialog.button.quit_without_saving", "en:dialog.button.keep_version")
    assert [overwrite for _revision, overwrite in setup.stack.file.blocking] == [False, True]


def test_external_change_quit_without_saving_leaves_the_file(setup: Setup) -> None:
    setup.changed()
    setup.stack.file.blocking_validation = CHANGED
    setup.stack.dialogs.confirm_answers = [True]

    assert setup.presenter.can_close()
    assert len(setup.stack.file.blocking) == 1
    assert not setup.still_saving()


def test_external_change_overwrite_failure_falls_back_to_retry_question(setup: Setup) -> None:
    setup.changed()
    setup.stack.file.blocking_validations = [CHANGED, REPLACE_FAILED]
    setup.stack.dialogs.confirm_answers = [False, False]

    assert not setup.presenter.can_close()
    assert setup.stack.dialogs.texts("confirm")[1][0] == "en:shutdown.failed.title"


def test_flush_without_dialog_saves_and_stops(setup: Setup) -> None:
    setup.changed()

    setup.presenter.flush_without_dialog()

    assert len(setup.stack.file.blocking) == 1
    assert setup.stack.dialogs.calls == []
    assert not setup.still_saving()


def test_flush_without_dialog_logs_a_failure(setup: Setup, caplog: pytest.LogCaptureFixture) -> None:
    setup.changed()
    setup.stack.file.blocking_validation = REPLACE_FAILED

    setup.presenter.flush_without_dialog()

    assert "not saved at shutdown" in caplog.text
    assert setup.stack.dialogs.calls == []


def test_session_end_flush_saves_and_keeps_saving_if_the_session_end_is_cancelled(setup: Setup) -> None:
    setup.changed()

    setup.presenter.flush_on_session_end()

    assert len(setup.stack.file.blocking) == 1
    assert setup.stack.dialogs.calls == []
    assert setup.still_saving()


def test_session_end_flush_logs_a_failure(setup: Setup, caplog: pytest.LogCaptureFixture) -> None:
    setup.changed()
    setup.stack.file.blocking_validation = REPLACE_FAILED

    setup.presenter.flush_on_session_end()

    assert "not saved at the end of the Windows session" in caplog.text
    assert setup.stack.dialogs.calls == []


def test_a_question_without_attached_dialogs_is_a_wiring_error() -> None:
    stack = StorageStack()
    presenter = ShutdownPresenter(stack.coordinator, stack.translator)
    stack.session.reset(make_user_data())
    stack.coordinator.attach(DATA_PATH, SAVED_AT)
    stack.session.change()
    stack.file.blocking_validations.append(REPLACE_FAILED)

    with pytest.raises(RuntimeError, match="attach"):
        presenter.can_close()
