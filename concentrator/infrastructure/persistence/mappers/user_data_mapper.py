"""``UserDataSchema`` <-> ``StoredUserData``."""

from datetime import datetime
from typing import Final

from concentrator.application.storage.user_data import StoredUserData, UserData
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.time_rules import TimeRules
from concentrator.infrastructure.persistence.mappers.user_settings_mapper import UserSettingsMapper
from concentrator.infrastructure.persistence.schemas.user_data_schema import UserDataSchema

SETTINGS_FIELD: Final = "settings"
SAVED_AT_FIELD: Final = "saved_at"


class UserDataMapper:
    """Converts the whole file."""

    @staticmethod
    def to_domain(schema: UserDataSchema) -> DataResult[StoredUserData]:
        """Build and validate every section.

        Args:
            schema: Validated DTO.

        Returns:
            The data and its ``saved_at``, or every rule failure (dotted file paths).
        """
        settings = UserSettingsMapper.to_domain(schema.settings, SETTINGS_FIELD)
        validation = settings.validation.merge(TimeRules.validate_utc(schema.saved_at, SAVED_AT_FIELD))
        if settings.data is None or validation.is_failure:
            return DataResult.fail(validation)
        data = UserData(schema_version=schema.schema_version, settings=settings.data)
        return DataResult.ok(StoredUserData(data=data, saved_at=schema.saved_at), validation)

    @staticmethod
    def to_schema(data: UserData, saved_at: datetime, app_version: str) -> UserDataSchema:
        """Build the DTO written to the file.

        Args:
            data: Validated data.
            saved_at: Instant of this save (timezone-aware UTC).
            app_version: Version of the running application.

        Returns:
            The DTO.
        """
        return UserDataSchema(
            schema_version=data.schema_version,
            saved_at=saved_at,
            app_version=app_version,
            settings=UserSettingsMapper.to_schema(data.settings),
        )
