"""``UserSettingsSchema`` <-> ``UserSettings``."""

from concentrator.application.settings.settings_defaults import SettingsDefaults
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.settings.log_level_enum import LogLevelEnum
from concentrator.domain.settings.user_settings import UserSettings, UserSettingsId
from concentrator.domain.settings.user_settings_rules import UserSettingsRules
from concentrator.infrastructure.persistence.schemas.user_settings_schema import UserSettingsSchema


class UserSettingsMapper:
    """Converts the ``settings`` section."""

    @staticmethod
    def to_domain(
        schema: UserSettingsSchema, field_prefix: str, defaults: SettingsDefaults
    ) -> DataResult[UserSettings]:
        """Build and validate the settings; an unknown enum integer becomes ``UNKNOWN``.

        Args:
            schema: Validated DTO.
            field_prefix: Dotted path of the section in the file (``settings``).
            defaults: Values of the keys a file written before phase 4 does not have.

        Returns:
            The settings, or the rule failures with fields such as ``settings.language``.
        """
        log_level = defaults.log_level if schema.log_level is None else LogLevelEnum.parse(schema.log_level)
        notify = schema.notify_when_inactive
        settings = UserSettings(
            id=UserSettingsId(schema.id),
            created_at=schema.created_at,
            updated_at=schema.updated_at,
            language=LanguageEnum.parse(schema.language),
            log_level=log_level,
            notify_when_inactive=defaults.notify_when_inactive if notify is None else notify,
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
            log_level=settings.log_level.value,
            notify_when_inactive=settings.notify_when_inactive,
        )
