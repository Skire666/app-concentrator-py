"""Content of the first-run dialog: explanation, notice, default location, action buttons."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from concentrator.presentation.storage.startup_snapshots import FirstRunSnapshot
from concentrator.ui.support.styles import WARNING_PROPERTY
from concentrator.ui.widgets.button_column_widget import ButtonColumnWidget


def _wrapped_label(parent: QWidget) -> QLabel:
    """A plain-text label that wraps.

    Args:
        parent: Parent widget.

    Returns:
        The label.
    """
    label = QLabel(parent)
    label.setTextFormat(Qt.TextFormat.PlainText)
    label.setWordWrap(True)
    return label


class FirstRunPanel(QWidget):
    """Emits ``action_requested(int)`` for its buttons."""

    action_requested = Signal(int)

    def __init__(self, spacing_px: int, parent: QWidget | None = None) -> None:
        """Build the panel.

        Args:
            spacing_px: ``ui.dialog_spacing_px``.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._intro = _wrapped_label(self)
        self._notice = _wrapped_label(self)
        self._notice.setProperty(WARNING_PROPERTY, True)
        self._default_location = _wrapped_label(self)
        self._default_location.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._buttons = ButtonColumnWidget(self)
        self._buttons.action_requested.connect(self.action_requested)
        layout = QVBoxLayout(self)
        layout.setSpacing(spacing_px)
        for widget in (self._intro, self._notice, self._default_location, self._buttons):
            layout.addWidget(widget)
        layout.addStretch(1)

    @property
    def buttons(self) -> ButtonColumnWidget:
        """Action buttons (for tests)."""
        return self._buttons

    @property
    def notice_text(self) -> str:
        """Text of the "file not found" notice (for tests)."""
        return self._notice.text()

    def render_snapshot(self, snapshot: FirstRunSnapshot) -> None:
        """Show a first-run snapshot.

        Args:
            snapshot: Dialog state.
        """
        self.setUpdatesEnabled(False)
        self._intro.setText(snapshot.intro)
        self._notice.setText(snapshot.notice)
        self._notice.setVisible(bool(snapshot.notice))
        self._default_location.setText(snapshot.default_location)
        self._buttons.render_snapshot(snapshot.buttons)
        self.setUpdatesEnabled(True)
