"""Notification area icon with its Show / Quit menu."""

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon, QWidget

from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.button_snapshot import ButtonSnapshot
from concentrator.presentation.shell.shell_snapshot import TraySnapshot

SHOW_REASONS = frozenset({QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick})


class TrayPanel(QObject):
    """Always visible icon; a click on it or on a notification asks to show the window.

    Emits ``action_requested(int)``. The icon is also used by ``QtAttention`` for the notifications.
    """

    action_requested = Signal(int)

    def __init__(self, icon: QIcon, window: QWidget) -> None:
        """Build the icon and its menu (not shown yet).

        Args:
            icon: Application icon.
            window: Main window, owner of the icon and of the menu.
        """
        super().__init__(window)
        self._menu = QMenu(window)
        self._show = QAction(self._menu)
        self._quit = QAction(self._menu)
        self._menu.addAction(self._show)
        self._menu.addSeparator()
        self._menu.addAction(self._quit)
        self._tray = QSystemTrayIcon(icon, self)
        self._tray.setContextMenu(self._menu)
        self._show_action = ActionIdEnum.TRAY_SHOW
        self._quit_action = ActionIdEnum.TRAY_QUIT
        self._show.triggered.connect(lambda: self.action_requested.emit(int(self._show_action)))
        self._quit.triggered.connect(lambda: self.action_requested.emit(int(self._quit_action)))
        self._tray.activated.connect(self._on_activated)
        self._tray.messageClicked.connect(lambda: self.action_requested.emit(int(self._show_action)))

    @property
    def tray_icon(self) -> QSystemTrayIcon:
        """The icon (handed to the attention adapter)."""
        return self._tray

    @property
    def menu_actions(self) -> tuple[QAction, QAction]:
        """Show and Quit (for tests)."""
        return self._show, self._quit

    def show(self) -> None:
        """Show the icon in the notification area."""
        self._tray.show()

    def hide(self) -> None:
        """Remove the icon (on quit, so no stale icon stays in the notification area)."""
        self._tray.hide()

    def render_snapshot(self, snapshot: TraySnapshot) -> None:
        """Show the tooltip and the menu texts.

        Args:
            snapshot: Tray state.
        """
        self._tray.setToolTip(snapshot.tooltip)
        self._show_action = snapshot.show_action.action
        self._quit_action = snapshot.quit_action.action
        _apply(self._show, snapshot.show_action)
        _apply(self._quit, snapshot.quit_action)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Show the window on a click or a double click (the context menu opens by itself).

        Args:
            reason: How the icon was activated.
        """
        if reason in SHOW_REASONS:
            self.action_requested.emit(int(self._show_action))


def _apply(action: QAction, snapshot: ButtonSnapshot) -> None:
    """Show one menu item.

    Args:
        action: Menu item.
        snapshot: Its state.
    """
    action.setText(snapshot.text)
    action.setEnabled(snapshot.enabled)
    action.setVisible(snapshot.visible)
