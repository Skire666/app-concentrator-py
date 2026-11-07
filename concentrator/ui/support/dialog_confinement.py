"""Keeps the open dialogs inside the main window (ADR-036)."""

from typing import override

from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QWidget

from concentrator.ui.support.dialog_geometry import clamped
from concentrator.ui.support.position_clamp_filter import PositionClampFilter
from concentrator.ui.support.window_rects import WindowRects


class DialogConfinement(QObject):
    """Clamps the tracked dialogs when they move and when the main window moves or is resized.

    On Windows the native ``PositionClampFilter`` clamps every move before it happens; elsewhere (and
    in the ``offscreen`` tests) a dialog that moved out is moved back right after its ``Move`` event.
    A dialog is left alone until it is visible: moving it earlier would mark it as explicitly placed,
    and Qt would no longer center it on the main window when it shows.
    """

    def __init__(self, host: QWidget, rects: WindowRects, native: PositionClampFilter | None) -> None:
        """Create the confinement.

        Args:
            host: Main window.
            rects: Window rectangles matching ``native`` (native ones on Windows).
            native: The installed native filter, ``None`` off Windows.
        """
        super().__init__(host)
        self._host = host
        self._rects = rects
        self._native = native
        self._dialogs: list[QWidget] = []
        host.installEventFilter(self)

    def track(self, dialog: QWidget) -> None:
        """Keep a dialog inside the main window until ``untrack``.

        Args:
            dialog: Dialog about to run.
        """
        self._dialogs.append(dialog)
        if self._native is not None:
            self._native.track(dialog)
        else:
            dialog.installEventFilter(self)

    def untrack(self, dialog: QWidget) -> None:
        """Stop keeping a dialog inside the main window.

        Args:
            dialog: Dialog that has closed.
        """
        self._dialogs.remove(dialog)
        if self._native is not None:
            self._native.untrack(dialog)
        else:
            dialog.removeEventFilter(self)

    @override
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        kind = event.type()
        if watched is self._host and kind in {QEvent.Type.Move, QEvent.Type.Resize}:
            for dialog in tuple(self._dialogs):
                self._confine(dialog)
        elif kind == QEvent.Type.Move and isinstance(watched, QWidget) and watched in self._dialogs:
            self._confine(watched)
        return False

    def _confine(self, dialog: QWidget) -> None:
        """Move a dialog back inside the main window when it is not.

        Args:
            dialog: Tracked dialog.
        """
        if not dialog.isVisible():
            return
        current = self._rects.frame(dialog)
        target = clamped(current, self._rects.frame(self._host))
        if target != current:
            self._rects.move_frame(dialog, target.x, target.y)
