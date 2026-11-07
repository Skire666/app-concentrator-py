"""Closing the main window asks first (owner decision, 2026-11-07)."""

from concentrator.presentation.storage.shutdown_presenter import ShutdownPresenter
from tests.fakes.storage_stack import DATA_PATH, StorageStack
from tests.fakes.user_data_factory import SAVED_AT, make_user_data


def _presenter(stack: StorageStack, *, countdown: bool = False) -> ShutdownPresenter:
    presenter = ShutdownPresenter(stack.coordinator, stack.translator, lambda: countdown)
    presenter.attach(stack.dialogs)
    stack.session.reset(make_user_data())
    stack.coordinator.attach(DATA_PATH, SAVED_AT)
    return presenter


def test_quit_is_confirmed_then_pending_changes_are_flushed() -> None:
    stack = StorageStack()
    presenter = _presenter(stack)
    stack.session.change()

    assert presenter.may_close()

    assert stack.dialogs.texts("confirm") == [
        ("en:shutdown.confirm.title", "en:shutdown.confirm.message", "en:dialog.button.quit", "en:dialog.button.cancel")
    ]
    assert len(stack.file.blocking) == 1


def test_declining_keeps_the_window_open_and_writes_nothing() -> None:
    stack = StorageStack()
    presenter = _presenter(stack)
    stack.session.change()
    stack.dialogs.confirm_answer = False

    assert not presenter.may_close()

    assert stack.file.blocking == []
    assert stack.coordinator.has_unsaved_changes


def test_a_running_countdown_is_mentioned() -> None:
    stack = StorageStack()

    _presenter(stack, countdown=True).may_close()

    assert stack.dialogs.texts("confirm")[0][1] == "en:shutdown.confirm.message.countdown"


def test_without_a_countdown_source_no_countdown_is_assumed() -> None:
    stack = StorageStack()
    presenter = ShutdownPresenter(stack.coordinator, stack.translator)
    presenter.attach(stack.dialogs)

    assert presenter.may_close()
    assert stack.dialogs.texts("confirm")[0][1] == "en:shutdown.confirm.message"
