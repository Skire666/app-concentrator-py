"""Draft of the timer edit dialog, validated on every change (``AGENTS.md`` section 8.4)."""

from collections.abc import Callable

from concentrator.domain.common.severity_enum import SeverityEnum
from concentrator.domain.common.validation_issue import ValidationIssue
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.timer.duration import Duration
from concentrator.domain.timer.sound_ref import SoundRef
from concentrator.domain.timer.timer_config_rules import SOUND_FIELD, TimerConfigRules
from concentrator.domain.timer.timer_limits import TimerLimits
from concentrator.domain.timer.timer_settings import TimerSettings
from concentrator.domain.timer.volume import Volume
from concentrator.presentation.common.form_state import FormState


class TimerEditForm:
    """``FormState`` over ``TimerSettings``: domain rules plus a check that the sound can be played.

    The sound check reads the disk, so it runs only when the sound changes. A problem with the stored
    sound (a custom file deleted since) is a warning: the other settings can still be saved, and the
    alarm falls back to the default sound. A problem with a newly chosen sound blocks saving.
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
        self._check_sound = check_sound
        self._checked: dict[SoundRef, ValidationResult] = {}
        self._stored_sound = baseline.sound
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
        self._stored_sound = self._state.draft.sound
        self._state.commit()
        self._state.set_draft(self._state.draft)

    def _validate(self, settings: TimerSettings) -> ValidationResult:
        """Validate a draft.

        Args:
            settings: Draft.

        Returns:
            The rule issues, plus the sound check on ``sound``.
        """
        return TimerConfigRules.validate_settings(settings, self._limits).merge(self._sound_issues(settings.sound))

    def _sound_issues(self, sound: SoundRef) -> ValidationResult:
        """Check a sound once; issues of the stored sound are downgraded to warnings.

        Args:
            sound: Sound of the draft.

        Returns:
            The issues on ``sound``.
        """
        if not TimerConfigRules.validate_sound(sound).is_success:
            return ValidationResult.success()
        if sound not in self._checked:
            self._checked[sound] = self._check_sound(sound)
        severity = SeverityEnum.WARNING if sound == self._stored_sound else SeverityEnum.ERROR
        issues = (
            ValidationIssue(code=issue.code, severity=severity, field=SOUND_FIELD, params=issue.params)
            for issue in self._checked[sound].issues
        )
        return ValidationResult.of(*issues)
