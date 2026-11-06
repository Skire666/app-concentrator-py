import logging

import pytest

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from tests.fakes.fake_clock import FakeClock
from tests.fakes.manual_scheduler import ManualScheduler

GATE_LOGGER = "concentrator.presentation.common.action_gate"
ACTION = ActionIdEnum.SHELL_TOGGLE_LANGUAGE


class _Renders:
    def __init__(self, coordinator: RenderCoordinator) -> None:
        self.builds: dict[RenderSectionEnum, int] = {}
        for section in (RenderSectionEnum.SHELL, RenderSectionEnum.STATUS_BAR):
            coordinator.register(section, lambda section=section: self._build(section), lambda _snapshot: None)

    def _build(self, section: RenderSectionEnum) -> int:
        self.builds[section] = self.builds.get(section, 0) + 1
        return self.builds[section]


class _Harness:
    def __init__(self) -> None:
        self.clock = FakeClock()
        self.scheduler = ManualScheduler()
        coordinator = RenderCoordinator(self.scheduler)
        self.renders = _Renders(coordinator)
        self.gate = ActionGate(self.clock, self.scheduler, coordinator, cooldown_ms=100, slow_threshold_ms=200)


@pytest.fixture
def harness() -> _Harness:
    return _Harness()


def test_run_returns_the_operation_result_and_marks_the_action_busy(harness: _Harness) -> None:
    failure = ValidationResult.failure(ErrorCodeEnum.FORMAT_INVALID)

    result = harness.gate.run(ACTION, lambda: failure)

    assert result is failure
    assert harness.gate.is_busy(ACTION)
    assert not harness.gate.is_busy(ActionIdEnum.SHELL_SHOW_FOCUS)


def test_busy_action_is_skipped_without_running(harness: _Harness) -> None:
    calls: list[str] = []
    harness.gate.run(ACTION, ValidationResult.success)

    result = harness.gate.run(ACTION, lambda: calls.append("ran") or ValidationResult.success())

    assert result.is_skipped
    assert calls == []


def test_cooldown_releases_the_action_after_100_ms(harness: _Harness) -> None:
    harness.gate.run(ACTION, ValidationResult.success)

    harness.scheduler.advance(99)
    assert harness.gate.is_busy(ACTION)

    harness.scheduler.advance(1)
    assert not harness.gate.is_busy(ACTION)


def test_cooldown_counts_the_time_spent_in_the_operation(harness: _Harness) -> None:
    def slow_operation() -> ValidationResult:
        harness.clock.advance(ms=60)
        return ValidationResult.success()

    harness.gate.run(ACTION, slow_operation)

    harness.scheduler.advance(40)
    assert not harness.gate.is_busy(ACTION)


def test_only_the_sections_bound_to_the_action_are_rendered(harness: _Harness) -> None:
    harness.gate.run(ACTION, ValidationResult.success)
    harness.scheduler.run_pending()
    harness.scheduler.advance(100)

    assert harness.renders.builds == {RenderSectionEnum.STATUS_BAR: 2}


def test_slow_action_is_logged_at_info(harness: _Harness, caplog: pytest.LogCaptureFixture) -> None:
    def slow_operation() -> ValidationResult:
        harness.clock.advance(ms=250)
        return ValidationResult.success()

    with caplog.at_level(logging.INFO, logger=GATE_LOGGER):
        harness.gate.run(ACTION, slow_operation)

    assert [record.getMessage() for record in caplog.records] == ["Action SHELL_TOGGLE_LANGUAGE took 250 ms"]


def test_fast_or_interactive_actions_are_not_logged(harness: _Harness, caplog: pytest.LogCaptureFixture) -> None:
    def slow_dialog() -> ValidationResult:
        harness.clock.advance(seconds=5)
        return ValidationResult.success()

    with caplog.at_level(logging.INFO, logger=GATE_LOGGER):
        harness.gate.run(ActionIdEnum.SHELL_SHOW_FOCUS, ValidationResult.success)
        harness.gate.run(ACTION, slow_dialog, interactive=True)

    assert caplog.records == []


def test_operation_exception_propagates_and_still_releases(harness: _Harness) -> None:
    def broken() -> ValidationResult:
        raise LookupError

    with pytest.raises(LookupError):
        harness.gate.run(ACTION, broken)

    harness.scheduler.advance(100)
    assert not harness.gate.is_busy(ACTION)


def test_token_keeps_the_action_busy_until_finished(harness: _Harness) -> None:
    token = harness.gate.begin(ACTION)
    assert token.data is not None
    assert harness.gate.begin(ACTION).validation.is_skipped

    harness.scheduler.advance(500)
    assert harness.gate.is_busy(ACTION)

    token.data.finish()
    token.data.finish()
    harness.scheduler.advance(100)
    assert not harness.gate.is_busy(ACTION)
    assert harness.scheduler.pending_count == 0
