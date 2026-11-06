import logging
import sys
import threading
from collections.abc import Iterator
from types import TracebackType
from typing import override

import pytest

from concentrator.application.ports.error_reporter_port import ErrorReporterPort
from concentrator.infrastructure.logging.exception_hooks import ExceptionHooks
from tests.fakes.recording_error_reporter import RecordingErrorReporter

HOOKS_LOGGER = "concentrator.infrastructure.logging.exception_hooks"


class _BrokenReporter(ErrorReporterPort):
    @override
    def report(self, error: BaseException) -> None:
        raise RuntimeError


def _raise_in_thread() -> None:
    raise ValueError


@pytest.fixture
def reporter() -> RecordingErrorReporter:
    return RecordingErrorReporter()


@pytest.fixture
def hooks(reporter: RecordingErrorReporter) -> Iterator[ExceptionHooks]:
    installed = ExceptionHooks(reporter)
    installed.install()
    yield installed
    installed.uninstall()


def test_install_replaces_and_uninstall_restores_both_hooks(reporter: RecordingErrorReporter) -> None:
    previous_sys, previous_thread = sys.excepthook, threading.excepthook
    hooks = ExceptionHooks(reporter)

    hooks.install()
    assert sys.excepthook is not previous_sys
    assert threading.excepthook is not previous_thread

    hooks.uninstall()
    assert sys.excepthook is previous_sys
    assert threading.excepthook is previous_thread


@pytest.mark.usefixtures("hooks")
def test_main_thread_exception_is_logged_critical_and_reported(
    reporter: RecordingErrorReporter, caplog: pytest.LogCaptureFixture
) -> None:
    error = KeyError("missing")

    with caplog.at_level(logging.CRITICAL, logger=HOOKS_LOGGER):
        sys.excepthook(KeyError, error, None)

    assert reporter.errors == [error]
    assert caplog.records[0].levelno == logging.CRITICAL
    assert caplog.records[0].exc_info is not None


@pytest.mark.usefixtures("hooks")
def test_thread_exception_is_logged_critical_and_reported(
    reporter: RecordingErrorReporter, caplog: pytest.LogCaptureFixture
) -> None:
    worker = threading.Thread(target=_raise_in_thread, name="worker-1")

    with caplog.at_level(logging.CRITICAL, logger=HOOKS_LOGGER):
        worker.start()
        worker.join()

    assert [type(error) for error in reporter.errors] == [ValueError]
    assert "worker-1" in caplog.records[0].getMessage()


@pytest.mark.usefixtures("hooks")
def test_thread_system_exit_is_ignored(reporter: RecordingErrorReporter) -> None:
    worker = threading.Thread(target=sys.exit)

    worker.start()
    worker.join()

    assert reporter.errors == []


def test_keyboard_interrupt_goes_to_the_previous_hook(
    reporter: RecordingErrorReporter, monkeypatch: pytest.MonkeyPatch
) -> None:
    received: list[type[BaseException]] = []

    def previous(kind: type[BaseException], _value: BaseException, _traceback: TracebackType | None) -> None:
        received.append(kind)

    monkeypatch.setattr(sys, "excepthook", previous)
    hooks = ExceptionHooks(reporter)
    hooks.install()
    try:
        sys.excepthook(KeyboardInterrupt, KeyboardInterrupt(), None)
    finally:
        hooks.uninstall()

    assert received == [KeyboardInterrupt]
    assert reporter.errors == []


def test_failing_reporter_is_logged_and_contained(caplog: pytest.LogCaptureFixture) -> None:
    hooks = ExceptionHooks(_BrokenReporter())
    hooks.install()
    try:
        with caplog.at_level(logging.ERROR, logger=HOOKS_LOGGER):
            sys.excepthook(ValueError, ValueError("x"), None)
    finally:
        hooks.uninstall()

    assert [record.getMessage() for record in caplog.records] == ["Unhandled exception", "The error reporter failed"]
