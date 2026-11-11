"""Zone 1 of the main window and the TODO dialogs, on the offscreen platform."""

from datetime import date

import pytest
from PySide6.QtCore import QPoint, Qt, QTimer, QUrl
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialog, QMenu, QWidget
from pytestqt.qtbot import QtBot

from concentrator.application.todo.task_list_commands import ListValues
from concentrator.domain.common.multiline_text import MultilineText
from concentrator.domain.todo.priority_enum import PriorityEnum
from concentrator.domain.todo.task_draft import TaskDraft
from concentrator.domain.todo.task_sort_key_enum import TaskSortKeyEnum
from concentrator.domain.todo.task_state_enum import TaskStateEnum
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.table_snapshot import CellLinkSnapshot
from concentrator.presentation.todo.task_details_snapshot import TextLineSnapshot
from concentrator.presentation.todo.todo_layout import TodoLayout
from concentrator.ui.support.modal_host import ScreenDialogRunner
from concentrator.ui.widgets.link_text_browser import LinkTextBrowser, lines_html
from concentrator.ui.widgets.link_text_delegate import shown_length, visible_links
from concentrator.ui.windows.todo_edit_dialogs import ListEditWindow, TaskEditWindow
from tests.fakes.todo_factory import HOME_LIST_ID, WORK_LIST_ID, make_task
from tests.fakes.todo_ui_stack import TodoUiStack
from tests.ui.shell_harness import ShellHarness

pytestmark = pytest.mark.ui

LAYOUT = TodoLayout(
    table_ratio_percent=75,
    column_widths_px=(60, 40, 120, 140, 130, 50, 50, 140, 140),
    text_width_percent=80,
    spacing_px=10,
)


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
    assert [table.model.index(row, 2).data() for row in range(3)] == ["third", "second", "first"]
    assert table.model.headerData(2, Qt.Orientation.Horizontal) == "en:todo.column.task"


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

    table.table.horizontalHeader().sectionClicked.emit(2)
    _settle(harness)

    assert [table.model.index(row, 2).data() for row in range(2)] == ["a", "b"]
    assert table.table.horizontalHeader().sortIndicatorSection() == 2


def test_reset_columns_keeps_the_task_column_stretching(harness: ShellHarness) -> None:
    _add(harness, "a")
    table = harness.window.focus_page.table_panel
    header = table.table.horizontalHeader()
    header.moveSection(0, 3)

    table.reset_columns()

    assert [header.logicalIndex(visual) for visual in range(header.count())] == list(range(10))
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

    shortcut = harness.window.focus_page.new_task_shortcut
    assert shortcut.context() is Qt.ShortcutContext.WidgetWithChildrenShortcut
    shortcut.activated.emit()
    _settle(harness)
    assert harness.todo.task_window.shows == 2

    QTest.keyClick(table, Qt.Key.Key_Delete)
    _settle(harness)
    assert [task.text.first_line for task in harness.todo.tasks()] == ["Report"]
    assert harness.stack.dialogs.texts("confirm")[-1][1] == "en:todo.delete_tasks.message.one(count=1)"


def test_a_tab_click_ignored_during_the_cooldown_keeps_the_tab_of_the_list_shown(harness: ShellHarness) -> None:
    bar = harness.window.focus_page.tabs_panel.tab_bar
    bar.setCurrentIndex(1)
    harness.turn()

    bar.setCurrentIndex(0)
    harness.turn()

    assert harness.todo.state.list_id == HOME_LIST_ID
    assert bar.currentIndex() == 1


def test_an_ampersand_in_a_list_name_is_shown_as_typed(harness: ShellHarness) -> None:
    harness.todo.list_commands.create(ListValues(name="R&D", description=MultilineText(), priority=PriorityEnum.URGENT))
    _add(harness, "Report")
    page = harness.window.focus_page
    page.table_panel.table.selectRow(0)
    harness.turn()

    assert (
        page.tabs_panel.tab_bar.tabText(0)
        == "en:todo.tab.text_no_open(badge=en:todo.priority.badge.urgent,name=R&&D,count=0)"
    )
    move_menu = page.toolbar_panel.move_button.menu()
    assert move_menu is not None
    assert "R&&D" in [action.text() for action in move_menu.actions()]


def test_a_header_click_ignored_during_the_cooldown_keeps_the_indicator_of_the_order(
    harness: ShellHarness, qtbot: QtBot
) -> None:
    _add(harness, "b", "a")
    harness.window.show()
    qtbot.waitExposed(harness.window)
    header = harness.window.focus_page.table_panel.table.horizontalHeader()

    def click(section: int) -> None:
        position = QPoint(header.sectionViewportPosition(section) + 5, 5)
        QTest.mouseClick(header.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, position)
        harness.turn()

    click(2)
    click(3)

    assert harness.todo.state.sort_key is TaskSortKeyEnum.TEXT
    assert (header.sortIndicatorSection(), header.sortIndicatorOrder()) == (2, Qt.SortOrder.AscendingOrder)


def test_a_tab_tooltip_shows_html_of_a_description_as_typed(harness: ShellHarness) -> None:
    harness.todo.list_commands.update(
        WORK_LIST_ID,
        ListValues(name="Work", description=MultilineText(("<b>bold</b>", "x")), priority=PriorityEnum.HIGH),
    )
    harness.turn()

    tooltip = harness.window.focus_page.tabs_panel.tab_bar.tabToolTip(0)

    assert "&lt;b&gt;bold&lt;/b&gt;" in tooltip
    assert "<b>" not in tooltip


def test_filter_bar_narrows_the_table_and_shows_the_counter(harness: ShellHarness) -> None:
    harness.todo.task_commands.quick_add(WORK_LIST_ID, "État des lieux")
    _add(harness, "Groceries")
    filters = harness.window.focus_page.filter_panel
    table = harness.window.focus_page.table_panel

    QTest.keyClicks(filters.search_box, "etat")
    harness.scheduler.advance(150)
    _settle(harness)

    assert table.model.rowCount() == 1
    assert filters.counter_label.text() == "en:todo.filter.counter.other(count=2,shown=1)"
    assert table.table.isColumnHidden(3)

    filters.scope_box.setCurrentIndex(1)
    _settle(harness)

    assert not table.table.isColumnHidden(3)
    assert filters.scope_box.currentIndex() == 1


def test_filter_bar_due_filter_and_recurring_toggle(harness: ShellHarness) -> None:
    _add(harness, "No date")
    filters = harness.window.focus_page.filter_panel
    table = harness.window.focus_page.table_panel

    filters.due_box.setCurrentIndex(5)
    _settle(harness)
    assert table.model.rowCount() == 0

    filters.due_box.setCurrentIndex(6)
    _settle(harness)
    assert table.model.rowCount() == 1

    filters.recurring_box.click()
    _settle(harness)
    assert table.model.rowCount() == 0
    assert filters.recurring_box.isChecked()


def test_task_dialog_saves_a_weekly_repetition(qtbot: QtBot) -> None:
    stack = TodoUiStack(register_editors=False)
    window = TaskEditWindow(stack.task_editor, stack.renderer, ScreenDialogRunner(), LAYOUT)
    qtbot.addWidget(window.dialog)
    stack.task_editor.attach(window, stack.dialogs)
    panel = window.dialog.panel
    repeat = panel.recurrence_panel
    seen: dict[str, object] = {}

    def act() -> None:
        QTest.keyClicks(panel.text_input, "Backup")
        panel.date_inputs[0].setChecked(True)
        repeat.repeat_box.setChecked(True)
        stack.scheduler.run_pending()
        seen["visible"] = not repeat.weekday_input.isHidden()
        seen["checked"] = [button.isChecked() for button in repeat.weekday_input.buttons]
        repeat.weekday_input.buttons[0].click()
        repeat.interval_input.setValue(2)
        end, _end_date, end_count = repeat.end_inputs
        end.setCurrentIndex(2)
        stack.scheduler.run_pending()
        end_count.setValue(4)
        stack.scheduler.run_pending()
        seen["count_visible"] = not end_count.isHidden()
        seen["summary"] = repeat.texts[0].text()
        panel.buttons[0].click()

    QTimer.singleShot(0, act)
    stack.task_editor.open_new(WORK_LIST_ID)

    recurrence = stack.tasks().items[0].recurrence
    assert recurrence is not None
    assert (recurrence.interval, recurrence.end_count) == (2, 4)
    assert [int(day) for day in recurrence.weekdays] == [1, 5]
    assert seen["visible"] is True
    assert seen["checked"] == [False, False, False, False, True, False, False]
    assert seen["count_visible"] is True
    assert str(seen["summary"]).startswith("en:todo.recurrence.times.other(")


def test_link_text_browser_escapes_text_and_sends_the_link_number(qtbot: QtBot) -> None:
    browser = LinkTextBrowser()
    qtbot.addWidget(browser)
    lines = (
        TextLineSnapshot(text="<b>not bold</b> & co"),
        TextLineSnapshot(text="  - D:/My folder", link_start=4, link_end=16, link_index=2),
    )
    clicked: list[int] = []
    browser.link_activated.connect(clicked.append)

    browser.set_lines(lines)
    browser.set_lines(lines)
    browser.anchorClicked.emit(QUrl("link:2"))
    browser.anchorClicked.emit(QUrl("https://example.org"))

    assert browser.toPlainText() == "<b>not bold</b> & co\n  - D:/My folder"
    assert '<a href="link:2">D:/My folder</a>' in lines_html(lines)
    assert "&lt;b&gt;" in lines_html(lines)
    assert clicked == [2]


def test_table_link_click_and_open_link_menu_reach_the_opener(harness: ShellHarness) -> None:
    harness.todo.task_commands.quick_add(WORK_LIST_ID, "https://example.org/a-rather-long-address\nC:/Windows")
    harness.turn()
    page = harness.window.focus_page
    table = page.table_panel
    table.table.resize(900, 300)
    table.table.setColumnWidth(2, 600)
    rect = table.table.visualRect(table.model.index(0, 2))

    QTest.mouseClick(
        table.table.viewport(), Qt.MouseButton.LeftButton, pos=rect.center() - QPoint(rect.width() // 2 - 12, 0)
    )
    _settle(harness)
    table.show_menu(QPoint(0, 0))
    menu = table.last_menu
    assert menu is not None
    submenu = next(action.menu() for action in menu.actions() if action.text() == "en:action.link_open")
    assert isinstance(submenu, QMenu)
    assert [action.text() for action in submenu.actions()] == [
        "https://example.org/a-rather-long-address",
        "C:/Windows",
    ]
    submenu.actions()[1].trigger()
    _settle(harness)

    targets = [target.value for target in harness.todo.opener.links]
    assert targets == ["https://example.org/a-rather-long-address", "C:/Windows"]


def test_details_and_history_tabs_follow_the_selection(harness: ShellHarness) -> None:
    _add(harness, "Report\nC:/Reports")
    page = harness.window.focus_page
    page.table_panel.table.selectRow(0)
    _settle(harness)

    assert page.info_tabs.tabText(0) == "en:todo.details.title"
    assert page.info_tabs.tabText(1) == "en:todo.history.title"
    assert len(page.history_panel.lines) == 1
    assert page.details_panel.text == "Report\nC:/Reports"
    page.details_panel.browser.anchorClicked.emit(QUrl("link:0"))
    _settle(harness)
    assert [target.value for target in harness.todo.opener.links] == ["C:/Reports"]


def test_shown_length_cuts_a_text_wider_than_the_limit(qtbot: QtBot) -> None:
    widget = QWidget()
    qtbot.addWidget(widget)
    metrics = widget.fontMetrics()
    text = "word " * 40

    cut = shown_length(text, metrics, metrics.horizontalAdvance(text[:30]))

    assert shown_length("short", metrics, 1000) == len("short")
    assert cut == 30
    assert shown_length(text, metrics, 0) == 0


def test_visible_links_end_at_the_cut() -> None:
    links = (
        CellLinkSnapshot(column=1, start=0, end=10, index=0),
        CellLinkSnapshot(column=1, start=20, end=30, index=1),
    )

    assert visible_links(links, 5) == (CellLinkSnapshot(column=1, start=0, end=5, index=0),)
    assert visible_links(links, 40) == links


def test_long_task_text_is_cut_and_a_link_after_the_cut_is_not_clickable(harness: ShellHarness) -> None:
    long_line = "a rather long first line " * 8
    harness.todo.task_commands.quick_add(WORK_LIST_ID, f"{long_line}\nhttps://example.org")
    harness.turn()
    table = harness.window.focus_page.table_panel
    table.table.resize(900, 300)
    table.table.setColumnWidth(2, 300)
    harness.window.show()
    table.table.viewport().grab()
    rect = table.table.visualRect(table.model.index(0, 2))

    QTest.mouseClick(table.table.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(rect.right() - 5, rect.center().y()))
    _settle(harness)

    assert harness.todo.opener.links == []
    assert table.model.rows[0].overflow == "en:todo.table.overflow.other(count=2)"
