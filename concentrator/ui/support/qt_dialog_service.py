"""``DialogPort`` on ``QMessageBox`` and ``QFileDialog``; button texts come from the catalogs.

Every dialog runs through a ``DialogRunner``: ``ModalHost`` once the main window exists (dimmed,
centered, kept inside; ADR-036), ``ScreenDialogRunner`` before.
"""

from typing import override

from PySide6.QtWidgets import QFileDialog, QMessageBox

from concentrator.presentation.ports.dialog_port import DialogPort
from concentrator.ui.support.modal_host import DialogRunner


def _normalized(path: str) -> str | None:
    """Return a chosen path with ``/`` separators, ``None`` when the dialog was cancelled.

    Args:
        path: Path returned by Qt, ``""`` on cancel.

    Returns:
        The normalized path or ``None``.
    """
    return path.replace("\\", "/") if path else None


class QtDialogService(DialogPort):
    """Modal dialogs run by a ``DialogRunner``."""

    def __init__(self, runner: DialogRunner) -> None:
        """Create the service.

        Args:
            runner: Runs the dialogs (and gives their parent).
        """
        self._runner = runner

    @override
    def confirm(self, title: str, message: str, accept_text: str, reject_text: str) -> bool:
        box = QMessageBox(
            QMessageBox.Icon.Question, title, message, QMessageBox.StandardButton.NoButton, self._runner.parent
        )
        accept = box.addButton(accept_text, QMessageBox.ButtonRole.AcceptRole)
        reject = box.addButton(reject_text, QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(reject)
        box.setEscapeButton(reject)
        self._runner.run(box)
        return box.clickedButton() is accept

    @override
    def inform(self, title: str, message: str, button_text: str) -> None:
        self._message(QMessageBox.Icon.Information, title, message, button_text)

    @override
    def warn(self, title: str, message: str, button_text: str) -> None:
        self._message(QMessageBox.Icon.Warning, title, message, button_text)

    @override
    def error(self, title: str, message: str, button_text: str) -> None:
        self._message(QMessageBox.Icon.Critical, title, message, button_text)

    @override
    def choose_open_file(self, title: str, directory: str, name_filter: str) -> str | None:
        parent = self._runner.parent
        path, _selected = self._runner.dimmed(
            lambda: QFileDialog.getOpenFileName(parent, title, directory, name_filter)
        )
        return _normalized(path)

    @override
    def choose_save_file(self, title: str, directory: str, name_filter: str) -> str | None:
        parent = self._runner.parent
        path, _selected = self._runner.dimmed(
            lambda: QFileDialog.getSaveFileName(
                parent, title, directory, name_filter, options=QFileDialog.Option.DontConfirmOverwrite
            )
        )
        return _normalized(path)

    @override
    def choose_folder(self, title: str, directory: str) -> str | None:
        parent = self._runner.parent
        return _normalized(self._runner.dimmed(lambda: QFileDialog.getExistingDirectory(parent, title, directory)))

    def _message(self, icon: QMessageBox.Icon, title: str, message: str, button_text: str) -> None:
        """Show a message with one closing button.

        Args:
            icon: Message icon.
            title: Window title.
            message: Text.
            button_text: Label of the closing button.
        """
        box = QMessageBox(icon, title, message, QMessageBox.StandardButton.NoButton, self._runner.parent)
        button = box.addButton(button_text, QMessageBox.ButtonRole.AcceptRole)
        box.setDefaultButton(button)
        box.setEscapeButton(button)
        self._runner.run(box)
