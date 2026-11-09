"""Business rules of the hourly chime."""

from typing import Final

from concentrator.domain.common.entity_rules import EntityRules
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.timer.chime_settings import ChimeSettings
from concentrator.domain.timer.hourly_chime import HourlyChime
from concentrator.domain.timer.timer_config_rules import TimerConfigRules

START_HOUR_FIELD: Final = "start_hour"
END_HOUR_FIELD: Final = "end_hour"
FIRST_HOUR: Final = 0
LAST_HOUR: Final = 23


class HourlyChimeRules:
    """Stateless validation of the chime. Field paths are those of the ``[hourly_chime]`` section."""

    @staticmethod
    def validate(chime: HourlyChime) -> ValidationResult:
        """Check the identity and every setting.

        Args:
            chime: Chime to check.

        Returns:
            The merged result.
        """
        return EntityRules.validate_identity(chime).merge(HourlyChimeRules.validate_settings(chime.settings))

    @staticmethod
    def validate_settings(settings: ChimeSettings) -> ValidationResult:
        """Check every editable value (the chime dialog validates its draft with this method).

        Args:
            settings: Values to check.

        Returns:
            The merged result; the sound and volume rules are those of the alarm (fields ``sound`` and
            ``volume``).
        """
        return TimerConfigRules.validate_sound(settings.sound).merge(
            TimerConfigRules.validate_volume(settings.volume),
            HourlyChimeRules.validate_hours(settings.start_hour, settings.end_hour),
        )

    @staticmethod
    def validate_hours(start_hour: int, end_hour: int) -> ValidationResult:
        """Check the active hours.

        Args:
            start_hour: First full hour that chimes.
            end_hour: Last full hour that chimes.

        Returns:
            Success, ``CHIME_HOUR_OUT_OF_RANGE`` (``min``, ``max``) on a field out of 0-23, or
            ``CHIME_HOURS_REVERSED`` on ``end_hour`` when it comes before ``start_hour``.
        """
        ranges = HourlyChimeRules.validate_hour(start_hour, START_HOUR_FIELD).merge(
            HourlyChimeRules.validate_hour(end_hour, END_HOUR_FIELD)
        )
        if ranges.is_failure or start_hour <= end_hour:
            return ranges
        return ValidationResult.failure(ErrorCodeEnum.CHIME_HOURS_REVERSED, field=END_HOUR_FIELD)

    @staticmethod
    def validate_hour(hour: int, field: str) -> ValidationResult:
        """Check one hour.

        Args:
            hour: Hour to check.
            field: Field path reported in the issue.

        Returns:
            Success or ``CHIME_HOUR_OUT_OF_RANGE`` (``min``, ``max``).
        """
        if FIRST_HOUR <= hour <= LAST_HOUR:
            return ValidationResult.success()
        return ValidationResult.failure(
            ErrorCodeEnum.CHIME_HOUR_OUT_OF_RANGE, field=field, min=FIRST_HOUR, max=LAST_HOUR
        )
