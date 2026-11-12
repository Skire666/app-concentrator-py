"""An exception raised in a Qt slot is logged CRITICAL and shown in the error dialog (phase 8)."""

from collections.abc import Iterator

import pytest
from PySide6.QtWidgets import QPushButton
from pytestqt.qtbot import QtBot

from concentrator.infrastructure.logging.exception_hooks import ExceptionHooks
from concentrator.presentation.shell.unexpected_error_presenter import UnexpectedErrorPresenter
from tests.fakes.fake_dialogs import FakeDialogs
from tests.fakes.fake_translator import FakeTranslator
from tests.fakes.immediate_dispatcher import ImmediateDispatcher

pytestmark = pytest.mark.ui


class SlotFailureError(RuntimeError):
    """Raised on purpose by the slot under test."""


@pytest.fixture
def dialogs() -> Iterator[FakeDialogs]:
    shown = FakeDialogs()
    presenter = UnexpectedErrorPresenter(ImmediateDispatcher(), FakeTranslator())
    presenter.attach(shown)
    hooks = ExceptionHooks(presenter)
    hooks.install()
    yield shown
    hooks.uninstall()


def _fail() -> None:
    raise SlotFailureError


@pytest.mark.qt_no_exception_capture
def test_exception_in_a_slot_is_logged_and_shown(
    qtbot: QtBot, dialogs: FakeDialogs, caplog: pytest.LogCaptureFixture
) -> None:
    button = QPushButton()
    qtbot.addWidget(button)
    button.clicked.connect(_fail)

    button.click()

    critical = [record for record in caplog.records if record.levelname == "CRITICAL"]
    assert [record.getMessage() for record in critical] == ["Unhandled exception"]
    assert critical[0].exc_info is not None
    assert critical[0].exc_info[0] is SlotFailureError
    assert [name for name, _arguments in dialogs.calls] == ["error"]
