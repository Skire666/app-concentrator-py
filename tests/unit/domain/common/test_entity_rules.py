from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone

from concentrator.domain.common.entity_rules import EntityRules
from concentrator.domain.common.error_code_enum import ErrorCodeEnum

NOW = datetime(2026, 11, 6, 9, 0, tzinfo=UTC)


@dataclass(frozen=True, slots=True, kw_only=True)
class Entity:
    id: str
    created_at: datetime = NOW
    updated_at: datetime = NOW


def test_validate_identity_accepts_id_and_utc_timestamps() -> None:
    assert EntityRules.validate_identity(Entity(id="019a")).is_success


def test_validate_identity_rejects_blank_id() -> None:
    result = EntityRules.validate_identity(Entity(id="  "))

    assert result.error_codes == (ErrorCodeEnum.REQUIRED_VALUE_MISSING,)
    assert result.issues[0].field == "id"


def test_validate_identity_reports_every_non_utc_timestamp() -> None:
    paris = NOW.astimezone(timezone(timedelta(hours=1)))

    result = EntityRules.validate_identity(Entity(id="", created_at=paris, updated_at=NOW.replace(tzinfo=None)))

    assert result.error_codes == (
        ErrorCodeEnum.REQUIRED_VALUE_MISSING,
        ErrorCodeEnum.DATETIME_NOT_UTC,
        ErrorCodeEnum.DATETIME_NOT_UTC,
    )
    assert [issue.field for issue in result.issues] == ["id", "created_at", "updated_at"]
