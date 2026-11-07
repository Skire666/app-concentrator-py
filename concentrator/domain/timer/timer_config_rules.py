"""Business rules of the timer configuration."""

from typing import Final

from concentrator.domain.common.entity_rules import EntityRules
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.timer.duration import Duration
from concentrator.domain.timer.sound_kind_enum import SoundKindEnum
from concentrator.domain.timer.sound_ref import SoundRef
from concentrator.domain.timer.timer_config import TimerConfig
from concentrator.domain.timer.timer_limits import TimerLimits
from concentrator.domain.timer.timer_settings import TimerSettings
from concentrator.domain.timer.volume import MAX_VOLUME_PERCENT, MIN_VOLUME_PERCENT, Volume

DURATION_FIELD: Final = "duration_seconds"
SOUND_FIELD: Final = "sound"
SOUND_KIND_FIELD: Final = "sound.kind"
VOLUME_FIELD: Final = "volume"
LOOP_COUNT_FIELD: Final = "loop_count"
AUTO_STOP_FIELD: Final = "auto_stop_seconds"
MIN_LOOP_COUNT: Final = 1
NEVER_AUTO_STOP: Final = 0


class TimerConfigRules:
    """Stateless validation of the timer configuration. Field paths are those of the ``[timer]`` section."""

    @staticmethod
    def validate(config: TimerConfig, limits: TimerLimits) -> ValidationResult:
        """Check the identity and every setting.

        Args:
            config: Configuration to check.
            limits: Bounds from ``concentrator.ini``.

        Returns:
            The merged result.
        """
        return EntityRules.validate_identity(config).merge(TimerConfigRules.validate_settings(config.settings, limits))

    @staticmethod
    def validate_settings(settings: TimerSettings, limits: TimerLimits) -> ValidationResult:
        """Check every editable value (the edit dialog validates its draft with this method).

        Args:
            settings: Values to check.
            limits: Bounds from ``concentrator.ini``.

        Returns:
            The merged result, one issue per failing field.
        """
        return TimerConfigRules.validate_duration(settings.duration, limits).merge(
            TimerConfigRules.validate_sound(settings.sound),
            TimerConfigRules.validate_volume(settings.volume),
            TimerConfigRules.validate_loop_count(settings.loop_count, limits),
            TimerConfigRules.validate_auto_stop(settings.auto_stop_seconds, limits),
        )

    @staticmethod
    def validate_duration(duration: Duration, limits: TimerLimits) -> ValidationResult:
        """Check the countdown duration.

        Args:
            duration: Duration to check.
            limits: Bounds.

        Returns:
            Success, ``TIMER_DURATION_TOO_SHORT`` (``min``) or ``TIMER_DURATION_TOO_LONG`` (``max``), as
            ``HH:MM:SS`` texts.
        """
        if duration.seconds < limits.min_duration_seconds:
            minimum = Duration(limits.min_duration_seconds).as_clock_text()
            return ValidationResult.failure(ErrorCodeEnum.TIMER_DURATION_TOO_SHORT, field=DURATION_FIELD, min=minimum)
        if duration.seconds > limits.max_duration_seconds:
            maximum = Duration(limits.max_duration_seconds).as_clock_text()
            return ValidationResult.failure(ErrorCodeEnum.TIMER_DURATION_TOO_LONG, field=DURATION_FIELD, max=maximum)
        return ValidationResult.success()

    @staticmethod
    def validate_sound(sound: SoundRef) -> ValidationResult:
        """Check that a sound is chosen.

        Args:
            sound: Sound to check.

        Returns:
            Success, ``ENUM_VALUE_UNKNOWN`` on ``sound.kind`` for a kind written by a newer version, or
            ``TIMER_SOUND_UNSET`` when no kind or no value is set.
        """
        if sound.kind is SoundKindEnum.UNKNOWN:
            return ValidationResult.failure(ErrorCodeEnum.ENUM_VALUE_UNKNOWN, field=SOUND_KIND_FIELD)
        if sound.kind is SoundKindEnum.UNSET or not sound.value.strip():
            return ValidationResult.failure(ErrorCodeEnum.TIMER_SOUND_UNSET, field=SOUND_FIELD)
        return ValidationResult.success()

    @staticmethod
    def validate_volume(volume: Volume, field: str = VOLUME_FIELD) -> ValidationResult:
        """Check a volume (alarm, and the hourly chime from phase 3).

        Args:
            volume: Volume to check.
            field: Field path reported in the issue.

        Returns:
            Success or ``TIMER_VOLUME_OUT_OF_RANGE`` (``min``, ``max``).
        """
        if MIN_VOLUME_PERCENT <= volume.percent <= MAX_VOLUME_PERCENT:
            return ValidationResult.success()
        return ValidationResult.failure(
            ErrorCodeEnum.TIMER_VOLUME_OUT_OF_RANGE, field=field, min=MIN_VOLUME_PERCENT, max=MAX_VOLUME_PERCENT
        )

    @staticmethod
    def validate_loop_count(loop_count: int, limits: TimerLimits) -> ValidationResult:
        """Check the play count (checked even when the sound repeats until stopped).

        Args:
            loop_count: Play count.
            limits: Bounds.

        Returns:
            Success or ``TIMER_LOOP_COUNT_OUT_OF_RANGE`` (``min``, ``max``).
        """
        if MIN_LOOP_COUNT <= loop_count <= limits.max_loop_count:
            return ValidationResult.success()
        return ValidationResult.failure(
            ErrorCodeEnum.TIMER_LOOP_COUNT_OUT_OF_RANGE,
            field=LOOP_COUNT_FIELD,
            min=MIN_LOOP_COUNT,
            max=limits.max_loop_count,
        )

    @staticmethod
    def validate_auto_stop(auto_stop_seconds: int, limits: TimerLimits) -> ValidationResult:
        """Check the automatic stop: 0 (never) or between the configured bounds.

        Args:
            auto_stop_seconds: Delay in seconds.
            limits: Bounds.

        Returns:
            Success or ``TIMER_AUTO_STOP_OUT_OF_RANGE`` (``min``, ``max``).
        """
        if auto_stop_seconds == NEVER_AUTO_STOP:
            return ValidationResult.success()
        if limits.min_auto_stop_seconds <= auto_stop_seconds <= limits.max_auto_stop_seconds:
            return ValidationResult.success()
        return ValidationResult.failure(
            ErrorCodeEnum.TIMER_AUTO_STOP_OUT_OF_RANGE,
            field=AUTO_STOP_FIELD,
            min=limits.min_auto_stop_seconds,
            max=limits.max_auto_stop_seconds,
        )
