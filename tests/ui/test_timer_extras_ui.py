"""Favorites, special options and their dialogs on the offscreen platform."""

import pytest
from PySide6.QtCore import QPoint, QRect, QSize, Qt, QTimer
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton, QWidget
from pytestqt.qtbot import QtBot

from concentrator.domain.timer.duration import Duration
from concentrator.domain.timer.timer_presets_collection import TimerPresetsCollection
from concentrator.domain.timer.timer_state_enum import TimerStateEnum
from concentrator.domain.timer.volume import Volume
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.timer.timer_layout import TimerLayout
from concentrator.ui.panels.presets_panel import PresetsPanel
from concentrator.ui.panels.special_options_panel import SpecialOptionsPanel
from concentrator.ui.support.modal_host import ScreenDialogRunner
from concentrator.ui.support.styles import INVALID_PROPERTY
from concentrator.ui.widgets.flow_layout import FlowLayout
from concentrator.ui.windows.chime_settings_dialog import ChimeSettingsWindow
from concentrator.ui.windows.preset_edit_dialog import PresetEditWindow
from tests.fakes.app_config_factory import make_ui_section
from tests.fakes.timer_extras_factory import make_preset, make_presets
from tests.fakes.timer_ui_stack import TimerUiStack
from tests.ui.shell_harness import ShellHarness

pytestmark = pytest.mark.ui
LAYOUT = TimerLayout.from_ui_section(make_ui_section())
BUTTON_SIZE = QSize(80, 30)


class Recorder:
    """Records the arguments of each signal emission (one value, or a tuple of values)."""

    def __init__(self) -> None:
        self.values: list[object] = []

    def __call__(self, *args: object) -> None:
        self.values.append(args[0] if len(args) == 1 else args)


def _presets_panel(qtbot: QtBot, stack: TimerUiStack) -> PresetsPanel:
    panel = PresetsPanel(LAYOUT)
    qtbot.addWidget(panel)
    panel.render_snapshot(stack.presets_snapshot)
    return panel


def _fixed_buttons(host: QWidget, count: int) -> list[QPushButton]:
    buttons: list[QPushButton] = []
    for _index in range(count):
        button = QPushButton(host)
        button.setFixedSize(BUTTON_SIZE)
        buttons.append(button)
    return buttons


def test_flow_layout_wraps_onto_new_lines(qtbot: QtBot) -> None:
    host = QWidget()
    qtbot.addWidget(host)
    flow = FlowLayout(host, 10)
    buttons = _fixed_buttons(host, 3)
    for button in buttons:
        flow.addWidget(button)

    flow.setGeometry(QRect(0, 0, 180, 200))

    assert [button.geometry().topLeft() for button in buttons] == [QPoint(0, 0), QPoint(90, 0), QPoint(0, 40)]
    assert flow.heightForWidth(180) == 70
    assert flow.heightForWidth(300) == 30
    assert flow.hasHeightForWidth()


def test_flow_layout_skips_hidden_widgets_and_inserts_in_order(qtbot: QtBot) -> None:
    host = QWidget()
    qtbot.addWidget(host)
    flow = FlowLayout(host, 10)
    first, last, inserted = _fixed_buttons(host, 3)
    flow.addWidget(first)
    flow.addWidget(last)
    flow.insert_widget(1, inserted)
    first.hide()

    flow.setGeometry(QRect(0, 0, 400, 100))

    items = [flow.itemAt(index) for index in range(flow.count())]
    assert [item.widget() for item in items if item is not None] == [first, inserted, last]
    assert inserted.geometry().topLeft() == QPoint(0, 0)
    assert flow.minimumSize() == BUTTON_SIZE
    assert flow.itemAt(5) is None
    assert flow.takeAt(5) is None
    assert flow.expandingDirections() == Qt.Orientation(0)


def test_presets_panel_renders_one_button_per_favorite_then_add(qtbot: QtBot) -> None:
    stack = TimerUiStack()
    panel = _presets_panel(qtbot, stack)

    assert [button.text() for button in panel.preset_buttons] == [
        "en:duration.label.minutes(minutes=15)",
        "en:duration.label.minutes(minutes=30)",
        "en:duration.label.minutes(minutes=45)",
    ]
    assert panel.add_button.text() == "en:action.preset_add"
    assert panel.title.text() == "en:presets.title"
    assert panel.empty_label.isHidden()


def test_presets_panel_emits_the_preset_id_with_the_action(qtbot: QtBot) -> None:
    stack = TimerUiStack()
    panel = _presets_panel(qtbot, stack)
    recorder = Recorder()
    panel.preset_action_requested.connect(recorder)
    panel.action_requested.connect(recorder)

    panel.preset_buttons[1].click()
    panel.add_button.click()

    assert recorder.values == [(int(ActionIdEnum.PRESET_APPLY), "preset-30"), int(ActionIdEnum.PRESET_ADD)]


def test_presets_panel_follows_the_number_of_favorites(qtbot: QtBot) -> None:
    stack = TimerUiStack()
    panel = _presets_panel(qtbot, stack)

    stack.presets.presets = make_presets(5)
    panel.render_snapshot(stack.presets_snapshot)
    assert len(panel.preset_buttons) == 1

    stack.presets.presets = make_presets(5, 10, 20, 25)
    panel.render_snapshot(stack.presets_snapshot)
    assert [button.text() for button in panel.preset_buttons][-1] == "en:duration.label.minutes(minutes=25)"


def test_context_menu_opens_on_a_disabled_favorite_and_emits_its_actions(qtbot: QtBot) -> None:
    stack = TimerUiStack()
    panel = _presets_panel(qtbot, stack)
    panel.resize(400, 200)
    panel.show()
    recorder = Recorder()
    panel.preset_action_requested.connect(recorder)
    target = panel.preset_buttons[2]
    target.setEnabled(False)  # as during the cooldown after a click

    position = target.rect().center()
    event = QContextMenuEvent(QContextMenuEvent.Reason.Mouse, position, target.mapToGlobal(position))
    QApplication.sendEvent(target, event)

    menu = panel.last_menu
    assert menu is not None
    actions = menu.actions()
    assert [action.text() for action in actions] == ["en:action.preset_edit", "en:action.preset_delete"]
    actions[1].trigger()
    assert recorder.values == [(int(ActionIdEnum.PRESET_DELETE), "preset-45")]


def test_context_menu_outside_a_favorite_is_ignored(qtbot: QtBot) -> None:
    stack = TimerUiStack()
    panel = _presets_panel(qtbot, stack)
    panel.resize(400, 200)
    panel.show()

    for receiver in (panel, panel.add_button):
        position = receiver.rect().center()
        QApplication.sendEvent(
            receiver, QContextMenuEvent(QContextMenuEvent.Reason.Mouse, position, receiver.mapToGlobal(position))
        )

    assert panel.last_menu is None


def test_a_second_context_menu_replaces_the_first(qtbot: QtBot) -> None:
    stack = TimerUiStack()
    panel = _presets_panel(qtbot, stack)

    panel.show_menu(0, QPoint(0, 0))
    first = panel.last_menu
    panel.show_menu(1, QPoint(0, 0))

    assert panel.last_menu is not first
    assert panel.last_menu is not None
    assert [action.isEnabled() for action in panel.last_menu.actions()] == [True, True]


def test_special_options_panel_shows_the_switch_and_emits_on_click(qtbot: QtBot) -> None:
    stack = TimerUiStack()
    panel = SpecialOptionsPanel()
    qtbot.addWidget(panel)
    panel.render_snapshot(stack.chime_presenter.build_snapshot())
    recorder = Recorder()
    panel.action_requested.connect(recorder)

    panel.chime_check_box.click()
    panel.chime_edit_button.click()

    assert panel.chime_check_box.text() == "en:action.chime_toggle"
    assert panel.chime_hours.text().startswith("en:chime.hours")
    assert recorder.values == [int(ActionIdEnum.CHIME_TOGGLE), int(ActionIdEnum.CHIME_EDIT)]


def test_check_box_shows_the_stored_value_again_after_a_refused_click(qtbot: QtBot) -> None:
    stack = TimerUiStack()
    panel = SpecialOptionsPanel()
    qtbot.addWidget(panel)
    panel.render_snapshot(stack.chime_presenter.build_snapshot())

    panel.chime_check_box.click()
    assert panel.chime_check_box.isChecked()
    panel.render_snapshot(stack.chime_presenter.build_snapshot())

    assert not panel.chime_check_box.isChecked()


def test_favorite_dialog_adds_what_the_user_typed(qtbot: QtBot) -> None:
    stack = TimerUiStack(register_editor=False)
    window = PresetEditWindow(stack.preset_editor, stack.renderer, ScreenDialogRunner(), LAYOUT)
    qtbot.addWidget(window.dialog)
    stack.preset_editor.attach(window)
    panel = window.dialog.panel

    def act() -> None:
        QTest.keyClicks(panel.label_input, "Pomodoro")
        stack.scheduler.run_pending()
        stack.scheduler.advance(100)
        panel.save_button.click()

    QTimer.singleShot(0, act)
    stack.preset_action(ActionIdEnum.PRESET_ADD)

    assert [preset.label for preset in stack.presets.presets.ordered()][-1] == "Pomodoro"
    assert window.dialog.windowTitle() == "en:preset.edit.title.new"
    assert not window.dialog.isVisible()


def test_favorite_dialog_shows_the_duplicate_error_inline(qtbot: QtBot) -> None:
    stack = TimerUiStack(register_editor=False)
    window = PresetEditWindow(stack.preset_editor, stack.renderer, ScreenDialogRunner(), LAYOUT)
    qtbot.addWidget(window.dialog)
    stack.preset_editor.attach(window)
    panel = window.dialog.panel
    seen: list[tuple[bool, bool, str]] = []

    def act() -> None:
        panel.duration_input.spin_boxes[1].setValue(15)
        stack.scheduler.run_pending()
        seen.append(
            (
                panel.duration_error.isVisibleTo(window.dialog),
                panel.save_button.isEnabled(),
                panel.label_input.placeholderText(),
            )
        )
        window.dialog.reject()

    QTimer.singleShot(0, act)
    stack.preset_action(ActionIdEnum.PRESET_ADD)

    assert seen == [(True, False, "en:preset.edit.label_placeholder(label=en:duration.label.minutes(minutes=15))")]
    assert stack.presets.writes == 0


def test_favorite_dialog_keeps_the_cursor_while_typing(qtbot: QtBot) -> None:
    stack = TimerUiStack(register_editor=False)
    window = PresetEditWindow(stack.preset_editor, stack.renderer, ScreenDialogRunner(), LAYOUT)
    qtbot.addWidget(window.dialog)
    panel = window.dialog.panel
    stack.renderer.flush()

    QTest.keyClicks(panel.label_input, "Tea")
    panel.label_input.setCursorPosition(1)
    stack.scheduler.run_pending()

    assert panel.label_input.text() == "Tea"
    assert panel.label_input.cursorPosition() == 1
    assert panel.label_input.property(INVALID_PROPERTY) is False


def test_chime_dialog_saves_the_hours_and_volume(qtbot: QtBot) -> None:
    stack = TimerUiStack(register_editor=False)
    stack.catalog.builtin = (*stack.catalog.builtin, "chime")
    window = ChimeSettingsWindow(stack.chime_editor, stack.renderer, ScreenDialogRunner(), LAYOUT)
    qtbot.addWidget(window.dialog)
    stack.chime_editor.attach(window, stack.dialogs)
    panel = window.dialog.panel

    def act() -> None:
        panel.start_hour.setCurrentIndex(0)
        panel.end_hour.setCurrentIndex(23)
        panel.volume_slider.slider.setValue(30)
        stack.scheduler.run_pending()
        stack.scheduler.advance(100)
        panel.save_button.click()

    QTimer.singleShot(0, act)
    stack.options_action(ActionIdEnum.CHIME_EDIT)

    settings = stack.chime_queries.settings()
    assert (settings.start_hour, settings.end_hour, settings.volume) == (0, 23, Volume(30))
    assert window.dialog.windowTitle() == "en:chime.edit.title"
    assert panel.start_hour.count() == 24
    assert not window.dialog.isVisible()


def test_chime_dialog_marks_reversed_hours(qtbot: QtBot) -> None:
    stack = TimerUiStack(register_editor=False)
    window = ChimeSettingsWindow(stack.chime_editor, stack.renderer, ScreenDialogRunner(), LAYOUT)
    qtbot.addWidget(window.dialog)
    stack.chime_editor.attach(window, stack.dialogs)
    panel = window.dialog.panel
    seen: list[tuple[bool, bool]] = []

    def act() -> None:
        panel.start_hour.setCurrentIndex(22)
        stack.scheduler.run_pending()
        seen.append((panel.end_hour.property(INVALID_PROPERTY) is True, panel.save_button.isEnabled()))
        window.dialog.reject()

    QTimer.singleShot(0, act)
    stack.options_action(ActionIdEnum.CHIME_EDIT)

    assert seen == [(True, False)]
    assert stack.chime.updates == []
    assert stack.dialogs.calls == []


def test_zone_two_stacks_timer_favorites_and_options(qtbot: QtBot) -> None:
    harness = ShellHarness()
    qtbot.addWidget(harness.window)
    harness.window.resize(1400, 860)
    harness.window.show()

    timer = harness.window.timer_panel.geometry()
    presets = harness.window.presets_panel.geometry()
    options = harness.window.special_options_panel.geometry()

    assert timer.bottom() < presets.top() < options.top()
    assert len(harness.window.presets_panel.preset_buttons) == 3
    assert harness.window.special_options_panel.chime_check_box.text() == "en:action.chime_toggle"


def test_main_window_click_on_a_favorite_starts_the_timer(qtbot: QtBot) -> None:
    harness = ShellHarness()
    qtbot.addWidget(harness.window)
    harness.scheduler.advance(100)

    harness.window.presets_panel.preset_buttons[0].click()
    harness.turn()

    assert harness.timer.engine.session.state is TimerStateEnum.RUNNING
    assert harness.timer.engine.settings().duration == Duration(900)
    assert harness.window.timer_panel.digits.text() == "00:15:00"
    harness.scheduler.advance(100)
    harness.turn()
    assert harness.window.presets_panel.preset_buttons[1].isEnabled()
    harness.window.presets_panel.preset_buttons[1].click()
    harness.turn()
    assert harness.window.timer_panel.digits.text() == "00:30:00"


def test_main_window_chime_box_switches_the_chime(qtbot: QtBot) -> None:
    harness = ShellHarness()
    qtbot.addWidget(harness.window)
    harness.scheduler.advance(100)

    harness.window.special_options_panel.chime_check_box.click()
    harness.turn()

    assert harness.timer.chime_queries.enabled() is True
    assert harness.window.special_options_panel.chime_check_box.isChecked()


def test_favorite_dialog_shows_a_stored_label_and_cancel_closes_it(qtbot: QtBot) -> None:
    stack = TimerUiStack(register_editor=False)
    stack.presets.presets = TimerPresetsCollection((make_preset(25, label="Pomodoro"),))
    window = PresetEditWindow(stack.preset_editor, stack.renderer, ScreenDialogRunner(), LAYOUT)
    qtbot.addWidget(window.dialog)
    stack.preset_editor.attach(window)
    panel = window.dialog.panel
    seen: list[str] = []

    def act() -> None:
        seen.append(panel.label_input.text())
        panel.label_input.clear()
        QTest.keyClicks(panel.label_input, "x" * 41)
        stack.scheduler.run_pending()
        seen.append(panel.label_error.text())
        stack.scheduler.advance(100)
        panel.cancel_button.click()

    QTimer.singleShot(0, act)
    stack.preset_action(ActionIdEnum.PRESET_EDIT, "preset-25")

    assert seen == ["Pomodoro", "en:error.preset_label_too_long(max=40)"]
    assert window.dialog.windowTitle() == "en:preset.edit.title.edit"
    assert not window.dialog.isVisible()
    assert stack.presets.writes == 0
