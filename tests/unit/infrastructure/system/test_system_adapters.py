import uuid
from datetime import UTC, timedelta

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.infrastructure.system import windows_shell
from concentrator.infrastructure.system.system_clock import SystemClock
from concentrator.infrastructure.system.uuid7_id_generator import Uuid7IdGenerator


def test_system_clock_returns_aware_utc_and_local_times() -> None:
    clock = SystemClock()

    now_utc = clock.now_utc()
    now_local = clock.now_local()

    assert now_utc.tzinfo is UTC
    assert now_local.utcoffset() is not None
    assert abs(now_local - now_utc) < timedelta(seconds=5)


def test_system_clock_monotonic_never_goes_backwards() -> None:
    clock = SystemClock()

    first = clock.monotonic()

    assert clock.monotonic() >= first


def test_uuid7_ids_are_version_7_unique_and_ordered() -> None:
    generator = Uuid7IdGenerator()

    ids = [generator.new_id() for _ in range(50)]

    assert all(uuid.UUID(value).version == 7 for value in ids)
    assert len(set(ids)) == len(ids)
    assert ids == sorted(ids)


def test_set_app_user_model_id_succeeds_for_a_valid_id() -> None:
    assert windows_shell.set_app_user_model_id("skire666.Concentrator.Tests").is_success


def test_set_app_user_model_id_reports_shell_failure() -> None:
    result = windows_shell.set_app_user_model_id("x" * 200)

    assert result.error_codes == (ErrorCodeEnum.APP_USER_MODEL_ID_FAILED,)


def test_allow_set_foreground_window_returns_a_boolean() -> None:
    assert windows_shell.allow_set_foreground_window() in {True, False}
