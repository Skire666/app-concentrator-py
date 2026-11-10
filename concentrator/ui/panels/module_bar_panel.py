"""Left vertical bar with the Focus, Journal and Settings buttons (full window height)."""

from types import MappingProxyType
from typing import Final, override

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QSizePolicy, QToolButton, QVBoxLayout, QWidget

from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.shell.shell_snapshot import ModuleButtonSnapshot, ShellSnapshot
from concentrator.ui.support.icon_loader import IconLoader
from concentrator.ui.support.styles import HIGHLIGHTED_PROPERTY, MODULE_BAR_STYLE
from concentrator.ui.widgets.badge_button import BadgeButton

MODULE_ICON_FILES: Final = MappingProxyType(
    {
        ActionIdEnum.SHELL_SHOW_FOCUS: "module-focus.svg",
        ActionIdEnum.SHELL_SHOW_JOURNAL: "module-journal.svg",
        ActionIdEnum.SHELL_SHOW_SETTINGS: "module-settings.svg",
    }
)
_ICON_WIDTH_RATIO: Final = 0.4
_MARGIN_PX: Final = 6


class _ModuleButton(BadgeButton):
    """Checkable tool button whose checked state only comes from the snapshot; it may show a badge."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    @override
    def nextCheckState(self) -> None:
        """Keep the checked state on click: the next render decides it."""

    def apply(self, snapshot: ModuleButtonSnapshot) -> None:
        """Show one button snapshot.

        Args:
            snapshot: Button state.
        """
        self.setText(snapshot.text)
        self.setToolTip(snapshot.tooltip)
        self.setChecked(snapshot.checked)
        self.setEnabled(snapshot.enabled)
        self.set_badge(snapshot.badge)
        if self.property(HIGHLIGHTED_PROPERTY) != snapshot.highlighted:
            self.setProperty(HIGHLIGHTED_PROPERTY, snapshot.highlighted)
            self.style().unpolish(self)
            self.style().polish(self)


class ModuleBarPanel(QWidget):
    """Emits ``action_requested(int)`` when a module button is clicked."""

    action_requested = Signal(int)

    def __init__(self, width_px: int, icons: IconLoader, parent: QWidget | None = None) -> None:
        """Build the bar.

        Args:
            width_px: ``ui.module_bar_width_px``.
            icons: Loader of the module icons.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setFixedWidth(width_px)
        self.setStyleSheet(MODULE_BAR_STYLE)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(_MARGIN_PX, _MARGIN_PX, _MARGIN_PX, _MARGIN_PX)
        icon_px = round(width_px * _ICON_WIDTH_RATIO)
        self._buttons: dict[ActionIdEnum, _ModuleButton] = {}
        for action, file_name in MODULE_ICON_FILES.items():
            button = _ModuleButton(self)
            button.setIcon(icons.icon(file_name))
            button.setIconSize(QSize(icon_px, icon_px))
            button.clicked.connect(lambda _checked=False, value=int(action): self.action_requested.emit(value))
            layout.addWidget(button)
            self._buttons[action] = button
        layout.addStretch(1)

    def button(self, action: ActionIdEnum) -> QToolButton:
        """Return the button of an action (for tests and accessibility wiring).

        Args:
            action: Page action.

        Returns:
            The button.
        """
        return self._buttons[action]

    def render_snapshot(self, snapshot: ShellSnapshot) -> None:
        """Show the module buttons of a shell snapshot.

        Args:
            snapshot: Shell state.
        """
        self.setUpdatesEnabled(False)
        for item in snapshot.module_buttons:
            button = self._buttons.get(item.action)
            if button is not None:
                button.apply(item)
        self.setUpdatesEnabled(True)
