"""Timer panel, edit dialog and notification area icon on the offscreen platform."""

from dataclasses import replace

import pytest
from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QSystemTrayIcon
from pytestqt.qtbot import QtBot

from concentrator.domain.timer.duration import Duration
from concentrator.domain.timer.timer_settings import TimerSettings
from concentrator.domain.timer.timer_state_enum import TimerStateEnum
from concentrator.domain.timer.timer_transition_enum import TimerTransitionEnum
from concentrator.domain.timer.volume import Volume
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.timer.timer_layout import TimerLayout
from concentrator.ui.panels.timer_edit_form_panel import TimerEditFormPanel
from concentrator.ui.panels.timer_panel import TimerPanel
from concentrator.ui.support.modal_host import ScreenDialogRunner
from concentrator.ui.support.styles import INVALID_PROPERTY
from concentrator.ui.windows.timer_edit_dialog import TimerEditWindow
from tests.fakes.app_config_factory import make_ui_section
from tests.fakes.timer_factory import DEFAULT_SETTINGS
from tests.fakes.timer_ui_stack import TimerUiStack
from tests.ui.shell_harness import ShellHarness

pytestmark = pytest.mark.ui
LAYOUT = TimerLayout.from_ui_section(make_ui_section())
SETTINGS: TimerSettings = replace(DEFAULT_SETTINGS, duration=Duration(10), auto_stop_seconds=0)


class Recorder:
    """Records the arguments of each signal emission (one value, or a tuple of values)."""

    def __init__(self) -> None:
        self.values: list[object] = []

    def __call__(self, *args: object) -> None:
        self.values.append(args[0] if len(args) == 1 else args)


def _panel(qtbot: QtBot) -> TimerPanel:
    panel = TimerPanel(LAYOUT)
    qtbot.addWidget(panel)
    return panel


def _stack(state: TimerStateEnum) -> TimerUiStack:
    stack = TimerUiStack(SETTINGS)
    if state is not TimerStateEnum.IDLE:
        stack.click(ActionIdEnum.TIMER_START)
    if state is TimerStateEnum.PAUSED:
        stack.click(ActionIdEnum.TIMER_PAUSE)
    if state is TimerStateEnum.RINGING:
        stack.advance(seconds=10)
    stack.scheduler.advance(100)
    return stack


@pytest.mark.parametrize(
    ("state", "texts", "alert"),
    [
        (TimerStateEnum.IDLE, ("timer_edit", "timer_reset", "timer_start"), False),
        (TimerStateEnum.RUNNING, ("timer_edit", "timer_reset", "timer_pause"), False),
        (TimerStateEnum.PAUSED, ("timer_edit", "timer_reset", "timer_resume"), False),
        (TimerStateEnum.RINGING, ("timer_restart", "timer_acknowledge", "timer_snooze"), True),
    ],
)
def test_timer_panel_renders_each_state(
    qtbot: QtBot, state: TimerStateEnum, texts: tuple[str, str, str], alert: bool
) -> None:
    panel = _panel(qtbot)
    snapshot = _stack(state).snapshot

    panel.render_snapshot(snapshot)

    assert panel.digits.text() == snapshot.digits
    assert panel.caption.text() == snapshot.caption
    assert panel.digits.alert is alert
    assert [button.text() for button in panel.buttons] == [f"en:action.{text}(minutes=5)" for text in texts]
    assert [button.isEnabled() for button in panel.buttons] == [
        button.enabled for button in (snapshot.left, snapshot.middle, snapshot.right)
    ]


def test_timer_digits_use_a_fixed_pitch_font_of_the_ini_size(qtbot: QtBot) -> None:
    panel = _panel(qtbot)
    font = panel.digits.font()

    assert font.pixelSize() == 64
    assert font.fixedPitch()


def test_a_button_click_emits_the_action_it_shows(qtbot: QtBot) -> None:
    panel = _panel(qtbot)
    panel.render_snapshot(_stack(TimerStateEnum.IDLE).snapshot)

    recorder = Recorder()
    panel.action_requested.connect(recorder)

    panel.buttons[2].click()

    assert recorder.values == [int(ActionIdEnum.TIMER_START)]


def test_a_double_click_on_start_performs_one_start(qtbot: QtBot) -> None:
    harness = ShellHarness()
    qtbot.addWidget(harness.window)
    harness.window.show()
    qtbot.waitExposed(harness.window)
    start = harness.window.timer_panel.buttons[2]

    QTest.mouseClick(start, Qt.MouseButton.LeftButton)
    QTest.mouseClick(start, Qt.MouseButton.LeftButton)  # second click of a double click, before any render
    harness.turn()

    started = [event for event in harness.timer.events if TimerTransitionEnum.STARTED in event.transitions]
    assert len(started) == 1
    assert harness.timer.queries.current_view().state is TimerStateEnum.RUNNING
    assert not start.isEnabled()
    harness.scheduler.advance(100)
    assert start.isEnabled()
    start.click()
    assert harness.timer.queries.current_view().state is TimerStateEnum.PAUSED


def test_ringing_on_another_page_highlights_the_focus_button(qtbot: QtBot) -> None:
    harness = ShellHarness()
    qtbot.addWidget(harness.window)
    harness.timer.engine.change(lambda session, now: session.start(now, Duration(1)), TimerTransitionEnum.STARTED)
    harness.window.module_bar.button(ActionIdEnum.SHELL_SHOW_JOURNAL).click()
    harness.turn()

    harness.timer.advance(seconds=1)
    harness.turn()

    focus = harness.window.module_bar.button(ActionIdEnum.SHELL_SHOW_FOCUS)
    assert focus.property("highlighted") is True
    assert harness.window.timer_panel.digits.text() == "00:00:00"


def test_edit_form_panel_shows_the_snapshot_without_emitting(qtbot: QtBot) -> None:
    stack = TimerUiStack(SETTINGS)
    panel = TimerEditFormPanel(LAYOUT)
    qtbot.addWidget(panel)
    recorder = Recorder()
    panel.duration_changed.connect(recorder)
    panel.volume_changed.connect(recorder)

    panel.render_snapshot(stack.edit_snapshot)

    assert [spin.value() for spin in panel.duration_input.spin_boxes] == [0, 0, 10]
    assert panel.sound_picker.combo.count() == 2
    assert panel.volume_slider.slider.value() == 80
    assert panel.loop_count.value() == 3
    assert not panel.auto_restart.isEnabled()
    assert not panel.save_button.isEnabled()
    assert panel.note.isHidden()
    assert recorder.values == []


def test_edit_form_panel_shows_inline_errors(qtbot: QtBot) -> None:
    stack = TimerUiStack(SETTINGS)
    panel = TimerEditFormPanel(LAYOUT)
    qtbot.addWidget(panel)
    stack.editor.on_duration_changed(0, 0, 0)

    panel.render_snapshot(stack.edit_snapshot)

    assert panel.error_label("duration").text() == "en:error.timer_duration_too_short(min=00:00:01)"
    assert not panel.error_label("duration").isHidden()
    assert panel.error_label("sound").isHidden()
    assert panel.duration_input.spin_boxes[0].property(INVALID_PROPERTY) is True


def test_edit_form_panel_forwards_user_changes(qtbot: QtBot) -> None:
    panel = TimerEditFormPanel(LAYOUT)
    qtbot.addWidget(panel)
    panel.render_snapshot(TimerUiStack(SETTINGS).edit_snapshot)
    recorder = Recorder()
    for signal in (panel.loop_forever_changed, panel.duration_changed, panel.sound_selected, panel.auto_stop_changed):
        signal.connect(recorder)

    panel.loop_forever.setChecked(True)
    panel.duration_input.spin_boxes[1].setValue(5)
    panel.sound_picker.combo.setCurrentIndex(1)
    panel.auto_stop.setValue(30)

    assert recorder.values == [True, (0, 5, 10), 1, 30]


def test_edit_dialog_saves_what_the_user_changed(qtbot: QtBot) -> None:
    stack = TimerUiStack(SETTINGS, register_editor=False)
    window = TimerEditWindow(stack.editor, stack.renderer, ScreenDialogRunner(), LAYOUT)
    qtbot.addWidget(window.dialog)
    stack.editor.attach(window, stack.dialogs)
    panel = window.dialog.panel

    def act() -> None:
        panel.volume_slider.slider.setValue(30)
        stack.scheduler.advance(100)
        panel.save_button.click()

    QTimer.singleShot(0, act)
    stack.click(ActionIdEnum.TIMER_EDIT)

    assert stack.config.config is not None
    assert stack.config.config.settings.volume == Volume(30)
    assert window.dialog.windowTitle() == "en:timer.edit.title"
    assert not window.dialog.isVisible()


def test_escape_on_a_dirty_edit_dialog_asks_first(qtbot: QtBot) -> None:
    stack = TimerUiStack(SETTINGS, register_editor=False)
    window = TimerEditWindow(stack.editor, stack.renderer, ScreenDialogRunner(), LAYOUT)
    qtbot.addWidget(window.dialog)
    stack.editor.attach(window, stack.dialogs)
    stack.dialogs.confirm_answers = [False, True]

    def act() -> None:
        window.dialog.panel.volume_slider.slider.setValue(30)
        window.dialog.reject()
        assert window.dialog.isVisible()
        window.dialog.reject()

    QTimer.singleShot(0, act)
    stack.click(ActionIdEnum.TIMER_EDIT)

    assert len(stack.dialogs.texts("confirm")) == 2
    assert stack.config.updates == []


def test_tray_panel_renders_and_emits(qtbot: QtBot) -> None:
    harness = ShellHarness()
    qtbot.addWidget(harness.window)
    tray = harness.window.tray
    show, quit_action = tray.menu_actions
    emitted: list[int] = []
    tray.action_requested.connect(emitted.append)

    show.trigger()
    tray.tray_icon.activated.emit(QSystemTrayIcon.ActivationReason.Trigger)
    tray.tray_icon.activated.emit(QSystemTrayIcon.ActivationReason.Context)
    tray.tray_icon.messageClicked.emit()
    tray.show()
    tray.hide()

    assert tray.tray_icon.toolTip() == "en:app.title"
    assert (show.text(), quit_action.text()) == ("en:action.tray_show", "en:action.tray_quit")
    assert emitted == [int(ActionIdEnum.TRAY_SHOW)] * 3


def test_tray_quit_closes_the_window_after_the_question(qtbot: QtBot) -> None:
    harness = ShellHarness()
    qtbot.addWidget(harness.window)
    harness.window.show()
    qtbot.waitExposed(harness.window)

    harness.window.tray.menu_actions[1].trigger()

    assert not harness.window.isVisible()
    assert harness.stack.dialogs.texts("confirm")[0][0] == "en:shutdown.confirm.title"


def test_tray_show_brings_the_window_back(qtbot: QtBot) -> None:
    harness = ShellHarness()
    qtbot.addWidget(harness.window)

    harness.window.tray.menu_actions[0].trigger()

    assert harness.window.isVisible()
