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
            Success, or ``AUDIO_DEVICE_UNAVAILABLE`` (the beep sounds instead). Failures found while
            playing (``AUDIO_FORMAT_UNSUPPORTED``, ``AUDIO_PLAYBACK_FAILED``) are logged and move on to
            the next file.
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
