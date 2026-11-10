"""Zone 1 of the main window and the TODO dialogs, on the offscreen platform."""

from datetime import date

import pytest
from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialog, QMenu
from pytestqt.qtbot import QtBot

from concentrator.domain.common.multiline_text import MultilineText
from concentrator.domain.todo.task_draft import TaskDraft
from concentrator.domain.todo.task_state_enum import TaskStateEnum
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.todo.todo_layout import TodoLayout
from concentrator.ui.support.modal_host import ScreenDialogRunner
from concentrator.ui.windows.todo_edit_dialogs import ListEditWindow, TaskEditWindow
from tests.fakes.todo_factory import HOME_LIST_ID, WORK_LIST_ID, make_task
from tests.fakes.todo_ui_stack import TodoUiStack
from tests.ui.shell_harness import ShellHarness

pytestmark = pytest.mark.ui

LAYOUT = TodoLayout(table_ratio_percent=75, column_widths_px=(60, 140, 140, 140), spacing_px=10)


@pytest.fixture
def harness(qtbot: QtBot) -> ShellHarness:
    built = ShellHarness()
    qtbot.addWidget(built.window)
    return built


def _add(harness: ShellHarness, *texts: str) -> None:
    for text in texts:
        harness.todo.task_commands.quick_add(WORK_LIST_ID, text)
    harness.turn()


def _settle(harness: ShellHarness) -> None:
    harness.turn()
    harness.stack.clock.advance(ms=200)
    harness.scheduler.advance(200)
    harness.turn()


def test_table_with_three_rows_renders_them_newest_first(harness: ShellHarness) -> None:
    _add(harness, "first", "second", "third")
    table = harness.window.focus_page.table_panel

    assert table.model.rowCount() == 3
    assert [table.model.index(row, 1).data() for row in range(3)] == ["third", "second", "first"]
    assert table.model.headerData(1, Qt.Orientation.Horizontal) == "en:todo.column.task"


def test_check_box_click_completes_the_right_task(harness: ShellHarness) -> None:
    _add(harness, "first", "second")
    model = harness.window.focus_page.table_panel.model
    index = model.index(1, 0)

    assert model.flags(index) & Qt.ItemFlag.ItemIsUserCheckable
    model.setData(index, Qt.CheckState.Checked.value, Qt.ItemDataRole.CheckStateRole)
    _settle(harness)

    states = {task.text.first_line: task.state for task in harness.todo.tasks()}
    assert states == {"first": TaskStateEnum.DONE, "second": TaskStateEnum.OPEN}
    assert model.index(1, 0).data(Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Checked


def test_tab_bar_renders_names_badges_and_follows_a_click(harness: ShellHarness) -> None:
    tabs = harness.window.focus_page.tabs_panel

    assert [tabs.tab_bar.tabText(index) for index in range(tabs.tab_bar.count())] == [
        "en:todo.tab.text_no_open(badge=en:todo.priority.badge.high,name=Work,count=0)",
        "en:todo.tab.text_no_open(badge=,name=Home,count=0)",
    ]
    tabs.tab_bar.setCurrentIndex(1)
    _settle(harness)

    assert harness.todo.state.list_id == HOME_LIST_ID
    tabs.show_menu(0, QPoint(0, 0))
    menu = tabs.last_menu
    assert menu is not None
    assert [action.text() for action in menu.actions()] == [
        "en:action.list_edit",
        "en:action.list_move_earlier",
        "en:action.list_move_later",
        "en:action.list_delete",
    ]


def test_quick_add_field_adds_the_task_on_enter_and_empties(harness: ShellHarness) -> None:
    field = harness.window.focus_page.quick_add_panel.input

    QTest.keyClicks(field, "Call the bank")
    QTest.keyClick(field, Qt.Key.Key_Return)
    harness.turn()

    assert [task.text.first_line for task in harness.todo.tasks()] == ["Call the bank"]
    assert not field.text()
    assert harness.window.focus_page.table_panel.model.rowCount() == 1


def test_selection_enables_the_toolbar_and_fills_the_details(harness: ShellHarness) -> None:
    _add(harness, "Report")
    page = harness.window.focus_page
    page.table_panel.table.selectRow(0)
    harness.turn()

    assert page.toolbar_panel.buttons[ActionIdEnum.TASK_EDIT].isEnabled()
    assert page.toolbar_panel.move_button.isEnabled()
    assert page.details_panel.text == "Report"
    assert page.details_panel.values[0] == "Work"


def test_context_menu_shows_the_task_actions_and_the_move_submenu(harness: ShellHarness) -> None:
    _add(harness, "Report")
    table = harness.window.focus_page.table_panel
    table.table.selectRow(0)
    harness.turn()

    table.show_menu(QPoint(0, 0))
    menu = table.last_menu
    assert menu is not None
    move = next(action for action in menu.actions() if action.text() == "en:action.task_move")
    submenu = move.menu()
    assert isinstance(submenu, QMenu)
    submenu.actions()[0].trigger()
    _settle(harness)

    assert harness.todo.tasks().items[0].list_id == HOME_LIST_ID


def test_toolbar_toggles_hide_done_tasks(harness: ShellHarness) -> None:
    _add(harness, "Report")
    page = harness.window.focus_page
    page.table_panel.table.selectRow(0)
    harness.turn()
    page.toolbar_panel.buttons[ActionIdEnum.TASK_COMPLETE].click()
    _settle(harness)

    show_done, _show_archived = page.toolbar_panel.toggles
    show_done.click()
    _settle(harness)

    assert page.table_panel.model.rowCount() == 0
    assert harness.preferences.values["layout/todo/show_done"] == "0"


def test_header_click_sorts_and_shows_the_indicator(harness: ShellHarness) -> None:
    _add(harness, "b", "a")
    table = harness.window.focus_page.table_panel

    table.table.horizontalHeader().sectionClicked.emit(1)
    _settle(harness)

    assert [table.model.index(row, 1).data() for row in range(2)] == ["a", "b"]
    assert table.table.horizontalHeader().sortIndicatorSection() == 1


def test_reset_columns_keeps_the_task_column_stretching(harness: ShellHarness) -> None:
    _add(harness, "a")
    table = harness.window.focus_page.table_panel
    header = table.table.horizontalHeader()
    header.moveSection(0, 3)

    table.reset_columns()

    assert [header.logicalIndex(visual) for visual in range(header.count())] == [0, 1, 2, 3, 4]
    assert header.sectionSize(0) == LAYOUT.column_widths_px[0]


def test_task_dialog_creates_a_task_with_a_due_date(qtbot: QtBot) -> None:
    stack = TodoUiStack(register_editors=False)
    window = TaskEditWindow(stack.task_editor, stack.renderer, ScreenDialogRunner(), LAYOUT)
    qtbot.addWidget(window.dialog)
    stack.task_editor.attach(window, stack.dialogs)
    panel = window.dialog.panel

    def act() -> None:
        QTest.keyClicks(panel.text_input, "Report")
        has_date, _date_edit = panel.date_inputs
        has_date.setChecked(True)
        stack.scheduler.run_pending()
        save, _cancel = panel.buttons
        save.click()

    QTimer.singleShot(0, act)
    stack.task_editor.open_new(WORK_LIST_ID)

    task = stack.tasks().items[0]
    assert (task.text.first_line, task.due_date) == ("Report", date(2026, 11, 6))
    assert window.dialog.windowTitle() == "en:todo.task_edit.title.new"
    assert not window.dialog.isVisible()


def test_escape_on_a_changed_task_dialog_asks_before_closing(qtbot: QtBot) -> None:
    stack = TodoUiStack(tasks=[make_task(1)], register_editors=False)
    window = TaskEditWindow(stack.task_editor, stack.renderer, ScreenDialogRunner(), LAYOUT)
    qtbot.addWidget(window.dialog)
    stack.task_editor.attach(window, stack.dialogs)
    panel = window.dialog.panel

    def act() -> None:
        QTest.keyClicks(panel.text_input, " changed")
        stack.scheduler.run_pending()
        window.dialog.reject()

    QTimer.singleShot(0, act)
    stack.task_editor.open_edit("task-001")

    assert stack.dialogs.texts("confirm")[0][1] == "en:todo.discard.message"
    assert window.dialog.result() == QDialog.DialogCode.Accepted
    assert stack.task("task-001").text.first_line == "Task 1"


def test_task_dialog_shows_the_time_field_only_with_a_date(qtbot: QtBot) -> None:
    stack = TodoUiStack(register_editors=False)
    stack.task_commands.create(
        TaskDraft(list_id=WORK_LIST_ID, text=MultilineText.from_text("a"), due_date=date(2026, 11, 9))
    )
    window = TaskEditWindow(stack.task_editor, stack.renderer, ScreenDialogRunner(), LAYOUT)
    qtbot.addWidget(window.dialog)
    stack.task_editor.attach(window, stack.dialogs)
    task_id = stack.tasks().items[0].id
    seen: list[tuple[bool, bool]] = []

    def act() -> None:
        has_time, time_edit = window.dialog.panel.time_inputs
        seen.append((has_time.isEnabled(), time_edit.isEnabled()))
        window.dialog.reject()

    QTimer.singleShot(0, act)
    stack.task_editor.open_edit(task_id)

    assert seen == [(True, False)]


def test_list_dialog_creates_a_list(qtbot: QtBot) -> None:
    stack = TodoUiStack(register_editors=False)
    window = ListEditWindow(stack.list_editor, stack.renderer, ScreenDialogRunner(), LAYOUT)
    qtbot.addWidget(window.dialog)
    stack.list_editor.attach(window, stack.dialogs)
    panel = window.dialog.panel

    def act() -> None:
        QTest.keyClicks(panel.name_input, "Ideas")
        QTest.keyClicks(panel.description_input, "Later")
        panel.priority_input.setCurrentIndex(0)
        stack.scheduler.run_pending()
        save, _cancel = panel.buttons
        save.click()

    QTimer.singleShot(0, act)
    stack.list_editor.open_new()

    created = next(item for item in stack.lists() if item.name == "Ideas")
    assert created.description.lines == ("Later",)
    assert stack.state.list_id == created.id
    assert not window.dialog.isVisible()


def test_list_dialog_shows_the_duplicate_error(qtbot: QtBot) -> None:
    stack = TodoUiStack(register_editors=False)
    window = ListEditWindow(stack.list_editor, stack.renderer, ScreenDialogRunner(), LAYOUT)
    qtbot.addWidget(window.dialog)
    stack.list_editor.attach(window, stack.dialogs)
    panel = window.dialog.panel
    seen: list[str] = []

    def act() -> None:
        QTest.keyClicks(panel.name_input, "work")
        stack.scheduler.run_pending()
        seen.append(panel.name_error.text())
        window.dialog.reject()

    QTimer.singleShot(0, act)
    stack.list_editor.open_new()

    assert seen == ["en:error.list_name_duplicate"]


def test_keyboard_toggles_deletes_and_opens_the_selected_task(harness: ShellHarness, qtbot: QtBot) -> None:
    _add(harness, "Report", "Call")
    harness.window.show()
    qtbot.waitExposed(harness.window)
    table = harness.window.focus_page.table_panel.table
    table.setFocus()
    table.selectRow(0)
    harness.turn()

    QTest.keyClick(table, Qt.Key.Key_Space)
    _settle(harness)
    assert {task.state for task in harness.todo.tasks() if task.text.first_line == "Call"} == {TaskStateEnum.DONE}

    QTest.keyClick(table, Qt.Key.Key_Return)
    _settle(harness)
    assert harness.todo.task_window.shows == 1

    QTest.keyClick(table, Qt.Key.Key_N, Qt.KeyboardModifier.ControlModifier)
    _settle(harness)
    assert harness.todo.task_window.shows == 2

    QTest.keyClick(table, Qt.Key.Key_Delete)
    _settle(harness)
    assert [task.text.first_line for task in harness.todo.tasks()] == ["Report"]
    assert harness.stack.dialogs.texts("confirm")[-1][1] == "en:todo.delete_tasks.message.one(count=1)"
