"""``UserSettingsSchema`` <-> ``UserSettings``."""

from concentrator.domain.common.data_result import DataResult
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.settings.user_settings import UserSettings, UserSettingsId
from concentrator.domain.settings.user_settings_rules import UserSettingsRules
from concentrator.infrastructure.persistence.schemas.user_settings_schema import UserSettingsSchema


class UserSettingsMapper:
    """Converts the ``settings`` section."""

    @staticmethod
    def to_domain(schema: UserSettingsSchema, field_prefix: str) -> DataResult[UserSettings]:
        """Build and validate the settings; an unknown language integer becomes ``UNKNOWN``.

        Args:
            schema: Validated DTO.
            field_prefix: Dotted path of the section in the file (``settings``).

        Returns:
            The settings, or the rule failures with fields such as ``settings.language``.
        """
        settings = UserSettings(
            id=UserSettingsId(schema.id),
            created_at=schema.created_at,
            updated_at=schema.updated_at,
            language=LanguageEnum.parse(schema.language),
        )
        validation = UserSettingsRules.validate(settings).prefixed(field_prefix)
        if validation.is_failure:
            return DataResult.fail(validation)
        return DataResult.ok(settings, validation)

    @staticmethod
    def to_schema(settings: UserSettings) -> UserSettingsSchema:
        """Build the DTO written to the file.

        Args:
            settings: Validated settings.

        Returns:
            The DTO; enums are written as integers.
        """
        return UserSettingsSchema(
            id=settings.id,
            created_at=settings.created_at,
            updated_at=settings.updated_at,
            language=settings.language.value,
        )
