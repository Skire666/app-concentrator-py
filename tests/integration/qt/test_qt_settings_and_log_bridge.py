import logging
from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import qCritical, qInfo, qWarning
from pytestqt.qtbot import QtBot

from concentrator.infrastructure.qt.qsettings_view_preferences import QSettingsViewPreferences
from concentrator.infrastructure.qt.qt_log_bridge import QT_LOGGER_NAME, QtLogBridge

pytestmark = pytest.mark.ui


@pytest.fixture
def bridge(qtbot: QtBot) -> Iterator[QtLogBridge]:
    del qtbot
    installed = QtLogBridge()
    installed.install()
    yield installed
    installed.uninstall()


def test_view_preferences_round_trip_through_a_new_file(qtbot: QtBot, tmp_path: Path) -> None:
    del qtbot
    ini_file = tmp_path / "nested" / "ui-state.ini"
    preferences = QSettingsViewPreferences(ini_file)

    preferences.set_text("layout/main_window/geometry", "AAEC/w==")
    preferences.set_text("storage/data_file_path", "C:/Users/me/concentrator.toml")
    assert preferences.sync()

    reopened = QSettingsViewPreferences(ini_file)
    assert reopened.get_text("layout/main_window/geometry") == "AAEC/w=="
    assert reopened.get_text("storage/data_file_path") == "C:/Users/me/concentrator.toml"
    assert reopened.get_text("layout/absent") is None


def test_view_preferences_remove_deletes_the_key(qtbot: QtBot, tmp_path: Path) -> None:
    del qtbot
    preferences = QSettingsViewPreferences(tmp_path / "ui-state.ini")
    preferences.set_text("layout/a", "1")

    preferences.remove("layout/a")
    preferences.remove("layout/never-written")

    assert preferences.get_text("layout/a") is None


def test_view_preferences_sync_reports_an_unwritable_file(qtbot: QtBot, tmp_path: Path) -> None:
    del qtbot
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    preferences = QSettingsViewPreferences(blocker / "ui-state.ini")
    preferences.set_text("layout/a", "1")

    assert not preferences.sync()


@pytest.mark.usefixtures("bridge")
def test_qt_messages_go_to_the_qt_logger(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG, logger=QT_LOGGER_NAME):
        qInfo("info from qt")
        qWarning("warning from qt")
        qCritical("critical from qt")

    records = [(record.name, record.levelno, record.getMessage()) for record in caplog.records]
    assert records == [
        (QT_LOGGER_NAME, logging.INFO, "info from qt"),
        (QT_LOGGER_NAME, logging.WARNING, "warning from qt"),
        (QT_LOGGER_NAME, logging.ERROR, "critical from qt"),
    ]


def test_uninstall_twice_is_harmless(qtbot: QtBot) -> None:
    del qtbot
    bridge = QtLogBridge()
    bridge.install()

    bridge.uninstall()
    bridge.uninstall()
