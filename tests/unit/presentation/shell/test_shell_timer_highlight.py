"""The Focus button is highlighted while the timer rings and another page is shown."""

from concentrator.application.timer.timer_events import TimerChangedEvent
from concentrator.domain.timer.timer_transition_enum import TimerTransitionEnum
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.shell.shell_presenter import ShellPresenter
from concentrator.presentation.shell.shell_snapshot import ShellSnapshot
from tests.fakes.fake_clock import FakeClock
from tests.fakes.fake_translator import FakeTranslator
from tests.fakes.manual_scheduler import ManualScheduler


class Setup:
    def __init__(self) -> None:
        self.ringing = False
        self.scheduler = ManualScheduler()
        self.renderer = RenderCoordinator(self.scheduler)
        gate = ActionGate(FakeClock(), self.scheduler, self.renderer, cooldown_ms=100, slow_threshold_ms=200)
        self.presenter = ShellPresenter(FakeTranslator(), gate, self.renderer, lambda: self.ringing)
        self.renders: list[ShellSnapshot] = []
        self.renderer.register(RenderSectionEnum.SHELL, self.presenter.build_shell_snapshot, self.renders.append)

    def highlighted(self) -> list[bool]:
        return [button.highlighted for button in self.presenter.build_shell_snapshot().module_buttons]

    def show(self, action: ActionIdEnum) -> None:
        self.scheduler.advance(100)
        self.presenter.on_action_requested(int(action))
        self.scheduler.run_pending()


def test_no_highlight_while_the_timer_is_silent() -> None:
    setup = Setup()
    setup.show(ActionIdEnum.SHELL_SHOW_JOURNAL)

    assert setup.highlighted() == [False, False, False]


def test_focus_is_highlighted_when_ringing_on_another_page() -> None:
    setup = Setup()
    setup.show(ActionIdEnum.SHELL_SHOW_SETTINGS)

    setup.ringing = True

    assert setup.highlighted() == [True, False, False]


def test_focus_is_not_highlighted_on_the_focus_page() -> None:
    setup = Setup()
    setup.ringing = True

    assert setup.highlighted() == [False, False, False]


def test_only_transitions_re_render_the_shell() -> None:
    setup = Setup()
    setup.scheduler.run_pending()
    setup.renders.clear()
    setup.show(ActionIdEnum.SHELL_SHOW_JOURNAL)
    rendered = len(setup.renders)

    setup.presenter.on_timer_changed(TimerChangedEvent(transitions=(), displayed_seconds=3))
    setup.scheduler.run_pending()
    assert len(setup.renders) == rendered

    setup.ringing = True
    setup.presenter.on_timer_changed(
        TimerChangedEvent(transitions=(TimerTransitionEnum.ALARM_STARTED,), displayed_seconds=0)
    )
    setup.scheduler.run_pending()
    assert setup.renders[-1].module_buttons[0].highlighted
