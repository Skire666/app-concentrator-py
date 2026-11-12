"""Qt attention adapter on the offscreen platform."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget
from pytestqt.qtbot import QtBot

from concentrator.infrastructure.qt.qt_attention import QtAttention


def test_attention_flashes_the_taskbar_button(qtbot: QtBot) -> None:
    window = QWidget()
    qtbot.addWidget(window)

    QtAttention(window).request_attention()


@pytest.mark.parametrize(
    ("state", "active"),
    [
        (Qt.ApplicationState.ApplicationActive, True),
        (Qt.ApplicationState.ApplicationInactive, False),
        (Qt.ApplicationState.ApplicationHidden, False),
    ],
)
def test_application_is_active_only_in_the_active_state(qtbot: QtBot, state: Qt.ApplicationState, active: bool) -> None:
    window = QWidget()
    qtbot.addWidget(window)

    attention = QtAttention(window, application_state=lambda: state)

    assert attention.is_application_active() is active
