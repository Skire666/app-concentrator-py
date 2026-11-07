"""Content of the recovery dialog: situation, problems, restorable versions, action buttons."""

from typing import Final

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtWidgets import QLabel, QListWidget, QVBoxLayout, QWidget

from concentrator.presentation.storage.startup_snapshots import RecoverySnapshot
from concentrator.ui.support.styles import WARNING_PROPERTY
from concentrator.ui.widgets.button_column_widget import ButtonColumnWidget

_SPACING_PX: Final = 10
_LINE_BREAK: Final = "\n"


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


class RecoveryPanel(QWidget):
    """Emits ``action_requested(int)`` for its buttons and ``candidate_selected(int)`` for the list."""

    action_requested = Signal(int)
    candidate_selected = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build the panel.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._intro = _wrapped_label(self)
        self._path = _wrapped_label(self)
        self._path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._problems = _wrapped_label(self)
        self._problems.setProperty(WARNING_PROPERTY, True)
        self._caption = _wrapped_label(self)
        self._candidates = QListWidget(self)
        self._candidates.currentRowChanged.connect(self.candidate_selected)
        self._buttons = ButtonColumnWidget(self)
        self._buttons.action_requested.connect(self.action_requested)
        self._build_layout()

    @property
    def candidates(self) -> QListWidget:
        """List of restorable versions (for tests)."""
        return self._candidates

    @property
    def buttons(self) -> ButtonColumnWidget:
        """Action buttons (for tests)."""
        return self._buttons

    @property
    def problems_text(self) -> str:
        """Text of the problem lines (for tests)."""
        return self._problems.text()

    def render_snapshot(self, snapshot: RecoverySnapshot) -> None:
        """Show a recovery snapshot.

        Args:
            snapshot: Dialog state.
        """
        self.setUpdatesEnabled(False)
        self._intro.setText(snapshot.intro)
        self._path.setText(snapshot.path)
        self._problems.setText(_LINE_BREAK.join(snapshot.problems))
        self._problems.setVisible(bool(snapshot.problems))
        self._caption.setText(snapshot.candidates_caption)
        self._caption.setVisible(bool(snapshot.candidates))
        self._render_candidates(snapshot)
        self._buttons.render_snapshot(snapshot.buttons)
        self.setUpdatesEnabled(True)

    def _render_candidates(self, snapshot: RecoverySnapshot) -> None:
        """Show the versions without emitting ``candidate_selected``.

        Args:
            snapshot: Dialog state.
        """
        blocker = QSignalBlocker(self._candidates)
        self._candidates.clear()
        self._candidates.addItems([candidate.text for candidate in snapshot.candidates])
        selected = next((row for row, candidate in enumerate(snapshot.candidates) if candidate.selected), -1)
        self._candidates.setCurrentRow(selected)
        self._candidates.setVisible(bool(snapshot.candidates))
        blocker.unblock()

    def _build_layout(self) -> None:
        """Stack the widgets vertically."""
        layout = QVBoxLayout(self)
        layout.setSpacing(_SPACING_PX)
        for widget in (self._intro, self._path, self._problems, self._caption, self._candidates, self._buttons):
            layout.addWidget(widget)
