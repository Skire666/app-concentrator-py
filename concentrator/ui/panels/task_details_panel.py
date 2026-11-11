"""Details pane under the table: full text with its links, list, due date, repetition, state and dates."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFormLayout, QGroupBox, QLabel, QVBoxLayout, QWidget

from concentrator.presentation.todo.task_details_snapshot import TaskDetailsSnapshot
from concentrator.ui.widgets.link_text_browser import LinkTextBrowser


class TaskDetailsPanel(QGroupBox):
    """Read-only; the text is escaped before it becomes HTML, and its links are hyperlinks (ADR-014).

    Signals:
        link_activated(int): Number of the link clicked.
    """

    link_activated = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build the pane.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._text = LinkTextBrowser(self)
        self._text.link_activated.connect(self.link_activated.emit)
        self._empty = QLabel(self)
        self._empty.setTextFormat(Qt.TextFormat.PlainText)
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._form = QFormLayout()
        self._labels: list[tuple[QLabel, QLabel]] = []
        layout = QVBoxLayout(self)
        layout.addWidget(self._empty)
        layout.addWidget(self._text, 1)
        layout.addLayout(self._form)

    @property
    def text(self) -> str:
        """Full text shown (for tests)."""
        return self._text.toPlainText()

    @property
    def browser(self) -> LinkTextBrowser:
        """The text with its links (for tests)."""
        return self._text

    @property
    def values(self) -> tuple[str, ...]:
        """Values of the rows shown (for tests)."""
        return tuple(value.text() for _label, value in self._labels if value.isVisibleTo(self))

    def render_snapshot(self, snapshot: TaskDetailsSnapshot) -> None:
        """Show the task or the hint (idempotent).

        Args:
            snapshot: Pane state.
        """
        self.setUpdatesEnabled(False)
        self.setTitle(snapshot.title)
        self._text.set_lines(snapshot.lines)
        has_task = not snapshot.empty_text
        self._text.setVisible(has_task)
        self._empty.setText(snapshot.empty_text)
        self._empty.setVisible(not has_task)
        while len(self._labels) < len(snapshot.rows):
            pair = (QLabel(self), QLabel(self))
            pair[1].setTextFormat(Qt.TextFormat.PlainText)
            pair[1].setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self._form.addRow(*pair)
            self._labels.append(pair)
        for index, (label, value) in enumerate(self._labels):
            shown = index < len(snapshot.rows)
            label.setVisible(shown)
            value.setVisible(shown)
            if shown:
                label.setText(snapshot.rows[index].label)
                value.setText(snapshot.rows[index].value)
        self.setUpdatesEnabled(True)
