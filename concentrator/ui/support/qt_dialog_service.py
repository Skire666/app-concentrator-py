"""``DialogPort`` on ``QMessageBox`` and ``QFileDialog``; button texts come from the catalogs."""

from typing import override

from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from concentrator.presentation.ports.dialog_port import DialogPort


def _normalized(path: str) -> str | None:
    """Return a chosen path with ``/`` separators, ``None`` when the dialog was cancelled.

    Args:
        path: Path returned by Qt, ``""`` on cancel.

    Returns:
        The normalized path or ``None``.
    """
    return path.replace("\\", "/") if path else None


class QtDialogService(DialogPort):
    """Modal dialogs parented to the main window."""

    def __init__(self, parent: QWidget | None) -> None:
        """Create the service.

        Args:
            parent: Window the dialogs are centered on.
        """
        self._parent = parent

    @override
    def confirm(self, title: str, message: str, accept_text: str, reject_text: str) -> bool:
        box = QMessageBox(QMessageBox.Icon.Question, title, message, QMessageBox.StandardButton.NoButton, self._parent)
        accept = box.addButton(accept_text, QMessageBox.ButtonRole.AcceptRole)
        reject = box.addButton(reject_text, QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(reject)
        box.setEscapeButton(reject)
        box.exec()
        return box.clickedButton() is accept

    @override
    def inform(self, title: str, message: str, button_text: str) -> None:
        self._message(QMessageBox.Icon.Information, title, message, button_text)

    @override
    def error(self, title: str, message: str, button_text: str) -> None:
        self._message(QMessageBox.Icon.Critical, title, message, button_text)

    @override
    def choose_open_file(self, title: str, directory: str, name_filter: str) -> str | None:
        path, _selected = QFileDialog.getOpenFileName(self._parent, title, directory, name_filter)
        return _normalized(path)

    @override
    def choose_save_file(self, title: str, directory: str, name_filter: str) -> str | None:
        path, _selected = QFileDialog.getSaveFileName(self._parent, title, directory, name_filter)
        return _normalized(path)

    @override
    def choose_folder(self, title: str, directory: str) -> str | None:
        return _normalized(QFileDialog.getExistingDirectory(self._parent, title, directory))

    def _message(self, icon: QMessageBox.Icon, title: str, message: str, button_text: str) -> None:
        """Show a message with one closing button.

        Args:
            icon: Message icon.
            title: Window title.
            message: Text.
            button_text: Label of the closing button.
        """
        box = QMessageBox(icon, title, message, QMessageBox.StandardButton.NoButton, self._parent)
        button = box.addButton(button_text, QMessageBox.ButtonRole.AcceptRole)
        box.setDefaultButton(button)
        box.setEscapeButton(button)
        box.exec()
