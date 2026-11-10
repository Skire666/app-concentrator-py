"""Business rules of ``UserSettings``."""

from typing import Final

from concentrator.domain.common.base_int_enum import UNSET_VALUE, BaseIntEnum
from concentrator.domain.common.entity_rules import EntityRules
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.settings.general_settings import GeneralSettings
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.settings.log_level_enum import LogLevelEnum
from concentrator.domain.settings.user_settings import UserSettings

LANGUAGE_FIELD: Final = "language"
LOG_LEVEL_FIELD: Final = "log_level"


def _validate_chosen(value: BaseIntEnum, field: str) -> ValidationResult:
    """Check that an enum value is chosen and known.

    Args:
        value: Value to check.
        field: Field path reported in the issue.

    Returns:
        Success, ``ENUM_VALUE_UNSET`` or ``ENUM_VALUE_UNKNOWN``.
    """
    if value.value == UNSET_VALUE:
        return ValidationResult.failure(ErrorCodeEnum.ENUM_VALUE_UNSET, field=field)
    if not value.is_set:
        return ValidationResult.failure(ErrorCodeEnum.ENUM_VALUE_UNKNOWN, field=field)
    return ValidationResult.success()


class UserSettingsRules:
    """Stateless validation of the user settings."""

    @staticmethod
    def validate(settings: UserSettings) -> ValidationResult:
        """Check every field.

        Args:
            settings: Settings to check.

        Returns:
            The merged result of the identity and field checks.
        """
        return EntityRules.validate_identity(settings).merge(UserSettingsRules.validate_general(settings.general))

    @staticmethod
    def validate_general(general: GeneralSettings) -> ValidationResult:
        """Check the General values (the settings page validates its draft with this method).

        Args:
            general: Values to check.

        Returns:
            The merged result of the language and log level checks.
        """
        return UserSettingsRules.validate_language(general.language).merge(
            UserSettingsRules.validate_log_level(general.log_level)
        )

    @staticmethod
    def validate_language(language: LanguageEnum) -> ValidationResult:
        """Check that the language is chosen and known.

        Args:
            language: Language to check.

        Returns:
            Success, ``ENUM_VALUE_UNSET`` or ``ENUM_VALUE_UNKNOWN`` on ``language``.
        """
        return _validate_chosen(language, LANGUAGE_FIELD)

    @staticmethod
    def validate_log_level(log_level: LogLevelEnum) -> ValidationResult:
        """Check that the log level is chosen and known.

        Args:
            log_level: Level to check.

        Returns:
            Success, ``ENUM_VALUE_UNSET`` or ``ENUM_VALUE_UNKNOWN`` on ``log_level``.
        """
        return _validate_chosen(log_level, LOG_LEVEL_FIELD)
