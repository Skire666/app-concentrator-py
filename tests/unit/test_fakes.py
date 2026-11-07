"""The fakes drive many tests: check the non-trivial ones."""

import pytest

from tests.fakes.fake_clock import FakeClock
from tests.fakes.manual_scheduler import ManualScheduler


def test_manual_scheduler_runs_soon_calls_only_when_asked() -> None:
    scheduler = ManualScheduler()
    calls: list[str] = []
    scheduler.call_soon(lambda: calls.append("soon"))

    assert calls == []
    assert scheduler.run_pending() == 1
    assert calls == ["soon"]


def test_manual_scheduler_advance_runs_due_calls_in_time_order_and_skips_cancelled() -> None:
    scheduler = ManualScheduler()
    calls: list[str] = []
    scheduler.call_later(100, lambda: calls.append("100"))
    scheduler.call_later(50, lambda: calls.append("50"))
    scheduler.call_later(60, lambda: calls.append("cancelled")).cancel()
    scheduler.call_later(150, lambda: calls.append("150"))

    scheduler.advance(99)
    assert calls == ["50"]

    scheduler.advance(1)
    assert calls == ["50", "100"]
    assert scheduler.now_ms == 100
    assert scheduler.pending_count == 1


def test_manual_scheduler_runs_calls_scheduled_by_calls() -> None:
    scheduler = ManualScheduler()
    calls: list[str] = []

    def chain() -> None:
        scheduler.call_soon(lambda: calls.append("chained"))

    scheduler.call_later(10, chain)

    scheduler.advance(10)

    assert calls == ["chained"]


def test_fake_clock_advances_wall_and_monotonic_time_together() -> None:
    clock = FakeClock()
    start_utc, start_monotonic = clock.now_utc(), clock.monotonic()

    clock.advance(ms=250, seconds=1)

    assert (clock.now_utc() - start_utc).total_seconds() == pytest.approx(1.0)
    assert clock.monotonic() - start_monotonic == pytest.approx(1.25)
    assert clock.now_local().utcoffset() is not None

    clock.advance(ms=750)

    assert (clock.now_utc() - start_utc).total_seconds() == pytest.approx(2.0)
    assert clock.to_local(start_utc) == start_utc
    assert clock.to_local(start_utc).utcoffset() is not None
