"""Business rules of ``UserSettings``."""

from typing import Final

from concentrator.domain.common.entity_rules import EntityRules
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.settings.user_settings import UserSettings

LANGUAGE_FIELD: Final = "language"


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
        return EntityRules.validate_identity(settings).merge(UserSettingsRules.validate_language(settings.language))

    @staticmethod
    def validate_language(language: LanguageEnum) -> ValidationResult:
        """Check that the language is chosen and known.

        Args:
            language: Language to check.

        Returns:
            Success, ``ENUM_VALUE_UNSET`` or ``ENUM_VALUE_UNKNOWN`` on ``language``.
        """
        if language is LanguageEnum.UNSET:
            return ValidationResult.failure(ErrorCodeEnum.ENUM_VALUE_UNSET, field=LANGUAGE_FIELD)
        if not language.is_set:
            return ValidationResult.failure(ErrorCodeEnum.ENUM_VALUE_UNKNOWN, field=LANGUAGE_FIELD)
        return ValidationResult.success()
