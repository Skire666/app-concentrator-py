"""``SoundPlayerPort`` on ``QMediaPlayer`` + ``QAudioOutput`` (QtMultimedia, FFmpeg backend, ADR-004)."""

import logging
from collections.abc import Callable
from types import MappingProxyType
from typing import Final, override

from PySide6.QtCore import QMimeDatabase, QObject, QUrl
from PySide6.QtMultimedia import QAudio, QAudioOutput, QMediaDevices, QMediaFormat, QMediaPlayer
from PySide6.QtWidgets import QApplication

from concentrator.application.ports.sound_player_port import LOOP_FOREVER, SoundPlayback, SoundPlayerPort
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.timer.volume import MAX_VOLUME_PERCENT, Volume

_logger = logging.getLogger(__name__)

PLAYER_ERROR_CODES: Final = MappingProxyType(
    {
        QMediaPlayer.Error.ResourceError: ErrorCodeEnum.AUDIO_FILE_NOT_FOUND,
        QMediaPlayer.Error.FormatError: ErrorCodeEnum.AUDIO_FORMAT_UNSUPPORTED,
    }
)
MP3_MIME_TYPE: Final = "audio/mpeg"


def error_code_for(error: QMediaPlayer.Error) -> ErrorCodeEnum:
    """Convert a ``QMediaPlayer`` error.

    Args:
        error: Error reported by ``errorOccurred``.

    Returns:
        ``AUDIO_FILE_NOT_FOUND``, ``AUDIO_FORMAT_UNSUPPORTED`` or ``AUDIO_PLAYBACK_FAILED``.
    """
    return PLAYER_ERROR_CODES.get(error, ErrorCodeEnum.AUDIO_PLAYBACK_FAILED)


def linear_volume(volume: Volume) -> float:
    """Convert a perceived volume (percent) to the linear scale of ``QAudioOutput``.

    Args:
        volume: Volume in percent.

    Returns:
        A factor between 0 and 1.
    """
    return QAudio.convertVolume(
        volume.percent / MAX_VOLUME_PERCENT,
        QAudio.VolumeScale.LogarithmicVolumeScale,
        QAudio.VolumeScale.LinearVolumeScale,
    )


def decodable_mime_types() -> frozenset[str]:
    """Return the MIME types the multimedia backend can decode.

    Returns:
        For example ``audio/mpeg``; empty when the FFmpeg plugin is missing (frozen build).
    """
    formats = QMediaFormat().supportedFileFormats(QMediaFormat.ConversionMode.Decode)
    return frozenset(QMediaFormat(file_format).mimeType().name() for file_format in formats)


def has_audio_output() -> bool:
    """Tell whether the computer has an audio output device.

    Returns:
        Whether at least one output exists.
    """
    return bool(QMediaDevices.audioOutputs())


class QtSoundPlayer(SoundPlayerPort):
    """One named player (``alarm``, ``preview``, ``chime``). Files are streamed, so size does not matter.

    When a file cannot be played, the error is logged and the next file of the playback is tried; when
    none is left, ``QApplication.beep()`` sounds.
    """

    def __init__(
        self,
        name: str,
        parent: QObject,
        *,
        has_output: Callable[[], bool] = has_audio_output,
        beep: Callable[[], None] = QApplication.beep,
    ) -> None:
        """Create the player.

        Args:
            name: Name used in the log.
            parent: Owner of the Qt objects.
            has_output: Tells whether an audio output device exists.
            beep: Last resort when no file can be played.
        """
        self._name = name
        self._has_output = has_output
        self._beep = beep
        self._player = QMediaPlayer(parent)
        self._output = QAudioOutput(parent)
        self._player.setAudioOutput(self._output)
        self._player.errorOccurred.connect(self._on_error)
        self._pending: list[str] = []
        self._loops = 1

    @property
    def media_player(self) -> QMediaPlayer:
        """The Qt player (for tests)."""
        return self._player

    @property
    def audio_output(self) -> QAudioOutput:
        """The Qt audio output (for tests)."""
        return self._output

    @override
    def play(self, playback: SoundPlayback) -> ValidationResult:
        self.stop()
        if not self._has_output():
            _logger.warning("%s player: no audio output device; beeping", self._name)
            self._beep()
            return ValidationResult.failure(ErrorCodeEnum.AUDIO_DEVICE_UNAVAILABLE)
        self._output.setDevice(QMediaDevices.defaultAudioOutput())
        self._output.setVolume(linear_volume(playback.volume))
        self._loops = QMediaPlayer.Loops.Infinite if playback.loops == LOOP_FOREVER else playback.loops
        self._pending = list(playback.paths)
        self._play_next()
        return ValidationResult.success()

    @override
    def stop(self) -> None:
        self._pending = []
        self._player.stop()

    @override
    def check(self, path: str) -> ValidationResult:
        if not self._has_output():
            return ValidationResult.failure(ErrorCodeEnum.AUDIO_DEVICE_UNAVAILABLE)
        mime_type = QMimeDatabase().mimeTypeForFile(path).name()
        if mime_type not in decodable_mime_types():
            _logger.info("Sound file type %s cannot be decoded", mime_type)
            return ValidationResult.failure(ErrorCodeEnum.AUDIO_FORMAT_UNSUPPORTED)
        return ValidationResult.success()

    def _play_next(self) -> None:
        """Play the next file of the playback, or beep when none is left."""
        if not self._pending:
            _logger.warning("%s player: no playable sound file; beeping", self._name)
            self._beep()
            return
        path = self._pending.pop(0)
        self._player.setSource(QUrl.fromLocalFile(path))
        self._player.setLoops(self._loops)
        self._player.play()

    def _on_error(self, error: QMediaPlayer.Error, message: str) -> None:
        """Log a playback error and move on to the next file.

        Args:
            error: Qt error.
            message: Qt description.
        """
        if error is QMediaPlayer.Error.NoError:
            return
        _logger.warning("%s player: %s (%s); trying the next sound", self._name, error_code_for(error).name, message)
        self._play_next()
