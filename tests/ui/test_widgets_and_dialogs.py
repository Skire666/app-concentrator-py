from pathlib import Path

import pytest
from PySide6.QtCore import QByteArray, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton, QWidget
from pytestqt.qtbot import QtBot

from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.button_snapshot import ButtonSnapshot
from concentrator.presentation.shell.shell_snapshot import StatusBarSnapshot
from concentrator.ui.panels.status_bar_panel import StatusBarPanel
from concentrator.ui.support.icon_loader import IconLoader
from concentrator.ui.support.layout_codec import decode_blob, encode_blob
from concentrator.ui.support.modal_host import ModalHost
from concentrator.ui.support.qt_clipboard import QtClipboard
from concentrator.ui.support.qt_dialog_service import QtDialogService
from concentrator.ui.widgets.snapshot_button import SnapshotButton

pytestmark = pytest.mark.ui


def _click_in_next_message_box(text: str) -> None:
    def click() -> None:
        box = QApplication.activeModalWidget()
        assert isinstance(box, QMessageBox)
        buttons = [button for button in box.findChildren(QPushButton) if button.text() == text]
        buttons[0].click()

    QTimer.singleShot(0, click)


def test_snapshot_button_applies_the_snapshot_and_emits_its_action(qtbot: QtBot) -> None:
    button = SnapshotButton()
    qtbot.addWidget(button)
    button.setCheckable(True)
    snapshot = ButtonSnapshot(
        text="ENG", tooltip="tip", enabled=True, visible=True, action=ActionIdEnum.SHELL_TOGGLE_LANGUAGE, checked=True
    )

    received: list[int] = []
    button.action_requested.connect(received.append)

    button.apply(snapshot)
    button.click()

    assert (button.text(), button.toolTip(), button.isEnabled()) == ("ENG", "tip", True)
    assert received == [int(ActionIdEnum.SHELL_TOGGLE_LANGUAGE)]


def test_layout_codec_round_trip_and_invalid_text() -> None:
    blob = QByteArray(b"\x00\x01\xffqt")

    assert decode_blob(encode_blob(blob)) == blob
    assert decode_blob("not base64!") is None


def test_icon_loader_returns_a_null_icon_for_a_missing_file(qtbot: QtBot, tmp_path: Path) -> None:
    del qtbot

    assert IconLoader(tmp_path).icon("absent.svg").isNull()


@pytest.mark.parametrize(("clicked", "expected"), [("Yes!", True), ("No!", False)])
def test_confirm_returns_the_user_choice_with_catalog_button_texts(qtbot: QtBot, clicked: str, expected: bool) -> None:
    parent = QWidget()
    qtbot.addWidget(parent)
    _click_in_next_message_box(clicked)

    assert QtDialogService(ModalHost.create(parent, 10)).confirm("Title", "Question?", "Yes!", "No!") is expected


@pytest.mark.parametrize(("clicked", "expected"), [("Save", 0), ("Discard", 1), ("Cancel", 2)])
def test_choose_returns_the_index_of_the_clicked_answer(qtbot: QtBot, clicked: str, expected: int) -> None:
    parent = QWidget()
    qtbot.addWidget(parent)
    _click_in_next_message_box(clicked)

    service = QtDialogService(ModalHost.create(parent, 10))

    assert service.choose("Title", "Question?", ("Save", "Discard", "Cancel"), 2) == expected


def test_choose_escape_gives_the_cancel_answer(qtbot: QtBot) -> None:
    parent = QWidget()
    qtbot.addWidget(parent)

    def escape() -> None:
        box = QApplication.activeModalWidget()
        assert isinstance(box, QMessageBox)
        box.reject()

    QTimer.singleShot(0, escape)

    assert QtDialogService(ModalHost.create(parent, 10)).choose("Title", "Q?", ("A", "B", "C"), 1) == 1


def test_qt_clipboard_replaces_the_text(qtbot: QtBot) -> None:
    del qtbot

    QtClipboard().set_text("line 1\nline 2")

    assert QApplication.clipboard().text() == "line 1\nline 2"


@pytest.mark.parametrize("kind", ["inform", "warn", "error"])
def test_messages_close_with_their_catalog_button(qtbot: QtBot, kind: str) -> None:
    parent = QWidget()
    qtbot.addWidget(parent)
    service = QtDialogService(ModalHost.create(parent, 10))
    _click_in_next_message_box("Close!")

    getattr(service, kind)("Title", "Message", "Close!")


def test_status_bar_shows_the_save_tooltip_and_the_instance_warning(qtbot: QtBot) -> None:
    panel = StatusBarPanel()
    qtbot.addWidget(panel)
    button = ButtonSnapshot(
        text="ENG", tooltip="", enabled=True, visible=True, action=ActionIdEnum.SHELL_TOGGLE_LANGUAGE
    )
    warned = StatusBarSnapshot(
        save_state_text="Saved at 17:44:03",
        save_state_tooltip="Data file: D:/x.toml",
        instance_warning_text="Second launch not blocked",
        instance_warning_tooltip="Explanation",
        language_button=button,
    )

    panel.render_snapshot(warned)
    shown = (panel.save_state_tooltip, panel.instance_warning.text(), panel.instance_warning.isHidden())
    panel.render_snapshot(
        StatusBarSnapshot(
            save_state_text="Saved",
            save_state_tooltip="",
            instance_warning_text="",
            instance_warning_tooltip="",
            language_button=button,
        )
    )

    assert shown == ("Data file: D:/x.toml", "Second launch not blocked", False)
    assert panel.instance_warning.isHidden()
    assert panel.instance_warning.property("warning") is True
