"""Plays alarm, preview and chime sounds."""

from dataclasses import dataclass
from typing import Final, Protocol

from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.timer.volume import Volume

LOOP_FOREVER: Final = -1


@dataclass(frozen=True, slots=True, kw_only=True)
class SoundPlayback:
    """What to play.

    Attributes:
        paths: Audio files tried in order: when one cannot be played, the next one is; when none can,
            the system beep sounds. Empty means the beep alone.
        volume: Perceived volume.
        loops: Number of plays, or ``LOOP_FOREVER`` until ``stop``.
    """

    paths: tuple[str, ...]
    volume: Volume
    loops: int


class SoundPlayerPort(Protocol):
    """One player instance (alarm, preview, chime): starting a sound stops the one it was playing."""

    def play(self, playback: SoundPlayback) -> ValidationResult:
        """Start playing.

        Args:
            playback: Files, volume and play count.

        Returns:
            Success, ``AUDIO_DEVICE_UNAVAILABLE`` or ``AUDIO_PLAYBACK_FAILED`` (the beep sounds instead).
            A file that cannot be played (``AUDIO_FILE_NOT_FOUND``, ``AUDIO_FORMAT_UNSUPPORTED``) is logged
            and the next file is tried.
        """
        ...

    def stop(self) -> None:
        """Stop the sound being played (nothing happens when silent)."""
        ...

    def check(self, path: str) -> ValidationResult:
        """Tell whether a file can be played on this computer.

        Args:
            path: Existing audio file.

        Returns:
            Success, ``AUDIO_FORMAT_UNSUPPORTED`` or ``AUDIO_DEVICE_UNAVAILABLE``.
        """
        ...
