"""Rules shared by every entity: id and timestamps."""

from typing import Final

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.identified import Identified
from concentrator.domain.common.time_rules import TimeRules
from concentrator.domain.common.validation_result import ValidationResult

ID_FIELD: Final = "id"
CREATED_AT_FIELD: Final = "created_at"
UPDATED_AT_FIELD: Final = "updated_at"


class EntityRules:
    """Stateless checks of the identity part of an entity."""

    @staticmethod
    def validate_identity(entity: Identified) -> ValidationResult:
        """Check the id (not blank) and both timestamps (timezone-aware UTC).

        Args:
            entity: Entity to check.

        Returns:
            Success, or ``REQUIRED_VALUE_MISSING`` on ``id`` and ``DATETIME_NOT_UTC`` on a timestamp.
        """
        identity = (
            ValidationResult.failure(ErrorCodeEnum.REQUIRED_VALUE_MISSING, field=ID_FIELD)
            if not entity.id.strip()
            else ValidationResult.success()
        )
        return identity.merge(
            TimeRules.validate_utc(entity.created_at, CREATED_AT_FIELD),
            TimeRules.validate_utc(entity.updated_at, UPDATED_AT_FIELD),
        )
