"""``UserDataSchema`` <-> ``StoredUserData``."""

from datetime import datetime
from typing import Final

from concentrator.application.storage.user_data import StoredUserData, UserData, UserDataLimits
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.time_rules import TimeRules
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.timer.timer_config import TimerConfig
from concentrator.domain.timer.timer_limits import TimerLimits
from concentrator.infrastructure.persistence.mappers.timer_config_mapper import TimerConfigMapper
from concentrator.infrastructure.persistence.mappers.user_settings_mapper import UserSettingsMapper
from concentrator.infrastructure.persistence.schemas.timer_config_schema import TimerConfigSchema
from concentrator.infrastructure.persistence.schemas.user_data_schema import UserDataSchema

SETTINGS_FIELD: Final = "settings"
TIMER_FIELD: Final = "timer"
SAVED_AT_FIELD: Final = "saved_at"


def _timer_to_domain(schema: TimerConfigSchema | None, limits: TimerLimits) -> DataResult[TimerConfig | None]:
    """Map the optional ``[timer]`` section.

    Args:
        schema: The section, ``None`` when the file does not have it yet.
        limits: Bounds from ``concentrator.ini``.

    Returns:
        The configuration, ``None`` for an absent section, or the rule failures.
    """
    if schema is None:
        return DataResult[TimerConfig | None](data=None, validation=ValidationResult.success())
    mapped = TimerConfigMapper.to_domain(schema, TIMER_FIELD, limits)
    if mapped.data is None:
        return DataResult.fail(mapped.validation)
    return DataResult[TimerConfig | None](data=mapped.data, validation=mapped.validation)


class UserDataMapper:
    """Converts the whole file."""

    @staticmethod
    def to_domain(schema: UserDataSchema, limits: UserDataLimits) -> DataResult[StoredUserData]:
        """Build and validate every section.

        Args:
            schema: Validated DTO.
            limits: Bounds from ``concentrator.ini`` applied by the domain rules.

        Returns:
            The data and its ``saved_at``, or every rule failure (dotted file paths). A section the
            file does not have yet is ``None``.
        """
        settings = UserSettingsMapper.to_domain(schema.settings, SETTINGS_FIELD)
        timer = _timer_to_domain(schema.timer, limits.timer)
        validation = settings.validation.merge(
            timer.validation, TimeRules.validate_utc(schema.saved_at, SAVED_AT_FIELD)
        )
        if settings.data is None or validation.is_failure:
            return DataResult.fail(validation)
        data = UserData(schema_version=schema.schema_version, settings=settings.data, timer=timer.data)
        return DataResult.ok(StoredUserData(data=data, saved_at=schema.saved_at), validation)

    @staticmethod
    def to_schema(data: UserData, saved_at: datetime, app_version: str) -> UserDataSchema:
        """Build the DTO written to the file.

        Args:
            data: Validated data.
            saved_at: Instant of this save (timezone-aware UTC).
            app_version: Version of the running application.

        Returns:
            The DTO; a section that is ``None`` is not written.
        """
        return UserDataSchema(
            schema_version=data.schema_version,
            saved_at=saved_at,
            app_version=app_version,
            settings=UserSettingsMapper.to_schema(data.settings),
            timer=None if data.timer is None else TimerConfigMapper.to_schema(data.timer),
        )
