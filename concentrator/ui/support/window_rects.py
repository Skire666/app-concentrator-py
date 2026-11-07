"""Outer rectangles of top-level windows (ADR-036).

On the Windows platform the native rectangles (``GetWindowRect``, physical pixels) are used, because
the position filter works on native messages; elsewhere (tests run ``offscreen``) the Qt frame geometry.
"""

import ctypes
import logging
from ctypes import wintypes
from typing import Final, Protocol, override

from PySide6.QtWidgets import QWidget

from concentrator.ui.support.dialog_geometry import Box

_logger = logging.getLogger(__name__)

SWP_NOSIZE: Final = 0x0001
SWP_NOZORDER: Final = 0x0004
SWP_NOACTIVATE: Final = 0x0010
_MOVE_ONLY: Final = SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE


def _qt_frame(window: QWidget) -> Box:
    """Qt frame geometry of a window.

    Args:
        window: Top-level window.

    Returns:
        Its rectangle, frame included.
    """
    frame = window.frameGeometry()
    return Box(x=frame.x(), y=frame.y(), width=frame.width(), height=frame.height())


class WindowRects(Protocol):
    """Reads and moves the outer rectangle of a top-level window."""

    def frame(self, window: QWidget) -> Box:
        """Outer rectangle of a window.

        Args:
            window: Top-level window.

        Returns:
            Its rectangle in screen coordinates.
        """
        ...

    def move_frame(self, window: QWidget, x: int, y: int) -> None:
        """Move the outer rectangle of a window.

        Args:
            window: Top-level window.
            x: New left edge.
            y: New top edge.
        """
        ...


class QtWindowRects(WindowRects):
    """Qt frame geometry (any platform)."""

    @override
    def frame(self, window: QWidget) -> Box:
        return _qt_frame(window)

    @override
    def move_frame(self, window: QWidget, x: int, y: int) -> None:
        window.move(x, y)


class NativeWindowRects(WindowRects):
    """Win32 window rectangles, in the coordinates of ``WM_WINDOWPOSCHANGING``."""

    def __init__(self) -> None:
        """Bind ``GetWindowRect`` and ``SetWindowPos``."""
        user32 = ctypes.WinDLL("user32")
        self._get_window_rect = user32.GetWindowRect
        self._get_window_rect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        self._get_window_rect.restype = wintypes.BOOL
        self._set_window_pos = user32.SetWindowPos
        self._set_window_pos.argtypes = [
            wintypes.HWND,
            wintypes.HWND,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.UINT,
        ]
        self._set_window_pos.restype = wintypes.BOOL

    @override
    def frame(self, window: QWidget) -> Box:
        rect = wintypes.RECT()
        if not self._get_window_rect(int(window.winId()), ctypes.byref(rect)):
            _logger.warning("GetWindowRect failed; using the Qt frame geometry")
            return _qt_frame(window)
        return Box(x=rect.left, y=rect.top, width=rect.right - rect.left, height=rect.bottom - rect.top)

    @override
    def move_frame(self, window: QWidget, x: int, y: int) -> None:
        if not self._set_window_pos(int(window.winId()), None, x, y, 0, 0, _MOVE_ONLY):
            _logger.warning("SetWindowPos failed; moving with Qt")
            window.move(x, y)
