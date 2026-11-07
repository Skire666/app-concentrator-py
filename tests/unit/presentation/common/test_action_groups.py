"""Timer button actions share their cooldown (ADR-038)."""

from concentrator.domain.common.validation_result import ValidationResult
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.action_groups import TIMER_BUTTON_ACTIONS, group_of
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from tests.fakes.fake_clock import FakeClock
from tests.fakes.manual_scheduler import ManualScheduler


def _gate() -> tuple[ActionGate, ManualScheduler, list[RenderSectionEnum]]:
    scheduler = ManualScheduler()
    renderer = RenderCoordinator(scheduler)
    built: list[RenderSectionEnum] = []
    for section in (RenderSectionEnum.TIMER, RenderSectionEnum.SHELL):
        renderer.register(section, lambda section=section: built.append(section) or len(built), lambda _s: None)
    gate = ActionGate(FakeClock(), scheduler, renderer, cooldown_ms=100, slow_threshold_ms=200)
    return gate, scheduler, built


def test_timer_actions_form_one_group_and_others_are_alone() -> None:
    assert group_of(ActionIdEnum.TIMER_START) == TIMER_BUTTON_ACTIONS
    assert ActionIdEnum.TIMER_EDIT in TIMER_BUTTON_ACTIONS
    assert ActionIdEnum.TIMER_EDIT_SAVE not in TIMER_BUTTON_ACTIONS
    assert group_of(ActionIdEnum.SHELL_SHOW_FOCUS) == frozenset({ActionIdEnum.SHELL_SHOW_FOCUS})


def test_a_busy_action_makes_its_whole_group_busy() -> None:
    gate, scheduler, _built = _gate()

    gate.run(ActionIdEnum.TIMER_START, ValidationResult.success)

    assert gate.is_busy(ActionIdEnum.TIMER_PAUSE)
    assert gate.run(ActionIdEnum.TIMER_PAUSE, ValidationResult.success).is_skipped
    assert not gate.is_busy(ActionIdEnum.SHELL_SHOW_FOCUS)
    scheduler.advance(100)
    assert not gate.is_busy(ActionIdEnum.TIMER_PAUSE)


def test_the_sections_of_the_group_are_rendered_once() -> None:
    gate, scheduler, built = _gate()
    scheduler.run_pending()
    built.clear()

    gate.run(ActionIdEnum.TIMER_START, ValidationResult.success)
    scheduler.run_pending()

    assert built == [RenderSectionEnum.TIMER]
