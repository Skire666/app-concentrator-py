"""Focus queue of zone 2 and the star of the task table, on the offscreen platform."""

from dataclasses import replace

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from pytestqt.qtbot import QtBot

from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.button_snapshot import ButtonSnapshot
from concentrator.presentation.common.row_tone_enum import RowToneEnum
from concentrator.presentation.common.table_snapshot import TableRowSnapshot, TableSnapshot
from concentrator.presentation.focus.focus_queue_snapshot import (
    FocusFieldSnapshot,
    FocusRowSnapshot,
    PickerChoiceSnapshot,
)
from concentrator.presentation.todo.task_menu_snapshot import TaskMenuSnapshot
from concentrator.presentation.todo.task_table_snapshot import TaskTableSnapshot
from concentrator.ui.panels.task_table_panel import TaskTablePanel
from concentrator.ui.widgets.focus_row_widget import FocusRowWidget
from concentrator.ui.widgets.task_picker_widget import TaskPickerWidget
from tests.fakes.todo_factory import WORK_LIST_ID
from tests.ui.shell_harness import ShellHarness

pytestmark = pytest.mark.ui


@pytest.fixture
def harness(qtbot: QtBot) -> ShellHarness:
    built = ShellHarness()
    qtbot.addWidget(built.window)
    return built


def _settle(harness: ShellHarness) -> None:
    harness.turn()
    harness.stack.clock.advance(ms=200)
    harness.scheduler.advance(200)
    harness.turn()


def _add(harness: ShellHarness, *texts: str) -> list[str]:
    ids: list[str] = []
    for text in texts:
        created = harness.todo.task_commands.quick_add(WORK_LIST_ID, text).data
        assert created is not None
        ids.append(created.id)
    harness.turn()
    return ids


def _button(action: ActionIdEnum, *, enabled: bool = True) -> ButtonSnapshot:
    return ButtonSnapshot(text=action.name, tooltip="", enabled=enabled, visible=True, action=action)


def _row(*, tone: RowToneEnum = RowToneEnum.NORMAL) -> FocusRowSnapshot:
    return FocusRowSnapshot(
        item_id="item-1",
        text="Report",
        tooltip="Report",
        list_name="Work",
        due_text="06/11/2026",
        tone=tone,
        complete=_button(ActionIdEnum.FOCUS_COMPLETE),
        remove=_button(ActionIdEnum.FOCUS_REMOVE),
        menu=(
            _button(ActionIdEnum.FOCUS_MOVE_UP, enabled=False),
            _button(ActionIdEnum.FOCUS_MOVE_DOWN),
            _button(ActionIdEnum.FOCUS_SHOW_IN_LIST),
        ),
    )


def test_star_queues_a_task_and_the_queue_renders_its_row(harness: ShellHarness) -> None:
    (task_id,) = _add(harness, "Report")
    page = harness.window.focus_page
    table = page.table_panel
    queue = page.focus_queue_panel
    assert queue.empty_label.isVisibleTo(queue)

    table.table.clicked.emit(table.model.index(0, 1))
    _settle(harness)

    assert harness.todo.focus.queued() == [task_id]
    assert table.model.index(0, 1).data() == "en:todo.table.focus_on"
    assert [row.text_label.text() for row in queue.rows] == ["Report"]
    assert queue.capacity_label.text() == "en:focus.capacity(count=1,max=20)"
    assert not queue.empty_label.isVisibleTo(queue)


def test_a_click_on_another_column_or_a_closed_task_star_does_nothing(harness: ShellHarness) -> None:
    (task_id,) = _add(harness, "Report")
    harness.todo.task_commands.complete([task_id])
    _settle(harness)
    table = harness.window.focus_page.table_panel

    table.table.clicked.emit(table.model.index(0, 2))
    table.table.clicked.emit(table.model.index(0, 1))
    _settle(harness)

    assert harness.todo.focus.queued() == []


def test_check_box_of_a_row_completes_the_task(harness: ShellHarness) -> None:
    (task_id,) = _add(harness, "Report")
    harness.todo.focus.commands.add_tasks([task_id])
    _settle(harness)
    queue = harness.window.focus_page.focus_queue_panel

    queue.rows[0].check_box.click()
    _settle(harness)

    assert harness.todo.task(task_id).state.name == "DONE"
    assert queue.rows == ()


def test_remove_button_and_menu_reach_the_presenter(harness: ShellHarness) -> None:
    first, second = _add(harness, "first", "second")
    harness.todo.focus.commands.add_tasks([first, second])
    _settle(harness)
    queue = harness.window.focus_page.focus_queue_panel

    queue.show_menu(0, QPoint(0, 0))
    menu = queue.last_menu
    assert menu is not None
    assert [action.isEnabled() for action in menu.actions()] == [False, True, True]
    menu.actions()[1].trigger()
    _settle(harness)
    assert harness.todo.focus.queued() == [second, first]

    queue.rows[0].remove_button.click()
    _settle(harness)
    assert harness.todo.focus.queued() == [first]


def test_picker_and_quick_add_fields_queue_tasks(harness: ShellHarness) -> None:
    (task_id,) = _add(harness, "Report")
    queue = harness.window.focus_page.focus_queue_panel

    QTest.keyClicks(queue.picker.input, "rep")
    _settle(harness)
    assert queue.picker.completer.model().rowCount() == 1
    QTest.keyClick(queue.picker.input, Qt.Key.Key_Return)
    _settle(harness)
    QTest.keyClicks(queue.quick_add_input, "Call the bank")
    QTest.keyClick(queue.quick_add_input, Qt.Key.Key_Return)
    _settle(harness)

    assert harness.todo.focus.queued()[0] == task_id
    assert len(harness.todo.focus.queued()) == 2
    assert (queue.picker.input.text(), queue.quick_add_input.text()) == ("", "")
    assert not queue.error_text


def test_a_full_queue_shows_the_message_under_the_fields(harness: ShellHarness) -> None:
    ids = _add(harness, *(f"task {number}" for number in range(21)))
    harness.todo.focus.commands.add_tasks(ids[:20])
    _settle(harness)
    table = harness.window.focus_page.table_panel
    row = next(index for index, entry in enumerate(table.model.rows) if entry.key == ids[20])

    table.table.clicked.emit(table.model.index(row, 1))
    _settle(harness)

    assert harness.window.focus_page.focus_queue_panel.error_text == "en:error.focus_queue_full(max=20)"


def test_row_widget_shows_the_tone_and_moves_with_alt_arrows(qtbot: QtBot) -> None:
    widget = FocusRowWidget()
    qtbot.addWidget(widget)
    actions: list[int] = []
    widget.action_requested.connect(actions.append)
    widget.apply(_row(tone=RowToneEnum.ERROR))

    QTest.keyClick(widget, Qt.Key.Key_Up, Qt.KeyboardModifier.AltModifier)
    QTest.keyClick(widget, Qt.Key.Key_Down, Qt.KeyboardModifier.AltModifier)
    QTest.keyClick(widget, Qt.Key.Key_Down)

    assert actions == [int(ActionIdEnum.FOCUS_MOVE_DOWN)]
    assert widget.text_label.property("alert") is True
    assert widget.due_label.text() == "06/11/2026"
    assert widget.item_id == "item-1"


def test_picker_widget_emits_the_task_of_the_current_entry(qtbot: QtBot) -> None:
    widget = TaskPickerWidget()
    qtbot.addWidget(widget)
    picked: list[str] = []
    widget.picked.connect(picked.append)
    field = FocusFieldSnapshot(text="re", placeholder="Search", tooltip="", cleared_count=0)
    choices = (PickerChoiceSnapshot(task_id="t1", text="Report"), PickerChoiceSnapshot(task_id="t2", text="Read"))
    widget.apply(field, choices)
    widget.apply(field, choices)

    popup = widget.completer.popup()
    assert popup is not None
    popup.setCurrentIndex(widget.completer.completionModel().index(1, 0))
    widget.completer.activated.emit("Read")
    QTest.keyClick(widget.input, Qt.Key.Key_Return)
    widget.apply(field, ())
    QTest.keyClick(widget.input, Qt.Key.Key_Return)

    assert picked == ["t2", "t1"]


def test_enter_on_a_highlighted_entry_picks_only_that_entry(qtbot: QtBot) -> None:
    widget = TaskPickerWidget()
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)
    widget.input.setFocus()
    picked: list[str] = []
    widget.picked.connect(picked.append)
    field = FocusFieldSnapshot(text="re", placeholder="Search", tooltip="", cleared_count=0)
    widget.apply(
        field, (PickerChoiceSnapshot(task_id="t1", text="Report"), PickerChoiceSnapshot(task_id="t2", text="Read"))
    )
    widget.completer.complete()
    popup = widget.completer.popup()
    assert popup is not None
    assert popup.isVisible()

    QTest.keyClick(popup, Qt.Key.Key_Down)
    QTest.keyClick(popup, Qt.Key.Key_Down)
    QTest.keyClick(popup, Qt.Key.Key_Return)

    assert picked == ["t2"]


def _table(keys: list[str], selected: int) -> TaskTableSnapshot:
    rows = tuple(TableRowSnapshot(key=key, cells=("", "", key)) for key in keys)
    table = TableSnapshot(columns=("a", "b", "c"), rows=rows, selection=(keys.index(f"t{selected:03d}"),))
    return TaskTableSnapshot(table=table, menu=TaskMenuSnapshot(buttons=(), move_targets=()))


def test_table_keeps_its_scroll_after_a_reset_and_scrolls_to_a_new_selection(qtbot: QtBot) -> None:
    panel = TaskTablePanel((60, 40, 120, 140, 130, 50, 50, 140, 140), 80)
    qtbot.addWidget(panel)
    panel.resize(400, 200)
    panel.show()
    keys = [f"t{number:03d}" for number in range(100)]
    panel.render_snapshot(_table(keys, 0))
    bar = panel.table.verticalScrollBar()
    bar.setValue(bar.maximum())

    panel.render_snapshot(_table([key for key in keys if key != "t050"], 0))
    kept = bar.value()
    panel.render_snapshot(_table([key for key in keys if key != "t050"], 99))

    assert kept > bar.maximum() // 2
    assert panel.table.rowAt(panel.table.viewport().height() // 2) > 80
    panel.render_snapshot(_table([key for key in keys if key != "t050"], 1))
    assert panel.table.rowAt(0) <= 1


def test_row_tooltip_shows_html_of_a_task_as_typed(qtbot: QtBot) -> None:
    widget = FocusRowWidget()
    qtbot.addWidget(widget)

    widget.apply(replace(_row(), tooltip="<b>Fix</b> layout\nList: Work"))

    assert "&lt;b&gt;Fix&lt;/b&gt; layout" in widget.text_label.toolTip()
