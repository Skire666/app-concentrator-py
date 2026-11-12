"""``SoundPlayerPort`` on miniaudio (ADR-045): MP3 files decoded and played by one small native library.

The file is streamed (its size does not matter) and looped by a generator that miniaudio calls from its own
audio thread; the generator never raises (a decoding error ends the sound and is logged). When a sound ends
by itself, its device is closed on the main thread.
"""

import array
import logging
import math
from collections.abc import Callable, Generator
from functools import partial
from pathlib import Path
from typing import Final, Protocol, override

import miniaudio

from concentrator.application.ports.main_thread_dispatcher_port import MainThreadDispatcherPort
from concentrator.application.ports.sound_player_port import LOOP_FOREVER, SoundPlayback, SoundPlayerPort
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.timer.volume import MAX_VOLUME_PERCENT, Volume

_logger = logging.getLogger(__name__)

SAMPLE_RATE: Final = 44_100
CHANNELS: Final = 2
SAMPLE_FORMAT: Final = miniaudio.SampleFormat.SIGNED16
SAMPLE_TYPECODE: Final = "h"
APP_NAME: Final = "Concentrator"
LOG_100: Final = math.log(100)
FULL_VOLUME: Final = 0.99
"""Above this perceived volume, the linear factor is 1 (same curve as Qt's logarithmic volume scale)."""

type Frames = Generator[array.array[int], int]
"""Audio chunks; miniaudio sends the number of frames it wants and plays the chunk yielded back."""


class AudioDevice(Protocol):
    """One open output stream."""

    def start(self, frames: Frames) -> None:
        """Start pulling chunks from a started generator.

        Args:
            frames: The sound.
        """
        ...

    def set_volume(self, volume: float) -> None:
        """Set the linear volume.

        Args:
            volume: Factor between 0 and 1.
        """
        ...

    def close(self) -> None:
        """Stop and release the stream."""
        ...


class MiniaudioDevice(AudioDevice):
    """The default playback device of the computer, 16-bit stereo at 44.1 kHz."""

    def __init__(self, buffer_ms: int) -> None:
        """Open the device (``miniaudio.MiniaudioError`` when no output can be opened).

        Args:
            buffer_ms: Period of the audio buffer (``timer.audio_buffer_ms``); closing waits about 2.5 periods.
        """
        self._device = miniaudio.PlaybackDevice(
            output_format=SAMPLE_FORMAT,
            nchannels=CHANNELS,
            sample_rate=SAMPLE_RATE,
            buffersize_msec=buffer_ms,
            app_name=APP_NAME,
        )

    @override
    def start(self, frames: Frames) -> None:
        self._device.start(frames)

    @override
    def set_volume(self, volume: float) -> None:
        self._device.set_master_volume(volume)

    @override
    def close(self) -> None:
        self._device.close()


def linear_volume(volume: Volume) -> float:
    """Convert a perceived volume (percent) to a linear factor, as Qt's logarithmic volume scale did.

    Args:
        volume: Volume in percent.

    Returns:
        A factor between 0 and 1.
    """
    perceived = volume.percent / MAX_VOLUME_PERCENT
    if perceived > FULL_VOLUME:
        return 1.0
    return -math.log(1 - perceived) / LOG_100


def has_audio_output() -> bool:
    """Tell whether the computer has an audio output device.

    Returns:
        Whether at least one output exists (``False`` when the audio system cannot be queried).
    """
    try:
        return bool(miniaudio.Devices().get_playbacks())
    except miniaudio.MiniaudioError as error:
        _logger.warning("Audio devices cannot be listed: %s", error)
        return False


def probe(path: str) -> ErrorCodeEnum | None:
    """Tell why a file cannot be played, without opening a device.

    Args:
        path: Sound file.

    Returns:
        ``AUDIO_FILE_NOT_FOUND``, ``AUDIO_FORMAT_UNSUPPORTED`` or ``None`` when it can be decoded.
    """
    if not Path(path).is_file():
        return ErrorCodeEnum.AUDIO_FILE_NOT_FOUND
    try:
        miniaudio.get_file_info(path)
    except miniaudio.DecodeError:
        return ErrorCodeEnum.AUDIO_FORMAT_UNSUPPORTED
    return None


def decodes(path: Path) -> bool:
    """Decode the first samples of a file (self-check of the frozen build).

    Args:
        path: Sound file.

    Returns:
        Whether samples came out.
    """
    try:
        stream = miniaudio.stream_file(str(path), SAMPLE_FORMAT, CHANNELS, SAMPLE_RATE)
        chunk = next(stream)
    except miniaudio.MiniaudioError, OSError, StopIteration:  # a missing file raises FileNotFoundError
        return False
    stream.close()
    return len(chunk) > 0


def sound_frames(path: str, loops: int, on_end: Callable[[], None]) -> Frames:
    """Stream a file ``loops`` times (or until closed), then call ``on_end`` (from the audio thread).

    Prime it with ``next()`` before giving it to a device.

    Args:
        path: Decodable sound file.
        loops: Number of plays, or ``LOOP_FOREVER``.
        on_end: Called once when the sound ends, by itself, on a decoding error or when closed.

    Yields:
        Chunks of 16-bit stereo samples.
    """
    wanted = yield array.array(SAMPLE_TYPECODE)
    played = 0
    try:
        while loops == LOOP_FOREVER or played < loops:
            stream = miniaudio.stream_file(path, SAMPLE_FORMAT, CHANNELS, SAMPLE_RATE)
            for chunk in _chunks(stream, wanted):
                wanted = yield chunk
            played += 1
    except (miniaudio.MiniaudioError, OSError) as error:  # the file may disappear between two plays
        _logger.warning("Sound stopped: it cannot be decoded any further (%s)", type(error).__name__)
    finally:
        on_end()


def _chunks(stream: Frames, wanted: int) -> Generator[array.array[int]]:
    """Read one play of a stream, asking each time for the number of frames the device wants.

    The device asks for a constant period, so the first request is used for the whole play.

    Args:
        stream: Started miniaudio stream.
        wanted: Frames per chunk.

    Yields:
        Chunks until the end of the file.
    """
    while True:
        try:
            chunk = stream.send(wanted)
        except StopIteration:
            return
        yield chunk


class MiniaudioSoundPlayer(SoundPlayerPort):
    """One named player (``alarm``, ``preview``, ``chime``) with its own output stream while it plays.

    A file that cannot be played is logged and the next file of the playback is tried; when none is left,
    the beep sounds.
    """

    def __init__(
        self,
        name: str,
        *,
        dispatcher: MainThreadDispatcherPort,
        beep: Callable[[], None],
        open_device: Callable[[], AudioDevice],
        has_output: Callable[[], bool] = has_audio_output,
    ) -> None:
        """Create the player.

        Args:
            name: Name used in the log.
            dispatcher: Brings the end of a sound back to the main thread.
            beep: Last resort when no file can be played.
            open_device: Opens an output stream (``partial(MiniaudioDevice, buffer_ms)`` in the application).
            has_output: Tells whether an audio output device exists.
        """
        self._name = name
        self._dispatcher = dispatcher
        self._beep = beep
        self._has_output = has_output
        self._open_device = open_device
        self._device: AudioDevice | None = None
        self._generation = 0

    @property
    def playing(self) -> bool:
        """Whether an output stream is open (for tests)."""
        return self._device is not None

    @override
    def play(self, playback: SoundPlayback) -> ValidationResult:
        self.stop()
        if not self._has_output():
            _logger.warning("%s player: no audio output device; beeping", self._name)
            self._beep()
            return ValidationResult.failure(ErrorCodeEnum.AUDIO_DEVICE_UNAVAILABLE)
        path = self._first_playable(playback.paths)
        if path is None:
            _logger.warning("%s player: no playable sound file; beeping", self._name)
            self._beep()
            return ValidationResult.success()
        return self._start(path, playback)

    @override
    def stop(self) -> None:
        self._generation += 1
        if self._device is not None:
            self._device.close()
            self._device = None

    @override
    def check(self, path: str) -> ValidationResult:
        if not self._has_output():
            return ValidationResult.failure(ErrorCodeEnum.AUDIO_DEVICE_UNAVAILABLE)
        code = probe(path)
        if code is not None:
            _logger.info("Sound file cannot be played: %s", code.name)
            return ValidationResult.failure(code)
        return ValidationResult.success()

    def _first_playable(self, paths: tuple[str, ...]) -> str | None:
        """Find the first file of a playback that can be decoded.

        Args:
            paths: Candidate files, in order.

        Returns:
            Its path, ``None`` when none can be played (each refusal is logged).
        """
        for path in paths:
            code = probe(path)
            if code is None:
                return path
            _logger.warning("%s player: %s; trying the next sound", self._name, code.name)
        return None

    def _start(self, path: str, playback: SoundPlayback) -> ValidationResult:
        """Open a stream and start a decodable file.

        Args:
            path: Decodable file.
            playback: Volume and play count.

        Returns:
            Success, ``AUDIO_DEVICE_UNAVAILABLE`` when no stream opens, or ``AUDIO_PLAYBACK_FAILED`` when it
            opens but refuses to start (the beep sounds instead in both cases).
        """
        generation = self._generation
        frames = sound_frames(
            path, playback.loops, partial(self._dispatcher.dispatch, partial(self._ended, generation))
        )
        next(frames)
        try:
            device = self._open_device()
        except miniaudio.MiniaudioError as error:
            _logger.warning("%s player: the audio output cannot be opened (%s); beeping", self._name, error)
            frames.close()
            self._beep()
            return ValidationResult.failure(ErrorCodeEnum.AUDIO_DEVICE_UNAVAILABLE)
        try:
            device.set_volume(linear_volume(playback.volume))
            device.start(frames)
        except miniaudio.MiniaudioError as error:
            _logger.warning("%s player: the audio output refused to start (%s); beeping", self._name, error)
            device.close()
            frames.close()
            self._beep()
            return ValidationResult.failure(ErrorCodeEnum.AUDIO_PLAYBACK_FAILED)
        self._device = device
        return ValidationResult.success()

    def _ended(self, generation: int) -> None:
        """Main thread: release the stream of a sound that ended by itself.

        Args:
            generation: Play the ending sound belonged to; a later play or stop wins.
        """
        if generation == self._generation and self._device is not None:
            self._device.close()
            self._device = None
