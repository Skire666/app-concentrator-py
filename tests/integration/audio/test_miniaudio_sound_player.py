"""miniaudio sound player: real MP3 decoding of the shipped sounds, a fake output device (nothing is heard)."""

import array
import logging
from pathlib import Path
from typing import Final, override

import miniaudio
import pytest

from concentrator.application.ports.sound_player_port import LOOP_FOREVER, SoundPlayback
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.timer.volume import Volume
from concentrator.infrastructure.audio.miniaudio_sound_player import (
    CHANNELS,
    AudioDevice,
    Frames,
    MiniaudioSoundPlayer,
    decodes,
    has_audio_output,
    linear_volume,
    probe,
    sound_frames,
)
from concentrator.infrastructure.system.app_paths import AppPaths
from tests.fakes.immediate_dispatcher import ImmediateDispatcher

SHIPPED_SOUND: Final = next(AppPaths.from_runtime().sounds_dir.glob("*.mp3"))
PERIOD_FRAMES: Final = 4410
DEVICE_FAILURE: Final = "failed to init device"


class FakeDevice(AudioDevice):
    """Records what the player asks; ``drain`` plays the sound at once."""

    def __init__(self) -> None:
        self.volume = -1.0
        self.frames: Frames | None = None
        self.closed = False

    @override
    def start(self, frames: Frames) -> None:
        self.frames = frames

    @override
    def set_volume(self, volume: float) -> None:
        self.volume = volume

    @override
    def close(self) -> None:
        self.closed = True

    def drain(self) -> int:
        """Pull every chunk, as the audio thread would; return the number of frames played."""
        assert self.frames is not None
        return _pull(self.frames)


class RefusingDevice(FakeDevice):
    """Opens, then refuses to start."""

    @override
    def start(self, frames: Frames) -> None:
        raise miniaudio.MiniaudioError(DEVICE_FAILURE)


class Devices:
    def __init__(self, *, fail: bool = False) -> None:
        self.opened: list[FakeDevice] = []
        self._fail = fail

    def __call__(self) -> AudioDevice:
        if self._fail:
            raise miniaudio.MiniaudioError(DEVICE_FAILURE)
        device = FakeDevice()
        self.opened.append(device)
        return device


class Beeper:
    def __init__(self) -> None:
        self.count = 0

    def __call__(self) -> None:
        self.count += 1


def _pull(frames: Frames, limit: int | None = None) -> int:
    played = 0
    try:
        while limit is None or played < limit:
            chunk: array.array[int] = frames.send(PERIOD_FRAMES)
            played += len(chunk) // CHANNELS
    except StopIteration:
        pass
    return played


def _player(devices: Devices, beeper: Beeper, *, output: bool = True) -> MiniaudioSoundPlayer:
    return MiniaudioSoundPlayer(
        "test", dispatcher=ImmediateDispatcher(), beep=beeper, has_output=lambda: output, open_device=devices
    )


def _playback(*paths: Path | str, loops: int = 1) -> SoundPlayback:
    return SoundPlayback(paths=tuple(str(path) for path in paths), volume=Volume(50), loops=loops)


@pytest.fixture
def ended() -> list[int]:
    return []


@pytest.mark.parametrize(("percent", "factor"), [(0, 0.0), (50, 0.150515), (99, 1.0), (100, 1.0)])
def test_volume_follows_the_perceived_scale(percent: int, factor: float) -> None:
    assert linear_volume(Volume(percent)) == pytest.approx(factor, abs=1e-6)


def test_the_audio_outputs_can_be_listed() -> None:
    assert has_audio_output() in {True, False}


def test_probe_accepts_a_shipped_mp3_and_names_the_problem_otherwise(tmp_path: Path) -> None:
    damaged = tmp_path / "damaged.mp3"
    damaged.write_bytes(b"not an mp3")
    text = tmp_path / "notes.txt"
    text.write_text("hello", encoding="utf-8")

    assert probe(str(SHIPPED_SOUND)) is None
    assert probe(str(tmp_path / "missing.mp3")) is ErrorCodeEnum.AUDIO_FILE_NOT_FOUND
    assert probe(str(damaged)) is ErrorCodeEnum.AUDIO_FORMAT_UNSUPPORTED
    assert probe(str(text)) is ErrorCodeEnum.AUDIO_FORMAT_UNSUPPORTED


def test_decodes_reads_samples_of_a_shipped_mp3_only(tmp_path: Path) -> None:
    damaged = tmp_path / "damaged.mp3"
    damaged.write_bytes(b"not an mp3")

    assert decodes(SHIPPED_SOUND)
    assert not decodes(damaged)
    assert not decodes(tmp_path / "missing.mp3")


def test_frames_play_the_file_the_requested_number_of_times(ended: list[int]) -> None:
    once = sound_frames(str(SHIPPED_SOUND), 1, lambda: ended.append(1))
    twice = sound_frames(str(SHIPPED_SOUND), 2, lambda: ended.append(2))
    next(once)
    next(twice)

    single = _pull(once)

    assert single > 0
    assert _pull(twice) == 2 * single
    assert ended == [1, 2]


def test_frames_loop_until_closed(ended: list[int]) -> None:
    single = _pull(_primed(sound_frames(str(SHIPPED_SOUND), 1, lambda: None)))
    forever = _primed(sound_frames(str(SHIPPED_SOUND), LOOP_FOREVER, lambda: ended.append(0)))

    assert _pull(forever, limit=3 * single) >= 3 * single
    forever.close()
    assert ended == [0]


def test_a_file_gone_before_the_next_play_ends_the_sound(
    monkeypatch: pytest.MonkeyPatch, ended: list[int], caplog: pytest.LogCaptureFixture
) -> None:
    opened: list[str] = []
    real_stream = miniaudio.stream_file

    def stream_once(path: str, output_format: miniaudio.SampleFormat, nchannels: int, sample_rate: int) -> Frames:
        opened.append(path)
        if len(opened) > 1:
            raise FileNotFoundError(path)
        return real_stream(path, output_format, nchannels, sample_rate)

    monkeypatch.setattr(miniaudio, "stream_file", stream_once)
    frames = _primed(sound_frames(str(SHIPPED_SOUND), LOOP_FOREVER, lambda: ended.append(1)))

    with caplog.at_level(logging.WARNING):
        played = _pull(frames)

    assert played > 0
    assert len(opened) == 2
    assert ended == [1]
    assert "Sound stopped: it cannot be decoded any further (FileNotFoundError)" in caplog.text


def _primed(frames: Frames) -> Frames:
    next(frames)
    return frames


def test_play_opens_a_stream_at_the_converted_volume_and_stop_closes_it() -> None:
    devices = Devices()
    player = _player(devices, Beeper())

    assert player.play(_playback(SHIPPED_SOUND)).is_success

    device = devices.opened[0]
    assert device.volume == pytest.approx(linear_volume(Volume(50)))
    assert device.frames is not None
    assert player.playing
    player.stop()
    assert device.closed
    assert not player.playing


def test_a_sound_that_ends_closes_its_stream() -> None:
    devices = Devices()
    player = _player(devices, Beeper())
    player.play(_playback(SHIPPED_SOUND, loops=2))

    devices.opened[0].drain()

    assert devices.opened[0].closed
    assert not player.playing


def test_the_end_of_an_older_sound_leaves_the_new_one_playing() -> None:
    devices = Devices()
    player = _player(devices, Beeper())
    player.play(_playback(SHIPPED_SOUND))
    player.play(_playback(SHIPPED_SOUND))

    devices.opened[0].drain()

    assert player.playing
    assert not devices.opened[1].closed


def test_no_output_device_beeps_and_reports_it() -> None:
    devices = Devices()
    beeper = Beeper()

    result = _player(devices, beeper, output=False).play(_playback(SHIPPED_SOUND))

    assert result.error_codes == (ErrorCodeEnum.AUDIO_DEVICE_UNAVAILABLE,)
    assert beeper.count == 1
    assert devices.opened == []


def test_an_output_that_cannot_open_beeps_and_reports_it() -> None:
    beeper = Beeper()

    result = _player(Devices(fail=True), beeper).play(_playback(SHIPPED_SOUND))

    assert result.error_codes == (ErrorCodeEnum.AUDIO_DEVICE_UNAVAILABLE,)
    assert beeper.count == 1


def test_an_output_that_refuses_to_start_is_closed_and_beeps() -> None:
    device = RefusingDevice()
    beeper = Beeper()
    player = MiniaudioSoundPlayer(
        "test", dispatcher=ImmediateDispatcher(), beep=beeper, has_output=lambda: True, open_device=lambda: device
    )

    result = player.play(_playback(SHIPPED_SOUND))

    assert result.error_codes == (ErrorCodeEnum.AUDIO_PLAYBACK_FAILED,)
    assert device.closed
    assert beeper.count == 1
    assert not player.playing


def test_the_next_file_plays_when_the_first_cannot(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    devices = Devices()
    beeper = Beeper()

    with caplog.at_level(logging.WARNING):
        result = _player(devices, beeper).play(_playback(tmp_path / "missing.mp3", SHIPPED_SOUND))

    assert result.is_success
    assert len(devices.opened) == 1
    assert beeper.count == 0
    assert "test player: AUDIO_FILE_NOT_FOUND; trying the next sound" in caplog.text


@pytest.mark.parametrize("names", [(), ("missing.mp3",)])
def test_nothing_playable_beeps(tmp_path: Path, names: tuple[str, ...]) -> None:
    devices = Devices()
    beeper = Beeper()

    result = _player(devices, beeper).play(_playback(*(tmp_path / name for name in names)))

    assert result.is_success
    assert beeper.count == 1
    assert devices.opened == []


def test_check_names_the_problem_of_a_file(tmp_path: Path) -> None:
    player = _player(Devices(), Beeper())

    assert player.check(str(SHIPPED_SOUND)).is_success
    assert player.check(str(tmp_path / "missing.mp3")).error_codes == (ErrorCodeEnum.AUDIO_FILE_NOT_FOUND,)
    assert _player(Devices(), Beeper(), output=False).check(str(SHIPPED_SOUND)).error_codes == (
        ErrorCodeEnum.AUDIO_DEVICE_UNAVAILABLE,
    )
