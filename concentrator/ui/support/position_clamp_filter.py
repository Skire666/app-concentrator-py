"""Keeps the tracked dialogs inside the main window while Windows moves them (ADR-036).

Every move of a window (title bar drag, keyboard, another monitor, ``SetWindowPos``) sends
``WM_WINDOWPOSCHANGING`` before it happens, and Qt hands that message to its native event filters. The
proposed position is clamped in place, so a drag stops at the edges of the main window without
flicker. Qt does not forward ``WM_MOVING`` to the filters.
"""

import ctypes
from ctypes import wintypes
from typing import ClassVar, Final, override

from PySide6.QtCore import QAbstractNativeEventFilter, QByteArray
from PySide6.QtWidgets import QWidget

from concentrator.ui.support.dialog_geometry import Box, clamped
from concentrator.ui.support.window_rects import SWP_NOSIZE, WindowRects

WINDOWS_MESSAGE: Final = b"windows_generic_MSG"
WM_WINDOWPOSCHANGING: Final = 0x0046
SWP_NOMOVE: Final = 0x0002
NOT_HANDLED: Final = (False, 0)


class WindowPos(ctypes.Structure):
    """The Win32 ``WINDOWPOS`` structure pointed to by ``WM_WINDOWPOSCHANGING``."""

    _fields_: ClassVar = [
        ("hwnd", wintypes.HWND),
        ("hwnd_insert_after", wintypes.HWND),
        ("x", ctypes.c_int),
        ("y", ctypes.c_int),
        ("cx", ctypes.c_int),
        ("cy", ctypes.c_int),
        ("flags", wintypes.UINT),
    ]


class PositionClampFilter(QAbstractNativeEventFilter):
    """Native event filter of the application, active for the dialogs it tracks."""

    def __init__(self, rects: WindowRects, host: QWidget) -> None:
        """Create the filter (install it with ``QCoreApplication.installNativeEventFilter``).

        Args:
            rects: Native window rectangles.
            host: Main window the dialogs stay in.
        """
        super().__init__()
        self._rects = rects
        self._host = host
        self._tracked: dict[int, QWidget] = {}

    def track(self, dialog: QWidget) -> None:
        """Start keeping a dialog inside the main window.

        Args:
            dialog: Top-level dialog (its native window is created if needed).
        """
        self._tracked[int(dialog.winId())] = dialog

    def untrack(self, dialog: QWidget) -> None:
        """Stop keeping a dialog inside the main window.

        Args:
            dialog: A tracked dialog.
        """
        self._tracked.pop(int(dialog.winId()), None)

    @override
    def nativeEventFilter(self, event_type: QByteArray | bytes | bytearray | memoryview, message: int) -> object:
        if event_type != WINDOWS_MESSAGE:
            return NOT_HANDLED
        native = wintypes.MSG.from_address(int(message))
        dialog = self._tracked.get(native.hWnd or 0)
        if native.message != WM_WINDOWPOSCHANGING or dialog is None:
            return NOT_HANDLED
        position = WindowPos.from_address(native.lParam)
        if not position.flags & SWP_NOMOVE:
            self._clamp(position, dialog)
        return NOT_HANDLED

    def _clamp(self, position: WindowPos, dialog: QWidget) -> None:
        """Correct a proposed position in place; Qt and Windows then go on with it.

        Args:
            position: The ``WINDOWPOS`` of the message.
            dialog: The dialog being moved.
        """
        if position.flags & SWP_NOSIZE:
            current = self._rects.frame(dialog)
            width, height = current.width, current.height
        else:
            width, height = position.cx, position.cy
        target = clamped(Box(x=position.x, y=position.y, width=width, height=height), self._rects.frame(self._host))
        position.x = target.x
        position.y = target.y
