"""The editable values of the timer configuration."""

from dataclasses import dataclass

from concentrator.domain.timer.duration import Duration
from concentrator.domain.timer.sound_ref import SoundRef
from concentrator.domain.timer.volume import Volume


@dataclass(frozen=True, slots=True, kw_only=True)
class TimerSettings:
    """Duration and alarm of the timer, as edited in the timer dialog; checked by ``TimerConfigRules``.

    Attributes:
        duration: Countdown duration.
        sound: Alarm sound.
        volume: Alarm volume.
        loop_count: Number of times the sound plays (ignored when ``loop_forever``).
        loop_forever: Repeat the sound until the alarm stops.
        auto_stop_seconds: Stop ringing after this many seconds, ``0`` for never.
        auto_restart: Start the countdown again after an automatic stop.
    """

    duration: Duration
    sound: SoundRef
    volume: Volume
    loop_count: int
    loop_forever: bool
    auto_stop_seconds: int
    auto_restart: bool
