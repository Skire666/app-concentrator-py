"""Runs the modal dialogs over the main window: dimmed, centered, kept inside (ADR-036)."""

from collections.abc import Callable
from typing import Final, Protocol, Self, override

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QDialog, QWidget

from concentrator.ui.support.dialog_confinement import DialogConfinement
from concentrator.ui.support.dimming_overlay import DimmingOverlay
from concentrator.ui.support.position_clamp_filter import PositionClampFilter
from concentrator.ui.support.window_rects import NativeWindowRects, QtWindowRects

WINDOWS_PLATFORM: Final = "windows"


class DialogRunner(Protocol):
    """How ``QtDialogService`` shows its dialogs."""

    @property
    def parent(self) -> QWidget | None:
        """Parent of the dialogs (Qt centers a parented dialog on it)."""
        ...

    def run(self, dialog: QDialog) -> None:
        """Run a modal dialog until it closes.

        Args:
            dialog: Dialog parented to ``parent``.
        """
        ...

    def dimmed[T](self, operation: Callable[[], T]) -> T:
        """Run an operation that opens a dialog this runner cannot move (the Windows file picker).

        Args:
            operation: Opens the dialog and returns its result.

        Returns:
            The operation's result.
        """
        ...


class ScreenDialogRunner(DialogRunner):
    """Before the main window exists: dialogs without parent, centered on the screen by Qt."""

    @property
    @override
    def parent(self) -> QWidget | None:
        return None

    @override
    def run(self, dialog: QDialog) -> None:
        dialog.exec()

    @override
    def dimmed[T](self, operation: Callable[[], T]) -> T:
        return operation()


class ModalHost(DialogRunner):
    """Dialogs over the visible main window: dimming layer, centered by Qt on the window, clamped inside.

    A minimized window is restored first. While the window is hidden, dialogs behave as before the
    window existed.
    """

    def __init__(self, window: QWidget, overlay: DimmingOverlay, confinement: DialogConfinement) -> None:
        """Create the host; ``create`` builds the parts for the current platform.

        Args:
            window: Main window.
            overlay: Its dimming layer.
            confinement: Keeps the dialogs inside it.
        """
        self._window = window
        self._overlay = overlay
        self._confinement = confinement

    @classmethod
    def create(cls, window: QWidget, opacity_percent: int) -> Self:
        """Build the host; on the Windows platform the native position filter is installed.

        Args:
            window: Main window.
            opacity_percent: ``ui.dialog_overlay_opacity_percent``.

        Returns:
            The host.
        """
        overlay = DimmingOverlay(window, opacity_percent)
        application = QCoreApplication.instance()
        if QGuiApplication.platformName() != WINDOWS_PLATFORM or application is None:
            return cls(window, overlay, DialogConfinement(window, QtWindowRects(), None))
        rects = NativeWindowRects()
        native = PositionClampFilter(rects, window)
        application.installNativeEventFilter(native)
        window.destroyed.connect(lambda: application.removeNativeEventFilter(native))
        return cls(window, overlay, DialogConfinement(window, rects, native))

    @property
    @override
    def parent(self) -> QWidget | None:
        return self._window

    @override
    def run(self, dialog: QDialog) -> None:
        if not self._window.isVisible():
            dialog.exec()
            return
        self._prepare()
        self._confinement.track(dialog)
        try:
            dialog.exec()
        finally:
            self._confinement.untrack(dialog)
            self._overlay.release()

    @override
    def dimmed[T](self, operation: Callable[[], T]) -> T:
        if not self._window.isVisible():
            return operation()
        self._prepare()
        try:
            return operation()
        finally:
            self._overlay.release()

    def _prepare(self) -> None:
        """Restore a minimized window and dim it."""
        state = self._window.windowState()
        if state & Qt.WindowState.WindowMinimized:
            self._window.setWindowState(state & ~Qt.WindowState.WindowMinimized)
        self._overlay.acquire()
