"""Top-level window: module bar on the full height, pages above a one-line status bar (ADR-020)."""

import logging
from collections.abc import Callable
from typing import override

from PySide6.QtCore import QByteArray, QPoint, Qt
from PySide6.QtGui import QCloseEvent, QIcon
from PySide6.QtWidgets import QApplication, QHBoxLayout, QStackedWidget, QVBoxLayout, QWidget

from concentrator.presentation.common.layout_keys import LAYOUT_FOCUS_PAGE_SPLITTER, LAYOUT_MAIN_WINDOW_GEOMETRY
from concentrator.presentation.common.layout_state_keeper import LayoutStateKeeper
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.ports.main_window_port import MainWindowPort
from concentrator.presentation.shell.main_window_presenters import MainWindowPresenters
from concentrator.presentation.shell.shell_layout import ShellLayout
from concentrator.presentation.shell.shell_snapshot import ShellSnapshot
from concentrator.presentation.timer.timer_layout import TimerLayout
from concentrator.ui.panels.module_bar_panel import ModuleBarPanel
from concentrator.ui.panels.status_bar_panel import StatusBarPanel
from concentrator.ui.panels.timer_panel import TimerPanel
from concentrator.ui.panels.tray_panel import TrayPanel
from concentrator.ui.support.icon_loader import IconLoader
from concentrator.ui.support.layout_codec import decode_blob, encode_blob
from concentrator.ui.windows.focus_page import FocusPage
from concentrator.ui.windows.journal_page import JournalPage
from concentrator.ui.windows.settings_page import SettingsPage

_logger = logging.getLogger(__name__)


class MainWindow(QWidget):
    """Composes the shell panels, wires them to the presenters and persists the layout."""

    def __init__(
        self,
        *,
        presenters: MainWindowPresenters,
        renderer: RenderCoordinator,
        layout_keeper: LayoutStateKeeper,
        shell_layout: ShellLayout,
        timer_layout: TimerLayout,
        icons: IconLoader,
        app_icon: QIcon,
    ) -> None:
        """Build the window (not shown).

        Args:
            presenters: Presenters of the module bar, pages, status bar, timer, tray and shutdown.
            renderer: Render coordinator the panels are registered with.
            layout_keeper: Store of the layout blobs.
            shell_layout: Sizes from the ini.
            timer_layout: Font of the timer digits.
            icons: Loader of the module icons.
            app_icon: Window, taskbar and notification area icon.
        """
        super().__init__(None)
        self._shutdown = presenters.shutdown
        self._layout_keeper = layout_keeper
        self._shell_layout = shell_layout
        self.setWindowIcon(app_icon)
        self.setMinimumSize(shell_layout.min_width_px, shell_layout.min_height_px)
        self._module_bar = ModuleBarPanel(shell_layout.module_bar_width_px, icons, self)
        self._status_bar = StatusBarPanel(self)
        self._tray = TrayPanel(app_icon, self)
        self._pages = QStackedWidget(self)
        self._focus_page = FocusPage(shell_layout.zone1_ratio_percent, timer_layout, self._pages)
        self._journal_page = JournalPage(self._pages)
        self._settings_page = SettingsPage(self._pages)
        self._build_layout()
        self._wire(presenters, renderer)

    @property
    def module_bar(self) -> ModuleBarPanel:
        """Module bar panel."""
        return self._module_bar

    @property
    def status_bar(self) -> StatusBarPanel:
        """Status bar panel."""
        return self._status_bar

    @property
    def focus_page(self) -> FocusPage:
        """Menu A page."""
        return self._focus_page

    @property
    def timer_panel(self) -> TimerPanel:
        """Timer at the top of zone 2."""
        return self._focus_page.timer_panel

    @property
    def tray(self) -> TrayPanel:
        """Notification area icon."""
        return self._tray

    @property
    def current_page_index(self) -> int:
        """Index of the visible page."""
        return self._pages.currentIndex()

    def render_shell(self, snapshot: ShellSnapshot) -> None:
        """Show the title, the module bar and the active page.

        Args:
            snapshot: Shell state.
        """
        self.setUpdatesEnabled(False)
        self.setWindowTitle(snapshot.window_title)
        self._module_bar.render_snapshot(snapshot)
        self._focus_page.render_snapshot(snapshot)
        self._journal_page.render_snapshot(snapshot.journal_placeholder)
        self._settings_page.render_snapshot(snapshot.settings_placeholder)
        self._pages.setCurrentIndex(snapshot.active_page_index)
        self.setUpdatesEnabled(True)

    def restore_layout(self) -> None:
        """Restore geometry and splitter once, before ``show()``; fall back to the ini defaults."""
        if not self._restore_blob(LAYOUT_MAIN_WINDOW_GEOMETRY, self.restoreGeometry):
            self._apply_default_geometry()
        if not self._restore_blob(LAYOUT_FOCUS_PAGE_SPLITTER, self._focus_page.restore_splitter_state):
            self._focus_page.reset_splitter()

    def save_layout(self) -> None:
        """Export geometry and splitter (on close, never on every resize)."""
        self._layout_keeper.save(LAYOUT_MAIN_WINDOW_GEOMETRY, encode_blob(self.saveGeometry()))
        self._layout_keeper.save(LAYOUT_FOCUS_PAGE_SPLITTER, encode_blob(self._focus_page.splitter_state()))

    def bring_to_front(self) -> None:
        """Show the window in front (second launch); Windows may only flash the taskbar button."""
        self.setWindowState((self.windowState() & ~Qt.WindowState.WindowMinimized) | Qt.WindowState.WindowActive)
        self.show()
        self.raise_()
        self.activateWindow()
        QApplication.alert(self, 0)

    @override
    def closeEvent(self, event: QCloseEvent) -> None:
        if not self._shutdown.may_close():
            event.ignore()
            return
        self.save_layout()
        super().closeEvent(event)

    def _wire(self, presenters: MainWindowPresenters, renderer: RenderCoordinator) -> None:
        """Connect the panels to their presenters and register their render sections.

        Args:
            presenters: Presenters of the panels.
            renderer: Render coordinator.
        """
        shell, status_bar, timer, tray = presenters.shell, presenters.status_bar, presenters.timer, presenters.tray
        self._module_bar.action_requested.connect(shell.on_action_requested)
        self._status_bar.action_requested.connect(status_bar.on_action_requested)
        self.timer_panel.action_requested.connect(timer.on_action_requested)
        self._tray.action_requested.connect(tray.on_action_requested)
        renderer.register(RenderSectionEnum.SHELL, shell.build_shell_snapshot, self.render_shell)
        renderer.register(RenderSectionEnum.STATUS_BAR, status_bar.build_snapshot, self._status_bar.render_snapshot)
        renderer.register(RenderSectionEnum.TIMER, timer.build_snapshot, self.timer_panel.render_snapshot)
        renderer.register(RenderSectionEnum.TRAY, tray.build_snapshot, self._tray.render_snapshot)

    def _build_layout(self) -> None:
        """``QHBoxLayout[module bar, QVBoxLayout[pages, status bar]]``."""
        for page in (self._focus_page, self._journal_page, self._settings_page):
            self._pages.addWidget(page)
        content = QVBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)
        content.addWidget(self._pages, 1)
        content.addWidget(self._status_bar)
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._module_bar)
        root.addLayout(content, 1)

    def _restore_blob(self, key: str, restore: Callable[[QByteArray], bool]) -> bool:
        """Restore one saved blob.

        Args:
            key: Layout key.
            restore: Qt restore method.

        Returns:
            Whether a saved blob was restored; an invalid one is logged at WARNING.
        """
        text = self._layout_keeper.load(key)
        if text is None:
            return False
        blob = decode_blob(text)
        if blob is None or not restore(blob):
            _logger.warning("Saved layout %s is invalid; the defaults are used", key)
            return False
        return True

    def _apply_default_geometry(self) -> None:
        """Default size from the ini, centered on the screen."""
        self.resize(self._shell_layout.default_width_px, self._shell_layout.default_height_px)
        available = self.screen().availableGeometry()
        self.move(available.center() - QPoint(self.width() // 2, self.height() // 2))


class MainWindowHandle(MainWindowPort):
    """``MainWindowPort`` on the main window (a ``QWidget`` cannot subclass a ``Protocol`` directly)."""

    def __init__(self, window: MainWindow) -> None:
        """Wrap the window.

        Args:
            window: Main window.
        """
        self._window = window

    @override
    def show_in_front(self) -> None:
        self._window.bring_to_front()

    @override
    def request_close(self) -> None:
        self._window.close()
