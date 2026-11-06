"""Error dialog for unexpected errors (global hooks and ``EventBus`` dispatch)."""

import logging
from typing import override

from concentrator.application.ports.error_reporter_port import ErrorReporterPort
from concentrator.application.ports.main_thread_dispatcher_port import MainThreadDispatcherPort
from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.presentation.common.ui_texts import error_message_key
from concentrator.presentation.ports.dialog_port import DialogPort

_logger = logging.getLogger(__name__)


class UnexpectedErrorPresenter(ErrorReporterPort):
    """Shows one translated error dialog at a time, on the main thread.

    Errors reported before the window exists, or while a dialog is already open, are only logged (the
    caller has already logged the traceback).
    """

    def __init__(self, dispatcher: MainThreadDispatcherPort, translator: TranslatorPort) -> None:
        """Create the presenter.

        Args:
            dispatcher: Moves the dialog to the main thread.
            translator: Current-language translator.
        """
        self._dispatcher = dispatcher
        self._translator = translator
        self._dialogs: DialogPort | None = None
        self._showing = False

    def attach(self, dialogs: DialogPort) -> None:
        """Start showing dialogs (once the main window exists).

        Args:
            dialogs: Dialog service parented to the main window.
        """
        self._dialogs = dialogs

    @override
    def report(self, error: BaseException) -> None:
        self._dispatcher.dispatch(lambda: self._show(type(error).__name__))

    def _show(self, error_name: str) -> None:
        """Show the dialog unless one is already open.

        Args:
            error_name: Exception class name, for the log.
        """
        if self._dialogs is None or self._showing:
            _logger.info("Error dialog skipped for %s (no window or a dialog is open)", error_name)
            return
        self._showing = True
        try:
            tr = self._translator.tr
            message = tr(error_message_key(ErrorCodeEnum.UNKNOWN))
            self._dialogs.error(tr("dialog.error.title"), message, tr("dialog.button.ok"))
        finally:
            self._showing = False
