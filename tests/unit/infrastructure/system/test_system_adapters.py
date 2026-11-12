import logging
import sys
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.infrastructure.system import windows_shell
from concentrator.infrastructure.system.process_age import log_startup_time, process_age_ms
from concentrator.infrastructure.system.system_clock import SystemClock
from concentrator.infrastructure.system.uuid7_id_generator import Uuid7IdGenerator

PROCESS_AGE_SANITY_MS = 24 * 60 * 60 * 1000


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


def test_system_clock_truncates_wall_clock_to_whole_seconds_but_not_monotonic() -> None:
    precise = datetime(2026, 11, 6, 16, 44, 3, 987_654, tzinfo=UTC)
    precise_monotonic = 1234.567_891_234
    clock = SystemClock(wall_clock=lambda: precise, monotonic_clock=lambda: precise_monotonic)

    assert clock.now_utc() == datetime(2026, 11, 6, 16, 44, 3, tzinfo=UTC)
    assert clock.now_local().microsecond == 0
    assert clock.now_local() == clock.now_utc()
    assert clock.monotonic() == pytest.approx(precise_monotonic, rel=0, abs=1e-9)


def test_system_clock_real_sources_give_whole_seconds() -> None:
    clock = SystemClock()

    assert clock.now_utc().microsecond == 0
    assert clock.now_local().microsecond == 0


def test_system_clock_to_local_keeps_the_instant() -> None:
    moment = datetime(2026, 11, 6, 16, 44, 3, tzinfo=UTC)

    local = SystemClock().to_local(moment)

    assert local == moment
    assert local.utcoffset() is not None


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


@pytest.mark.skipif(sys.platform != "win32", reason="GetProcessTimes is a Windows API")
def test_process_age_counts_from_process_creation() -> None:
    elapsed = process_age_ms()

    assert elapsed is not None
    assert 0 < elapsed < PROCESS_AGE_SANITY_MS


def test_process_age_is_unknown_outside_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")

    assert process_age_ms() is None


@pytest.mark.skipif(sys.platform != "win32", reason="GetProcessTimes is a Windows API")
def test_startup_time_is_logged_at_info(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="concentrator.infrastructure.system.process_age"):
        log_startup_time()

    assert "Startup took " in caplog.text
    assert " ms (process start to main window shown)" in caplog.text


def test_startup_time_is_not_logged_outside_windows(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(sys, "platform", "linux")

    with caplog.at_level(logging.INFO):
        log_startup_time()

    assert "Startup took" not in caplog.text
