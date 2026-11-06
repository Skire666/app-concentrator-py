from concentrator.presentation.shell.unexpected_error_presenter import UnexpectedErrorPresenter
from tests.fakes.fake_dialogs import FakeDialogs
from tests.fakes.fake_translator import FakeTranslator
from tests.fakes.immediate_dispatcher import ImmediateDispatcher


def _presenter() -> tuple[UnexpectedErrorPresenter, ImmediateDispatcher]:
    dispatcher = ImmediateDispatcher()
    return UnexpectedErrorPresenter(dispatcher, FakeTranslator()), dispatcher


def test_report_before_attach_shows_nothing() -> None:
    presenter, dispatcher = _presenter()

    presenter.report(ValueError())

    assert dispatcher.dispatched == 1


def test_report_shows_a_translated_error_dialog_on_the_main_thread() -> None:
    presenter, dispatcher = _presenter()
    dialogs = FakeDialogs()
    presenter.attach(dialogs)

    presenter.report(ValueError())

    assert dispatcher.dispatched == 1
    assert dialogs.calls == [("error", ("en:dialog.error.title", "en:error.unknown", "en:dialog.button.ok"))]


def test_error_reported_while_a_dialog_is_open_is_not_stacked() -> None:
    presenter, _ = _presenter()
    dialogs = FakeDialogs()
    dialogs.on_error = lambda: presenter.report(RuntimeError())
    presenter.attach(dialogs)

    presenter.report(ValueError())
    presenter.report(KeyError())

    assert [name for name, _texts in dialogs.calls] == ["error", "error"]
