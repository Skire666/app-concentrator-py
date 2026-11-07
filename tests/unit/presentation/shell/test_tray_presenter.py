from typing import override

import pytest

from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.ports.main_window_port import MainWindowPort
from concentrator.presentation.shell.tray_presenter import TrayPresenter
from tests.fakes.fake_clock import FakeClock
from tests.fakes.fake_translator import FakeTranslator
from tests.fakes.manual_scheduler import ManualScheduler


class FakeWindow(MainWindowPort):
    def __init__(self) -> None:
        self.calls: list[str] = []

    @override
    def show_in_front(self) -> None:
        self.calls.append("show")

    @override
    def request_close(self) -> None:
        self.calls.append("close")


class Setup:
    def __init__(self) -> None:
        self.scheduler = ManualScheduler()
        self.gate = ActionGate(
            FakeClock(), self.scheduler, RenderCoordinator(self.scheduler), cooldown_ms=100, slow_threshold_ms=200
        )
        self.window = FakeWindow()
        self.presenter = TrayPresenter(FakeTranslator(), self.gate)
        self.presenter.attach(self.window)


@pytest.fixture
def setup() -> Setup:
    return Setup()


def test_snapshot_has_the_title_and_both_menu_items(setup: Setup) -> None:
    snapshot = setup.presenter.build_snapshot()

    assert snapshot.tooltip == "en:app.title"
    assert snapshot.show_action.text == "en:action.tray_show"
    assert snapshot.show_action.action is ActionIdEnum.TRAY_SHOW
    assert snapshot.quit_action.text == "en:action.tray_quit"
    assert snapshot.quit_action.enabled


def test_show_brings_the_window_to_the_front(setup: Setup) -> None:
    setup.presenter.on_action_requested(int(ActionIdEnum.TRAY_SHOW))

    assert setup.window.calls == ["show"]


def test_quit_closes_the_window_like_its_close_button(setup: Setup) -> None:
    setup.presenter.on_action_requested(int(ActionIdEnum.TRAY_QUIT))

    assert setup.window.calls == ["close"]
    assert not setup.presenter.build_snapshot().quit_action.enabled


def test_unknown_action_is_logged(setup: Setup, caplog: pytest.LogCaptureFixture) -> None:
    setup.presenter.on_action_requested(int(ActionIdEnum.TIMER_START))

    assert "Tray action TIMER_START (16) is not handled" in caplog.text
    assert setup.window.calls == []


def test_using_the_presenter_before_attach_is_a_wiring_error(setup: Setup) -> None:
    presenter = TrayPresenter(FakeTranslator(), setup.gate)

    with pytest.raises(RuntimeError, match="attach"):
        presenter.on_action_requested(int(ActionIdEnum.TRAY_SHOW))
