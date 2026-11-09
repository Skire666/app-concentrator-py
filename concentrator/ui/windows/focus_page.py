"""Menu A page: zone 1 (TODO manager, phase 5) and zone 2 (timer, focus queue later, favorites, options)."""

from typing import Final

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtWidgets import QSplitter, QVBoxLayout, QWidget

from concentrator.presentation.shell.shell_snapshot import ShellSnapshot
from concentrator.presentation.timer.timer_layout import TimerLayout
from concentrator.ui.panels.presets_panel import PresetsPanel
from concentrator.ui.panels.special_options_panel import SpecialOptionsPanel
from concentrator.ui.panels.timer_panel import TimerPanel
from concentrator.ui.widgets.placeholder_widget import PlaceholderWidget

_PERCENT: Final = 100


class FocusPage(QWidget):
    """Zone 1 and zone 2 in a horizontal splitter.

    Zone 2, top to bottom: timer, the room of the focus queue (phase 7), favorites, special options.
    """

    def __init__(self, zone1_ratio_percent: int, timer_layout: TimerLayout, parent: QWidget | None = None) -> None:
        """Build the page.

        Args:
            zone1_ratio_percent: Initial share of zone 1 (``ui.zone1_ratio_percent``).
            timer_layout: Font of the timer digits and spacing of the favorites.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._ratio = zone1_ratio_percent
        self._splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self._splitter.setChildrenCollapsible(False)
        self._zone1 = PlaceholderWidget(self._splitter)
        zone2 = QWidget(self._splitter)
        self._timer = TimerPanel(timer_layout, zone2)
        self._presets = PresetsPanel(timer_layout, zone2)
        self._options = SpecialOptionsPanel(zone2)
        stack = QVBoxLayout(zone2)
        stack.setSpacing(timer_layout.spacing_px)
        stack.addWidget(self._timer)
        stack.addStretch(1)
        stack.addWidget(self._presets)
        stack.addWidget(self._options)
        self._splitter.addWidget(self._zone1)
        self._splitter.addWidget(zone2)
        self._splitter.setStretchFactor(0, zone1_ratio_percent)
        self._splitter.setStretchFactor(1, _PERCENT - zone1_ratio_percent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._splitter)
        self.reset_splitter()

    @property
    def zone1_text(self) -> str:
        """Text of zone 1 (for tests)."""
        return self._zone1.text

    @property
    def timer_panel(self) -> TimerPanel:
        """Timer at the top of zone 2."""
        return self._timer

    @property
    def presets_panel(self) -> PresetsPanel:
        """Favorites, below the room of the focus queue."""
        return self._presets

    @property
    def special_options_panel(self) -> SpecialOptionsPanel:
        """Special options at the bottom of zone 2."""
        return self._options

    def render_snapshot(self, snapshot: ShellSnapshot) -> None:
        """Show the zone 1 placeholder.

        Args:
            snapshot: Shell state.
        """
        self._zone1.set_text(snapshot.focus_zone1_placeholder)

    def splitter_state(self) -> QByteArray:
        """Return the splitter blob to persist."""
        return self._splitter.saveState()

    def restore_splitter_state(self, state: QByteArray) -> bool:
        """Restore a persisted splitter blob.

        Args:
            state: Blob from ``splitter_state``.

        Returns:
            Whether Qt accepted it.
        """
        return self._splitter.restoreState(state)

    def reset_splitter(self) -> None:
        """Apply the ini ratio (sizes are distributed proportionally to the available width)."""
        self._splitter.setSizes([self._ratio, _PERCENT - self._ratio])

    def splitter_sizes(self) -> list[int]:
        """Return the current zone widths (for tests).

        Returns:
            Width of zone 1 and zone 2 in pixels.
        """
        return self._splitter.sizes()
