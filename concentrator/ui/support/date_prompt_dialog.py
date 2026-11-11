"""Dialog asking for one date (bulk due date), run by ``ModalHost`` like every dialog (ADR-036)."""

from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtWidgets import QDateEdit, QDialog, QDialogButtonBox, QFormLayout, QLabel, QVBoxLayout, QWidget

from concentrator.presentation.ports.dialog_port import DatePrompt


class DatePromptDialog(QDialog):
    """A calendar date field with OK and Cancel buttons labelled from the catalog."""

    def __init__(self, prompt: DatePrompt, parent: QWidget | None) -> None:
        """Build the dialog (not shown).

        Args:
            prompt: Texts and initial date.
            parent: Main window (Qt centers the dialog on it).
        """
        super().__init__(parent)
        self.setWindowTitle(prompt.title)
        self._date = QDateEdit(self)
        self._date.setCalendarPopup(True)
        self._date.setDisplayFormat(prompt.date_format)
        self._date.setDate(QDate(prompt.initial.year, prompt.initial.month, prompt.initial.day))
        buttons = QDialogButtonBox(self)
        self._accept = buttons.addButton(prompt.accept_text, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton(prompt.reject_text, QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form = QFormLayout()
        form.addRow(QLabel(prompt.label, self), self._date)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    @property
    def date_input(self) -> QDateEdit:
        """The date field (for tests)."""
        return self._date

    def chosen(self) -> date:
        """Return the date of the field.

        Returns:
            The date.
        """
        value = self._date.date()
        return date(value.year(), value.month(), value.day())
