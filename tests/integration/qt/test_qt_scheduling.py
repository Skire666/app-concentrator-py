import threading

import pytest
from PySide6.QtCore import QObject
from pytestqt.qtbot import QtBot

from concentrator.infrastructure.qt.qt_main_thread_dispatcher import QtMainThreadDispatcher
from concentrator.infrastructure.qt.qt_scheduler import QtScheduler

pytestmark = pytest.mark.ui


@pytest.fixture
def owner(qtbot: QtBot) -> QObject:
    del qtbot  # ensures the QApplication exists
    return QObject()


def test_call_soon_runs_on_a_later_event_loop_turn(qtbot: QtBot, owner: QObject) -> None:
    scheduler = QtScheduler(owner)
    calls: list[str] = []

    scheduler.call_soon(lambda: calls.append("soon"))
    assert calls == []

    qtbot.waitUntil(lambda: calls == ["soon"], timeout=1000)
    assert scheduler.pending_count == 0


def test_call_later_respects_delays(qtbot: QtBot, owner: QObject) -> None:
    scheduler = QtScheduler(owner)
    calls: list[str] = []

    scheduler.call_later(60, lambda: calls.append("late"))
    scheduler.call_later(0, lambda: calls.append("early"))

    qtbot.waitUntil(lambda: len(calls) == 2, timeout=2000)
    assert calls == ["early", "late"]


def test_cancel_prevents_the_call_and_is_idempotent(qtbot: QtBot, owner: QObject) -> None:
    scheduler = QtScheduler(owner)
    calls: list[str] = []
    handle = scheduler.call_later(10, lambda: calls.append("cancelled"))
    scheduler.call_later(30, lambda: calls.append("kept"))

    handle.cancel()
    handle.cancel()

    qtbot.waitUntil(lambda: calls == ["kept"], timeout=2000)
    assert scheduler.pending_count == 0


def test_cancel_after_the_call_ran_does_nothing(qtbot: QtBot, owner: QObject) -> None:
    scheduler = QtScheduler(owner)
    calls: list[str] = []
    handle = scheduler.call_soon(lambda: calls.append("ran"))
    qtbot.waitUntil(lambda: calls == ["ran"], timeout=1000)

    handle.cancel()

    assert calls == ["ran"]


def test_dispatch_from_a_worker_thread_runs_on_the_main_thread(qtbot: QtBot, owner: QObject) -> None:
    dispatcher = QtMainThreadDispatcher(owner)
    threads: list[threading.Thread] = []

    worker = threading.Thread(target=lambda: dispatcher.dispatch(lambda: threads.append(threading.current_thread())))
    worker.start()
    worker.join()

    qtbot.waitUntil(lambda: len(threads) == 1, timeout=1000)
    assert threads == [threading.main_thread()]
