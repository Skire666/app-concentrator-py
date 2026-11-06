from dataclasses import dataclass

import pytest

from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from tests.fakes.manual_scheduler import ManualScheduler


@dataclass(frozen=True)
class _Snapshot:
    value: int


class _Panel:
    def __init__(self) -> None:
        self.value = 0
        self.builds = 0
        self.rendered: list[_Snapshot] = []

    def build(self) -> _Snapshot:
        self.builds += 1
        return _Snapshot(self.value)

    def render(self, snapshot: _Snapshot) -> None:
        self.rendered.append(snapshot)


@pytest.fixture
def scheduler() -> ManualScheduler:
    return ManualScheduler()


@pytest.fixture
def coordinator(scheduler: ManualScheduler) -> RenderCoordinator:
    return RenderCoordinator(scheduler)


def _register(coordinator: RenderCoordinator, section: RenderSectionEnum) -> _Panel:
    panel = _Panel()
    coordinator.register(section, panel.build, panel.render)
    return panel


def test_three_requests_in_one_turn_render_once_on_the_next_turn(
    coordinator: RenderCoordinator, scheduler: ManualScheduler
) -> None:
    panel = _register(coordinator, RenderSectionEnum.SHELL)

    coordinator.request(RenderSectionEnum.SHELL)
    coordinator.request(RenderSectionEnum.SHELL)
    coordinator.request(RenderSectionEnum.SHELL)
    assert panel.rendered == []
    assert scheduler.pending_count == 1

    scheduler.run_pending()

    assert panel.builds == 1
    assert panel.rendered == [_Snapshot(0)]


def test_equal_snapshot_is_built_but_not_rendered_again(
    coordinator: RenderCoordinator, scheduler: ManualScheduler
) -> None:
    panel = _register(coordinator, RenderSectionEnum.SHELL)
    coordinator.request(RenderSectionEnum.SHELL)
    scheduler.run_pending()

    coordinator.request(RenderSectionEnum.SHELL)
    scheduler.run_pending()
    panel.value = 5
    coordinator.request(RenderSectionEnum.SHELL)
    scheduler.run_pending()

    assert panel.builds == 3
    assert panel.rendered == [_Snapshot(0), _Snapshot(5)]


def test_request_all_renders_every_section_once(coordinator: RenderCoordinator, scheduler: ManualScheduler) -> None:
    shell = _register(coordinator, RenderSectionEnum.SHELL)
    status = _register(coordinator, RenderSectionEnum.STATUS_BAR)

    coordinator.request_all()
    coordinator.request(RenderSectionEnum.STATUS_BAR)
    scheduler.run_pending()

    assert (shell.builds, status.builds) == (1, 1)
    assert len(shell.rendered) == len(status.rendered) == 1


def test_request_renders_only_the_requested_section(coordinator: RenderCoordinator, scheduler: ManualScheduler) -> None:
    shell = _register(coordinator, RenderSectionEnum.SHELL)
    status = _register(coordinator, RenderSectionEnum.STATUS_BAR)

    coordinator.request(RenderSectionEnum.STATUS_BAR)
    scheduler.run_pending()

    assert (shell.builds, status.builds) == (0, 1)


def test_unregistered_section_is_ignored(coordinator: RenderCoordinator, scheduler: ManualScheduler) -> None:
    coordinator.request(RenderSectionEnum.STATUS_BAR)

    assert scheduler.run_pending() == 1


def test_request_without_section_schedules_nothing(coordinator: RenderCoordinator, scheduler: ManualScheduler) -> None:
    coordinator.request()

    assert scheduler.pending_count == 0


def test_flush_renders_now_and_cancels_the_scheduled_flush(
    coordinator: RenderCoordinator, scheduler: ManualScheduler
) -> None:
    panel = _register(coordinator, RenderSectionEnum.SHELL)
    coordinator.request_all()

    coordinator.flush()

    assert panel.rendered == [_Snapshot(0)]
    assert scheduler.pending_count == 0


def test_request_made_while_rendering_is_flushed_on_the_next_turn(
    coordinator: RenderCoordinator, scheduler: ManualScheduler
) -> None:
    status = _register(coordinator, RenderSectionEnum.STATUS_BAR)

    def render_shell(_snapshot: _Snapshot) -> None:
        coordinator.request(RenderSectionEnum.STATUS_BAR)

    coordinator.register(RenderSectionEnum.SHELL, lambda: _Snapshot(1), render_shell)
    coordinator.request(RenderSectionEnum.SHELL)
    scheduler.run_pending()

    assert len(status.rendered) == 1


def test_registering_a_section_twice_is_a_programming_error(coordinator: RenderCoordinator) -> None:
    _register(coordinator, RenderSectionEnum.SHELL)

    with pytest.raises(ValueError, match="already registered"):
        _register(coordinator, RenderSectionEnum.SHELL)
