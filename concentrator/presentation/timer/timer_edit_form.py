"""Draft of the timer edit dialog, validated on every change (``AGENTS.md`` section 8.4)."""

from collections.abc import Callable

from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.timer.duration import Duration
from concentrator.domain.timer.sound_ref import SoundRef
from concentrator.domain.timer.timer_config_rules import TimerConfigRules
from concentrator.domain.timer.timer_limits import TimerLimits
from concentrator.domain.timer.timer_settings import TimerSettings
from concentrator.domain.timer.volume import Volume
from concentrator.presentation.common.form_state import FormState
from concentrator.presentation.timer.sound_check import SoundCheck


class TimerEditForm:
    """``FormState`` over ``TimerSettings``: domain rules plus a check that the sound can be played.

    The sound check (``SoundCheck``) runs once per sound; a problem with the stored sound is a warning.
    """

    def __init__(
        self, baseline: TimerSettings, limits: TimerLimits, check_sound: Callable[[SoundRef], ValidationResult]
    ) -> None:
        """Start editing.

        Args:
            baseline: Stored settings.
            limits: Bounds from ``concentrator.ini``.
            check_sound: Tells whether a sound exists and can be played.
        """
        self._limits = limits
        self._sound_check = SoundCheck(baseline.sound, check_sound)
        self._state = FormState(baseline, self._validate)

    @property
    def draft(self) -> TimerSettings:
        """Values being edited."""
        return self._state.draft

    @property
    def baseline(self) -> TimerSettings:
        """Values the draft is compared with."""
        return self._state.baseline

    @property
    def errors(self) -> ValidationResult:
        """Validation of the draft."""
        return self._state.errors

    @property
    def is_dirty(self) -> bool:
        """Whether the draft differs from the stored settings."""
        return self._state.is_dirty

    @property
    def can_submit(self) -> bool:
        """Whether the draft changed and has no failing issue."""
        return self._state.can_submit

    def set_duration(self, hours: int, minutes: int, seconds: int) -> None:
        """Change the duration.

        Args:
            hours: Hours.
            minutes: Minutes.
            seconds: Seconds.
        """
        self._state.set_field("duration", Duration.from_hms(hours, minutes, seconds))

    def set_sound(self, sound: SoundRef) -> None:
        """Change the sound.

        Args:
            sound: Built-in sound or file.
        """
        self._state.set_field("sound", sound)

    def set_volume(self, percent: int) -> None:
        """Change the volume.

        Args:
            percent: Volume in percent.
        """
        self._state.set_field("volume", Volume(percent))

    def set_loop_count(self, count: int) -> None:
        """Change the play count.

        Args:
            count: Number of plays.
        """
        self._state.set_field("loop_count", count)

    def set_loop_forever(self, forever: bool) -> None:
        """Repeat the sound until the alarm stops, or not.

        Args:
            forever: Whether to repeat.
        """
        self._state.set_field("loop_forever", forever)

    def set_auto_stop(self, seconds: int) -> None:
        """Change the automatic stop.

        Args:
            seconds: Delay, ``0`` for never.
        """
        self._state.set_field("auto_stop_seconds", seconds)

    def set_auto_restart(self, restart: bool) -> None:
        """Restart after the automatic stop, or not.

        Args:
            restart: Whether to restart.
        """
        self._state.set_field("auto_restart", restart)

    def commit(self) -> None:
        """Make the draft the stored settings (after a successful save)."""
        self._sound_check.commit(self._state.draft.sound)
        self._state.commit()
        self._state.set_draft(self._state.draft)

    def _validate(self, settings: TimerSettings) -> ValidationResult:
        """Validate a draft.

        Args:
            settings: Draft.

        Returns:
            The rule issues, plus the sound check on ``sound``.
        """
        return TimerConfigRules.validate_settings(settings, self._limits).merge(
            self._sound_check.issues(settings.sound)
        )
