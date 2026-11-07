import ctypes
from collections.abc import Callable
from ctypes import wintypes
from pathlib import Path
from typing import override

import pytest
from PySide6.QtCore import QByteArray, QTimer
from PySide6.QtGui import QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QWidget
from pytestqt.qtbot import QtBot

from concentrator.ui.support.dialog_geometry import Box
from concentrator.ui.support.dimming_overlay import DimmingOverlay
from concentrator.ui.support.modal_host import ModalHost, ScreenDialogRunner
from concentrator.ui.support.position_clamp_filter import (
    NOT_HANDLED,
    SWP_NOMOVE,
    WINDOWS_MESSAGE,
    WM_WINDOWPOSCHANGING,
    PositionClampFilter,
    WindowPos,
)
from concentrator.ui.support.qt_dialog_service import QtDialogService
from concentrator.ui.support.window_rects import SWP_NOSIZE, QtWindowRects, WindowRects

pytestmark = pytest.mark.ui

WAIT_MS = 2000


def _shown_window(qtbot: QtBot) -> QWidget:
    window = QWidget()
    qtbot.addWidget(window)
    window.setGeometry(100, 100, 800, 600)
    window.show()
    qtbot.waitExposed(window)
    return window


def _overlay(window: QWidget) -> DimmingOverlay:
    overlay = window.findChild(DimmingOverlay)
    assert overlay is not None
    return overlay


def _inside(dialog: QWidget, window: QWidget) -> bool:
    return window.frameGeometry().contains(dialog.frameGeometry())


def _while_open(dialog: QDialog, step: Callable[[], None]) -> None:
    def run_then_close() -> None:
        try:
            step()
        finally:
            dialog.accept()

    QTimer.singleShot(0, run_then_close)


def test_run_dims_the_window_while_the_dialog_is_open(qtbot: QtBot) -> None:
    window = _shown_window(qtbot)
    host = ModalHost.create(window, 10)
    dialog = QDialog(window)
    seen: list[object] = []

    def check() -> None:
        overlay = _overlay(window)
        seen.extend([overlay.isVisible(), overlay.geometry() == window.rect()])
        window.resize(900, 700)
        qtbot.waitUntil(lambda: overlay.geometry() == window.rect(), timeout=WAIT_MS)
        seen.append(overlay.size().width())

    _while_open(dialog, check)
    host.run(dialog)

    assert seen == [True, True, 900]
    assert not _overlay(window).isVisible()
    assert host.parent is window


def test_dialog_opens_centered_and_is_kept_inside_the_window(qtbot: QtBot) -> None:
    window = _shown_window(qtbot)
    host = ModalHost.create(window, 10)
    dialog = QDialog(window)
    dialog.resize(200, 100)
    seen: list[bool] = []

    def check() -> None:
        centre = dialog.frameGeometry().center() - window.frameGeometry().center()
        seen.append(abs(centre.x()) <= 1 and abs(centre.y()) <= 1)
        dialog.move(-3000, 5000)
        qtbot.waitUntil(lambda: _inside(dialog, window), timeout=WAIT_MS)
        window.move(1500, 900)
        qtbot.waitUntil(lambda: _inside(dialog, window), timeout=WAIT_MS)
        seen.append(dialog.frameGeometry().topLeft() == window.frameGeometry().topLeft())

    _while_open(dialog, check)
    host.run(dialog)

    assert seen == [True, True]


def test_hidden_window_runs_the_dialog_without_dimming(qtbot: QtBot) -> None:
    window = QWidget()
    qtbot.addWidget(window)
    host = ModalHost.create(window, 10)
    dialog = QDialog(window)
    seen: list[bool] = []
    _while_open(dialog, lambda: seen.append(_overlay(window).isVisible()))

    host.run(dialog)

    assert seen == [False]
    assert host.dimmed(lambda: _overlay(window).isVisible()) is False


def test_minimized_window_is_restored_before_the_dialog(qtbot: QtBot) -> None:
    window = _shown_window(qtbot)
    window.showMinimized()
    host = ModalHost.create(window, 10)
    dialog = QDialog(window)
    seen: list[bool] = []
    _while_open(dialog, lambda: seen.append(window.isMinimized()))

    host.run(dialog)

    assert seen == [False]


def test_dimmed_runs_the_operation_over_the_dimmed_window(qtbot: QtBot) -> None:
    window = _shown_window(qtbot)
    host = ModalHost.create(window, 10)

    assert host.dimmed(lambda: _overlay(window).isVisible()) is True
    assert not _overlay(window).isVisible()


def test_overlay_stays_until_the_last_dialog_closes_and_darkens_the_window(qtbot: QtBot) -> None:
    window = _shown_window(qtbot)
    overlay = DimmingOverlay(window, 10)

    overlay.acquire()
    overlay.acquire()
    overlay.release()
    still_shown = overlay.isVisible()
    pixel = overlay.grab().toImage().pixelColor(5, 5)
    overlay.release()
    overlay.release()

    assert still_shown
    assert not overlay.isVisible()
    assert overlay.alpha == 26
    assert pixel.lightness() < window.palette().color(QPalette.ColorRole.Window).lightness()


@pytest.mark.parametrize(("percent", "alpha"), [(0, 0), (10, 26), (50, 128)])
def test_overlay_alpha_follows_the_configured_percent(qtbot: QtBot, percent: int, alpha: int) -> None:
    window = QWidget()
    qtbot.addWidget(window)

    assert DimmingOverlay(window, percent).alpha == alpha


def test_screen_runner_shows_parentless_dialogs(qtbot: QtBot) -> None:
    runner = ScreenDialogRunner()
    dialog = QDialog()
    qtbot.addWidget(dialog)
    seen: list[bool] = []
    _while_open(dialog, lambda: seen.append(dialog.isVisible()))

    runner.run(dialog)

    assert runner.parent is None
    assert seen == [True]
    assert runner.dimmed(lambda: 7) == 7


def test_create_installs_the_native_filter_on_the_windows_platform(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = _shown_window(qtbot)
    monkeypatch.setattr(QGuiApplication, "platformName", staticmethod(lambda: "windows"))
    host = ModalHost.create(window, 10)
    dialog = QDialog(window)
    _while_open(dialog, lambda: None)

    host.run(dialog)

    assert host.parent is window


def _accept_next_file_dialog(path: Path | None) -> None:
    def answer() -> None:
        dialog = QApplication.activeModalWidget()
        assert isinstance(dialog, QFileDialog)
        if path is None:
            dialog.reject()
            return
        dialog.selectFile(str(path))
        dialog.accept()

    QTimer.singleShot(0, answer)


def test_file_pickers_return_slash_paths_or_none(qtbot: QtBot, tmp_path: Path) -> None:
    window = _shown_window(qtbot)
    service = QtDialogService(ModalHost.create(window, 10))
    existing = tmp_path / "data.toml"
    existing.write_text("", encoding="utf-8")

    _accept_next_file_dialog(existing)
    opened = service.choose_open_file("Open", str(tmp_path), "*.toml")
    _accept_next_file_dialog(tmp_path / "new.toml")
    saved = service.choose_save_file("Save", str(tmp_path), "*.toml")
    _accept_next_file_dialog(tmp_path)
    folder = service.choose_folder("Folder", str(tmp_path))
    _accept_next_file_dialog(None)
    cancelled = service.choose_open_file("Open", str(tmp_path), "*.toml")

    assert opened == existing.as_posix()
    assert saved == (tmp_path / "new.toml").as_posix()
    assert folder == tmp_path.as_posix()
    assert cancelled is None
    assert not _overlay(window).isVisible()


class _FixedRects(WindowRects):
    def __init__(self, boxes: dict[int, Box]) -> None:
        self.boxes = boxes
        self.qt = QtWindowRects()

    @override
    def frame(self, window: QWidget) -> Box:
        return self.boxes[int(window.winId())]

    @override
    def move_frame(self, window: QWidget, x: int, y: int) -> None:
        self.qt.move_frame(window, x, y)


class _Native:
    def __init__(self, qtbot: QtBot) -> None:
        self.host = QWidget()
        self.dialog = QDialog()
        qtbot.addWidget(self.host)
        qtbot.addWidget(self.dialog)
        boxes = {
            int(self.host.winId()): Box(x=100, y=50, width=800, height=600),
            int(self.dialog.winId()): Box(x=0, y=0, width=300, height=200),
        }
        self.filter = PositionClampFilter(_FixedRects(boxes), self.host)
        self.filter.track(self.dialog)

    def send(
        self, position: WindowPos, *, message: int = WM_WINDOWPOSCHANGING, kind: bytes = WINDOWS_MESSAGE
    ) -> object:
        native = wintypes.MSG(hWnd=int(self.dialog.winId()), message=message, lParam=ctypes.addressof(position))
        return self.filter.nativeEventFilter(QByteArray(kind), ctypes.addressof(native))


def test_native_filter_clamps_the_proposed_position_in_place(qtbot: QtBot) -> None:
    native = _Native(qtbot)
    position = WindowPos(x=-500, y=2000, cx=200, cy=100, flags=0)

    assert native.send(position) == NOT_HANDLED
    assert (position.x, position.y) == (100, 550)


def test_native_filter_uses_the_current_size_when_only_moving(qtbot: QtBot) -> None:
    native = _Native(qtbot)
    position = WindowPos(x=2000, y=2000, cx=0, cy=0, flags=SWP_NOSIZE)

    native.send(position)

    assert (position.x, position.y) == (600, 450)


@pytest.mark.parametrize(
    ("flags", "message", "kind"),
    [
        (SWP_NOMOVE, WM_WINDOWPOSCHANGING, WINDOWS_MESSAGE),
        (0, WM_WINDOWPOSCHANGING + 1, WINDOWS_MESSAGE),
        (0, WM_WINDOWPOSCHANGING, b"xcb_generic_event_t"),
    ],
)
def test_native_filter_ignores_other_messages(qtbot: QtBot, flags: int, message: int, kind: bytes) -> None:
    native = _Native(qtbot)
    position = WindowPos(x=-500, y=-500, cx=200, cy=100, flags=flags)

    native.send(position, message=message, kind=kind)

    assert (position.x, position.y) == (-500, -500)


def test_native_filter_forgets_an_untracked_dialog(qtbot: QtBot) -> None:
    native = _Native(qtbot)
    native.filter.untrack(native.dialog)
    position = WindowPos(x=-500, y=-500, cx=200, cy=100, flags=0)

    native.send(position)

    assert (position.x, position.y) == (-500, -500)
