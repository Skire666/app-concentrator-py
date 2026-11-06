"""Global hooks for uncaught exceptions: CRITICAL log with traceback, then the error reporter."""

import logging
import sys
import threading
from types import TracebackType

from concentrator.application.ports.error_reporter_port import ErrorReporterPort

_logger = logging.getLogger(__name__)

type _ExcInfo = tuple[type[BaseException], BaseException, TracebackType | None]


class ExceptionHooks:
    """Replaces ``sys.excepthook`` and ``threading.excepthook`` until ``uninstall``.

    One of the two places allowed to catch ``Exception`` (AGENTS.md rule 4, ADR-021).
    """

    def __init__(self, reporter: ErrorReporterPort) -> None:
        """Create uninstalled hooks.

        Args:
            reporter: Shows the error to the user; may be called from any thread.
        """
        self._reporter = reporter
        self._previous_sys_hook = sys.excepthook
        self._previous_thread_hook = threading.excepthook

    def install(self) -> None:
        """Install both hooks, remembering the previous ones."""
        self._previous_sys_hook = sys.excepthook
        self._previous_thread_hook = threading.excepthook
        sys.excepthook = self._on_exception
        threading.excepthook = self._on_thread_exception

    def uninstall(self) -> None:
        """Restore the hooks found by ``install``."""
        sys.excepthook = self._previous_sys_hook
        threading.excepthook = self._previous_thread_hook

    def _on_exception(
        self, exc_type: type[BaseException], exc_value: BaseException, exc_traceback: TracebackType | None
    ) -> None:
        """Handle an exception that reached the main thread's top level (Qt slots included).

        Args:
            exc_type: Exception class.
            exc_value: Exception instance.
            exc_traceback: Traceback.
        """
        if issubclass(exc_type, KeyboardInterrupt):
            self._previous_sys_hook(exc_type, exc_value, exc_traceback)
            return
        _logger.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))
        self._report(exc_value)

    def _on_thread_exception(self, args: threading.ExceptHookArgs) -> None:
        """Handle an exception that ended a thread other than the main one.

        Args:
            args: Exception details provided by ``threading``.
        """
        if args.exc_value is None or issubclass(args.exc_type, SystemExit):
            return
        thread_name = args.thread.name if args.thread is not None else "?"
        exc_info: _ExcInfo = (args.exc_type, args.exc_value, args.exc_traceback)
        _logger.critical("Unhandled exception in thread %s", thread_name, exc_info=exc_info)
        self._report(args.exc_value)

    def _report(self, error: BaseException) -> None:
        """Forward the error to the reporter without letting a reporter failure escape the hook.

        Args:
            error: The exception, already logged.
        """
        try:
            self._reporter.report(error)
        except Exception:  # AGENTS.md rule 4: global exception hooks are one of the two allowed places.
            _logger.exception("The error reporter failed")
