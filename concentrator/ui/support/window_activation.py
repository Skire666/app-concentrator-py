"""Bringing Concentrator to the front when it is launched a second time."""

import logging

from PySide6.QtWidgets import QApplication

_logger = logging.getLogger(__name__)


def bring_modal_dialog_to_front() -> None:
    """Show the open modal dialog in front: a second launch while a startup dialog is open.

    Windows may only flash the taskbar button instead.
    """
    dialog = QApplication.activeModalWidget()
    if dialog is None:
        _logger.info("Second launch before the main window: no dialog to bring to the front")
        return
    _logger.info("Second launch: bringing the open dialog to the front")
    dialog.raise_()
    dialog.activateWindow()
    QApplication.alert(dialog, 0)
