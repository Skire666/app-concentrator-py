"""Qt sound player and attention adapters on the offscreen platform (no sound is heard in tests)."""

from pathlib import Path
from typing import override

import pytest
from PySide6.QtCore import QObject, Qt, QUrl
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import QSystemTrayIcon, QWidget
from pytestqt.qtbot import QtBot

from concentrator.application.ports.sound_player_port import LOOP_FOREVER, SoundPlayback
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.timer.volume import Volume
from concentrator.infrastructure.qt.qt_attention import QtAttention, messages_supported
from concentrator.infrastructure.qt.qt_sound_player import (
    QtSoundPlayer,
    decodable_mime_types,
    error_code_for,
    has_audio_output,
    linear_volume,
)
from concentrator.infrastructure.system.app_paths import AppPaths

SHIPPED_SOUND = next(AppPaths.from_runtime().sounds_dir.glob("*.mp3"))


class Beeper:
    def __init__(self) -> None:
        self.count = 0

    def __call__(self) -> None:
        self.count += 1


@pytest.fixture
def owner(qtbot: QtBot) -> QObject:
    del qtbot  # ensures the QApplication exists
    return QObject()


def _player(owner: QObject, beeper: Beeper, *, output: bool = True) -> QtSoundPlayer:
    return QtSoundPlayer("test", owner, has_output=lambda: output, beep=beeper)


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (QMediaPlayer.Error.ResourceError, ErrorCodeEnum.AUDIO_FILE_NOT_FOUND),
        (QMediaPlayer.Error.FormatError, ErrorCodeEnum.AUDIO_FORMAT_UNSUPPORTED),
        (QMediaPlayer.Error.NetworkError, ErrorCodeEnum.AUDIO_PLAYBACK_FAILED),
        (QMediaPlayer.Error.AccessDeniedError, ErrorCodeEnum.AUDIO_PLAYBACK_FAILED),
    ],
)
def test_player_errors_map_to_audio_codes(error: QMediaPlayer.Error, code: ErrorCodeEnum) -> None:
    assert error_code_for(error) is code


def test_volume_is_converted_from_the_perceived_scale(owner: QObject) -> None:
    del owner
    assert linear_volume(Volume(0)) == pytest.approx(0.0, abs=1e-9)
    assert linear_volume(Volume(100)) == pytest.approx(1.0)
    assert 0.0 < linear_volume(Volume(50)) < 0.5


def test_backend_decodes_mp3_and_an_output_check_runs(owner: QObject) -> None:
    del owner
    assert "audio/mpeg" in decodable_mime_types()
    assert isinstance(has_audio_output(), bool)


def test_play_sets_the_first_file_loops_and_volume(owner: QObject) -> None:
    beeper = Beeper()
    player = _player(owner, beeper)

    result = player.play(SoundPlayback(paths=(SHIPPED_SOUND.as_posix(),), volume=Volume(100), loops=3))
    player.stop()

    assert result.is_success
    assert player.media_player.source() == QUrl.fromLocalFile(SHIPPED_SOUND.as_posix())
    assert player.media_player.loops() == 3
    assert player.audio_output.volume() == pytest.approx(1.0)
    assert beeper.count == 0


def test_play_forever_uses_the_infinite_loop(owner: QObject) -> None:
    player = _player(owner, Beeper())

    player.play(SoundPlayback(paths=(SHIPPED_SOUND.as_posix(),), volume=Volume(10), loops=LOOP_FOREVER))
    player.stop()

    assert player.media_player.loops() == QMediaPlayer.Loops.Infinite


def test_no_output_device_beeps_and_reports_it(owner: QObject) -> None:
    beeper = Beeper()

    result = _player(owner, beeper, output=False).play(SoundPlayback(paths=("a.mp3",), volume=Volume(10), loops=1))

    assert result.error_codes == (ErrorCodeEnum.AUDIO_DEVICE_UNAVAILABLE,)
    assert beeper.count == 1


def test_empty_playback_beeps(owner: QObject) -> None:
    beeper = Beeper()

    _player(owner, beeper).play(SoundPlayback(paths=(), volume=Volume(10), loops=1))

    assert beeper.count == 1


def test_a_playback_error_moves_to_the_next_file_then_to_the_beep(
    owner: QObject, caplog: pytest.LogCaptureFixture
) -> None:
    beeper = Beeper()
    player = _player(owner, beeper)
    player.play(SoundPlayback(paths=("C:/first.mp3", SHIPPED_SOUND.as_posix()), volume=Volume(0), loops=1))

    errors = player.media_player.errorOccurred
    errors.emit(QMediaPlayer.Error.FormatError, "bad header")
    assert player.media_player.source() == QUrl.fromLocalFile(SHIPPED_SOUND.as_posix())
    errors.emit(QMediaPlayer.Error.ResourceError, "gone")
    errors.emit(QMediaPlayer.Error.NoError, "")
    player.stop()

    assert beeper.count == 1
    assert "AUDIO_FORMAT_UNSUPPORTED (bad header); trying the next sound" in caplog.text


def test_a_missing_file_fails_asynchronously_and_ends_with_the_beep(qtbot: QtBot, owner: QObject) -> None:
    beeper = Beeper()
    player = _player(owner, beeper)

    player.play(SoundPlayback(paths=("Z:/no/such/alarm.mp3",), volume=Volume(0), loops=1))

    qtbot.waitUntil(lambda: beeper.count == 1, timeout=5000)


def test_check_accepts_mp3_and_refuses_other_files(owner: QObject, tmp_path: Path) -> None:
    text_file = tmp_path / "notes.txt"
    text_file.write_text("x", encoding="utf-8")
    player = _player(owner, Beeper())

    assert player.check(SHIPPED_SOUND.as_posix()).is_success
    assert player.check(text_file.as_posix()).error_codes == (ErrorCodeEnum.AUDIO_FORMAT_UNSUPPORTED,)
    assert _player(owner, Beeper(), output=False).check(SHIPPED_SOUND.as_posix()).error_codes == (
        ErrorCodeEnum.AUDIO_DEVICE_UNAVAILABLE,
    )


class RecordingTray(QSystemTrayIcon):
    def __init__(self, *, visible: bool) -> None:
        super().__init__()
        self.visible = visible
        self.messages: list[tuple[str, str, int]] = []

    @override
    def isVisible(self) -> bool:
        return self.visible

    @override
    def showMessage(self, title: str, msg: str, icon: object = None, msecs: int = 10000) -> None:
        self.messages.append((title, msg, msecs))


def test_attention_shows_the_message_with_the_configured_duration(qtbot: QtBot) -> None:
    window = QWidget()
    qtbot.addWidget(window)
    tray = RecordingTray(visible=True)
    attention = QtAttention(tray, window, 8000, supported=lambda: True)

    assert attention.notify("Time is up", "Done").is_success
    attention.request_attention()

    assert tray.messages == [("Time is up", "Done", 8000)]


@pytest.mark.parametrize(("supported", "visible"), [(False, True), (True, False)])
def test_attention_reports_unavailable_notifications(qtbot: QtBot, supported: bool, visible: bool) -> None:
    window = QWidget()
    qtbot.addWidget(window)
    tray = RecordingTray(visible=visible)

    result = QtAttention(tray, window, 8000, supported=lambda: supported).notify("t", "m")

    assert result.error_codes == (ErrorCodeEnum.NOTIFICATION_UNAVAILABLE,)
    assert tray.messages == []
    assert isinstance(messages_supported(), bool)


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

    attention = QtAttention(RecordingTray(visible=True), window, 8000, application_state=lambda: state)

    assert attention.is_application_active() is active
