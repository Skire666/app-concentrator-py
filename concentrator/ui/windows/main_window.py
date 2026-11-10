"""Top-level window: module bar on the full height, pages above a one-line status bar (ADR-020)."""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import override

from PySide6.QtCore import QByteArray, QPoint, Qt
from PySide6.QtGui import QCloseEvent, QIcon
from PySide6.QtWidgets import QApplication, QHBoxLayout, QStackedWidget, QVBoxLayout, QWidget

from concentrator.presentation.common.layout_keys import (
    LAYOUT_FOCUS_PAGE_SPLITTER,
    LAYOUT_JOURNAL_HEADER,
    LAYOUT_JOURNAL_SPLITTER,
    LAYOUT_MAIN_WINDOW_GEOMETRY,
)
from concentrator.presentation.common.layout_state_keeper import LayoutStateKeeper
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.shell.main_window_presenters import MainWindowPresenters
from concentrator.presentation.shell.shell_snapshot import ShellSnapshot
from concentrator.presentation.shell.window_layouts import WindowLayouts
from concentrator.ui.panels.module_bar_panel import ModuleBarPanel
from concentrator.ui.panels.presets_panel import PresetsPanel
from concentrator.ui.panels.special_options_panel import SpecialOptionsPanel
from concentrator.ui.panels.status_bar_panel import StatusBarPanel
from concentrator.ui.panels.timer_panel import TimerPanel
from concentrator.ui.support.icon_loader import IconLoader
from concentrator.ui.support.layout_codec import decode_blob, encode_blob
from concentrator.ui.windows.focus_page import FocusPage
from concentrator.ui.windows.journal_page import JournalPage
from concentrator.ui.windows.settings_page import SettingsPage

_logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _LayoutPart:
    """One persisted piece of layout: its key, how to export, restore and reset it."""

    key: str
    export: Callable[[], QByteArray]
    restore: Callable[[QByteArray], bool]
    reset: Callable[[], None]


class MainWindow(QWidget):
    """Composes the shell panels, wires them to the presenters and persists the layout."""

    def __init__(
        self,
        *,
        presenters: MainWindowPresenters,
        renderer: RenderCoordinator,
        layout_keeper: LayoutStateKeeper,
        layouts: WindowLayouts,
        icons: IconLoader,
        app_icon: QIcon,
    ) -> None:
        """Build the window (not shown).

        Args:
            presenters: Presenters of the module bar, pages, status bar, timer and shutdown.
            renderer: Render coordinator the panels are registered with.
            layout_keeper: Store of the layout blobs.
            layouts: Sizes from the ini.
            icons: Loader of the module icons.
            app_icon: Window and taskbar icon.
        """
        super().__init__(None)
        self._shutdown = presenters.shutdown
        self._layout_keeper = layout_keeper
        self._shell_layout = layouts.shell
        self.setWindowIcon(app_icon)
        self.setMinimumSize(layouts.shell.min_width_px, layouts.shell.min_height_px)
        self._module_bar = ModuleBarPanel(layouts.shell.module_bar_width_px, icons, self)
        self._status_bar = StatusBarPanel(self)
        self._pages = QStackedWidget(self)
        self._focus_page = FocusPage(layouts.shell.zone1_ratio_percent, layouts.timer, self._pages)
        self._journal_page = JournalPage(layouts.journal, self._pages)
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
    def journal_page(self) -> JournalPage:
        """Menu B page."""
        return self._journal_page

    @property
    def timer_panel(self) -> TimerPanel:
        """Timer at the top of zone 2."""
        return self._focus_page.timer_panel

    @property
    def presets_panel(self) -> PresetsPanel:
        """Favorites of zone 2."""
        return self._focus_page.presets_panel

    @property
    def special_options_panel(self) -> SpecialOptionsPanel:
        """Special options of zone 2."""
        return self._focus_page.special_options_panel

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
        self._settings_page.render_snapshot(snapshot.settings_placeholder)
        self._pages.setCurrentIndex(snapshot.active_page_index)
        self.setUpdatesEnabled(True)

    def restore_layout(self) -> None:
        """Restore geometry, splitters and columns once, before ``show()``; fall back to the ini defaults."""
        for part in self._layout_parts():
            if not self._restore_blob(part):
                part.reset()

    def save_layout(self) -> None:
        """Export geometry, splitters and columns (on close, never on every resize)."""
        for part in self._layout_parts():
            self._layout_keeper.save(part.key, encode_blob(part.export()))

    def reset_layout(self) -> None:
        """Apply the ini defaults at once ("Reset layout"; the stored blobs are removed by the presenter)."""
        if self.isMaximized() or self.isFullScreen():
            self.showNormal()
        for part in self._layout_parts():
            part.reset()

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

    def _layout_parts(self) -> tuple[_LayoutPart, ...]:
        """Every persisted piece of layout, in restore order.

        Returns:
            The parts.
        """
        focus, journal = self._focus_page, self._journal_page
        return (
            _LayoutPart(
                LAYOUT_MAIN_WINDOW_GEOMETRY, self.saveGeometry, self.restoreGeometry, self._apply_default_geometry
            ),
            _LayoutPart(
                LAYOUT_FOCUS_PAGE_SPLITTER, focus.splitter_state, focus.restore_splitter_state, focus.reset_splitter
            ),
            _LayoutPart(
                LAYOUT_JOURNAL_SPLITTER, journal.splitter_state, journal.restore_splitter_state, journal.reset_splitter
            ),
            _LayoutPart(
                LAYOUT_JOURNAL_HEADER, journal.header_state, journal.restore_header_state, journal.reset_columns
            ),
        )

    def _wire(self, presenters: MainWindowPresenters, renderer: RenderCoordinator) -> None:
        """Connect the panels to their presenters and register their render sections.

        Args:
            presenters: Presenters of the panels.
            renderer: Render coordinator.
        """
        shell, status_bar, timer = presenters.shell, presenters.status_bar, presenters.timer
        self._module_bar.action_requested.connect(shell.on_action_requested)
        self._status_bar.action_requested.connect(status_bar.on_action_requested)
        self.timer_panel.action_requested.connect(timer.on_action_requested)
        renderer.register(RenderSectionEnum.SHELL, shell.build_shell_snapshot, self.render_shell)
        renderer.register(RenderSectionEnum.STATUS_BAR, status_bar.build_snapshot, self._status_bar.render_snapshot)
        renderer.register(RenderSectionEnum.TIMER, timer.build_snapshot, self.timer_panel.render_snapshot)
        self._wire_timer_extras(presenters, renderer)
        self._journal_page.connect_presenter(presenters.journal, renderer)

    def _wire_timer_extras(self, presenters: MainWindowPresenters, renderer: RenderCoordinator) -> None:
        """Connect the favorites and the special options and register their render sections.

        Args:
            presenters: Presenters of the panels.
            renderer: Render coordinator.
        """
        presets, chime = presenters.presets, presenters.chime
        self.presets_panel.action_requested.connect(presets.on_action_requested)
        self.presets_panel.preset_action_requested.connect(presets.on_preset_action_requested)
        self.special_options_panel.action_requested.connect(chime.on_action_requested)
        renderer.register(RenderSectionEnum.PRESETS, presets.build_snapshot, self.presets_panel.render_snapshot)
        renderer.register(
            RenderSectionEnum.SPECIAL_OPTIONS, chime.build_snapshot, self.special_options_panel.render_snapshot
        )

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

    def _restore_blob(self, part: _LayoutPart) -> bool:
        """Restore one saved blob.

        Args:
            part: Piece of layout.

        Returns:
            Whether a saved blob was restored; an invalid one is logged at WARNING.
        """
        text = self._layout_keeper.load(part.key)
        if text is None:
            return False
        blob = decode_blob(text)
        if blob is None or not part.restore(blob):
            _logger.warning("Saved layout %s is invalid; the defaults are used", part.key)
            return False
        return True

    def _apply_default_geometry(self) -> None:
        """Default size from the ini, centered on the screen."""
        self.resize(self._shell_layout.default_width_px, self._shell_layout.default_height_px)
        available = self.screen().availableGeometry()
        self.move(available.center() - QPoint(self.width() // 2, self.height() // 2))
