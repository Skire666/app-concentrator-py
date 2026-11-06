from datetime import UTC, datetime, timedelta, timezone

import pytest

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.time_rules import TimeRules


def test_validate_utc_accepts_aware_utc() -> None:
    result = TimeRules.validate_utc(datetime(2026, 11, 6, 12, 0, tzinfo=UTC), "created_at")

    assert result.is_success


@pytest.mark.parametrize(
    "value",
    [
        datetime(2026, 11, 6, 12, 0, tzinfo=UTC).replace(tzinfo=None),
        datetime(2026, 11, 6, 12, 0, tzinfo=timezone(timedelta(hours=1))),
    ],
)
def test_validate_utc_rejects_naive_or_offset(value: datetime) -> None:
    result = TimeRules.validate_utc(value, "created_at")

    assert result.error_codes == (ErrorCodeEnum.DATETIME_NOT_UTC,)
    assert result.issues_for("created_at")
