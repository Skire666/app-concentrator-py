from collections.abc import Iterable
from datetime import date, time, timedelta
from pathlib import Path

import pytest

from concentrator.application.storage.storage_events import UserDataReplacedEvent
from concentrator.domain.todo.priority_enum import PriorityEnum
from concentrator.domain.todo.task import Task
from concentrator.domain.todo.task_state_enum import TaskStateEnum
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.button_snapshot import ButtonSnapshot
from concentrator.presentation.common.row_tone_enum import RowToneEnum
from concentrator.presentation.todo.task_menu_snapshot import TaskMenuSnapshot
from tests.fakes.todo_factory import HOME_LIST_ID, WORK_LIST_ID, make_list, make_task
from tests.fakes.todo_ui_stack import TodoUiStack

TODAY = date(2026, 11, 6)
"""Local date of ``FakeClock`` (2026-11-06 10:00 at UTC+1)."""


def _button(menu: TaskMenuSnapshot, action: ActionIdEnum) -> ButtonSnapshot:
    return next(button for button in menu.buttons if button.action is action)


def _enabled(menu: TaskMenuSnapshot) -> set[ActionIdEnum]:
    return {button.action for button in menu.buttons if button.enabled}


def _stack(*tasks: Task) -> TodoUiStack:
    stack = TodoUiStack(tasks=tasks)
    stack.renderer.request_all()
    stack.settle()
    return stack


def test_tabs_follow_priority_show_badges_counts_and_the_description() -> None:
    stack = TodoUiStack(
        lists=[
            make_list("Ideas", priority=PriorityEnum.LOW, position=0),
            make_list("Work", priority=PriorityEnum.HIGH, position=1, description="Clients\nAdmin"),
            make_list("Home", position=2),
        ],
        tasks=[make_task(1), make_task(2, state=TaskStateEnum.DONE)],
    )

    snapshot = stack.tabs.build_snapshot()

    assert [tab.text for tab in snapshot.tabs] == [
        "en:todo.tab.text(badge=en:todo.priority.badge.high,name=Work,count=1)",
        "en:todo.tab.text_no_open(badge=,name=Home,count=0)",
        "en:todo.tab.text_no_open(badge=en:todo.priority.badge.low,name=Ideas,count=0)",
    ]
    assert snapshot.selected_index == 0
    assert snapshot.description == "Clients\nAdmin"
    assert snapshot.tabs[0].tooltip == "en:todo.tab.tooltip(priority=en:todo.priority.high)\nClients\nAdmin"
    assert snapshot.add.action is ActionIdEnum.LIST_ADD


def test_tab_menu_enables_moves_within_the_priority_and_delete_unless_last() -> None:
    stack = TodoUiStack(lists=[make_list("Work", position=0), make_list("Home", position=1)])

    first, second = stack.tabs.build_snapshot().tabs
    single = TodoUiStack(lists=[make_list("Inbox")]).tabs.build_snapshot().tabs[0]

    assert [button.enabled for button in first.menu] == [True, False, True, True]
    assert [button.enabled for button in second.menu] == [True, True, False, True]
    assert [button.enabled for button in single.menu] == [True, False, False, False]


def test_selecting_a_tab_shows_its_tasks_and_is_remembered() -> None:
    stack = TodoUiStack(tasks=[make_task(1), make_task(2, list_id=HOME_LIST_ID)])

    stack.tabs.on_list_action_requested(int(ActionIdEnum.LIST_SELECT), HOME_LIST_ID)
    stack.settle()

    assert stack.state.list_id == HOME_LIST_ID
    assert [row.key for row in stack.rendered_table[-1].table.rows] == ["task-002"]
    assert stack.preferences.values["layout/todo/list"] == HOME_LIST_ID


def test_moving_a_tab_reorders_within_the_priority() -> None:
    stack = TodoUiStack(lists=[make_list("Work", position=0), make_list("Home", position=1)])

    stack.tabs.on_list_action_requested(int(ActionIdEnum.LIST_MOVE_LATER), "list-work")
    stack.settle()

    assert [tab.list_id for tab in stack.rendered_tabs[-1].tabs] == ["list-home", "list-work"]


def test_deleting_a_list_with_tasks_asks_with_their_number() -> None:
    stack = TodoUiStack(tasks=[make_task(1, list_id=HOME_LIST_ID), make_task(2, list_id=HOME_LIST_ID)])

    stack.tabs.on_list_action_requested(int(ActionIdEnum.LIST_DELETE), HOME_LIST_ID)

    assert stack.dialogs.texts("confirm")[0][1] == ("en:todo.delete_list.message_with_tasks.other(count=2,name=Home)")
    assert [item.name for item in stack.lists()] == ["Work"]
    assert len(stack.tasks()) == 0


def test_deleting_an_empty_list_can_be_cancelled() -> None:
    stack = TodoUiStack()
    stack.dialogs.confirm_answer = False

    stack.tabs.on_list_action_requested(int(ActionIdEnum.LIST_DELETE), HOME_LIST_ID)

    assert stack.dialogs.texts("confirm")[0][1] == "en:todo.delete_list.message(name=Home)"
    assert len(stack.lists()) == 2


def test_unknown_tab_actions_are_ignored() -> None:
    stack = TodoUiStack()

    stack.tabs.on_action_requested(int(ActionIdEnum.TASK_NEW))
    stack.tabs.on_list_action_requested(int(ActionIdEnum.TASK_NEW), WORK_LIST_ID)
    stack.tabs.on_list_action_requested(int(ActionIdEnum.LIST_DELETE), "missing")

    assert len(stack.lists()) == 2


def test_table_rows_show_state_text_due_and_marks() -> None:
    stack = TodoUiStack(
        tasks=[
            make_task(1, text="Report\nwith sources\nand charts", due_date=TODAY - timedelta(days=1)),
            make_task(2, due_date=TODAY, due_time=time(18, 0), created_offset_minutes=1),
            make_task(3, due_date=TODAY, due_time=time(9, 0), created_offset_minutes=2),
            make_task(4, state=TaskStateEnum.DONE, due_date=TODAY - timedelta(days=3), created_offset_minutes=3),
            make_task(5, created_offset_minutes=4),
        ]
    )

    table = stack.table.build_snapshot().table
    rows = {row.key: row for row in table.rows}

    assert table.columns[1] == "en:todo.column.task"
    assert rows["task-001"].cells[1] == "Report en:todo.table.more_lines.other(count=2)"
    assert rows["task-001"].cells[2] == "en:format.date(day=05,month=11,year=2026)"
    assert rows["task-002"].cells[2] == "en:format.date(day=06,month=11,year=2026) en:format.time(hour=18,minute=00)"
    assert [rows[key].tone for key in ("task-001", "task-002", "task-003", "task-004", "task-005")] == [
        RowToneEnum.ERROR,
        RowToneEnum.WARNING,
        RowToneEnum.ERROR,
        RowToneEnum.MUTED,
        RowToneEnum.NORMAL,
    ]
    assert (rows["task-004"].checked, rows["task-005"].checked) == (True, False)
    assert (table.check_column, table.sort_column, table.sort_descending) == (0, 3, True)
    assert [row.key for row in table.rows] == ["task-005", "task-004", "task-003", "task-002", "task-001"]


def test_archived_rows_show_their_state_and_a_disabled_check_box() -> None:
    stack = TodoUiStack(tasks=[make_task(1, state=TaskStateEnum.ARCHIVED)])
    stack.toolbar.on_action_requested(int(ActionIdEnum.TODO_TOGGLE_SHOW_ARCHIVED))
    stack.settle()

    row = stack.rendered_table[-1].table.rows[0]

    assert (row.cells[0], row.checked, row.check_enabled) == ("en:todo.state.archived", True, False)


def test_selection_is_kept_after_a_render_and_after_sorting() -> None:
    stack = _stack(make_task(1, created_offset_minutes=1), make_task(2, created_offset_minutes=2))
    stack.select("task-001")

    assert stack.rendered_table[-1].table.selection == (1,)

    stack.table.on_sort_requested(3)
    stack.settle()

    table = stack.rendered_table[-1].table
    assert [row.key for row in table.rows] == ["task-001", "task-002"]
    assert table.selection == (0,)
    assert stack.preferences.values["layout/todo/sort_descending"] == "0"


def test_sorting_a_new_column_is_ascending_and_a_bad_column_is_ignored() -> None:
    stack = _stack(make_task(1, text="b"), make_task(2, text="a"))

    stack.table.on_sort_requested(1)
    stack.settle()
    stack.table.on_sort_requested(9)

    assert [row.key for row in stack.rendered_table[-1].table.rows] == ["task-002", "task-001"]
    assert stack.preferences.values["layout/todo/sort"] == "2"


def test_toolbar_states_follow_a_mixed_selection() -> None:
    stack = _stack(make_task(1), make_task(2, state=TaskStateEnum.DONE))

    assert _enabled(stack.toolbar.build_snapshot().menu) == {ActionIdEnum.TASK_NEW}

    stack.select("task-001", "task-002")
    menu = stack.toolbar.build_snapshot().menu

    assert _enabled(menu) == {
        ActionIdEnum.TASK_NEW,
        ActionIdEnum.TASK_COMPLETE,
        ActionIdEnum.TASK_REOPEN,
        ActionIdEnum.TASK_ARCHIVE,
        ActionIdEnum.TASK_MOVE,
        ActionIdEnum.TASK_DELETE,
    }
    assert [(target.list_id, target.enabled) for target in menu.move_targets] == [(HOME_LIST_ID, True)]

    stack.select("task-002")
    assert _enabled(stack.toolbar.build_snapshot().menu) >= {ActionIdEnum.TASK_EDIT, ActionIdEnum.TASK_DUPLICATE}


def test_reopen_in_a_mixed_selection_reopens_only_the_done_tasks() -> None:
    stack = _stack(make_task(1), make_task(2, state=TaskStateEnum.DONE))
    stack.select("task-001", "task-002")

    stack.toolbar.on_action_requested(int(ActionIdEnum.TASK_REOPEN))
    stack.settle()

    assert {task.state for task in stack.tasks()} == {TaskStateEnum.OPEN}


def test_done_on_three_tasks_then_hiding_done_drops_them_from_the_selection() -> None:
    stack = _stack(make_task(1), make_task(2), make_task(3), make_task(4))
    stack.select("task-001", "task-002", "task-003")

    stack.toolbar.on_action_requested(int(ActionIdEnum.TASK_COMPLETE))
    stack.settle()
    stack.toolbar.on_action_requested(int(ActionIdEnum.TODO_TOGGLE_SHOW_DONE))
    stack.settle()
    stack.refresher.on_todo_changed(stack.events[-1])
    stack.settle()

    assert [row.key for row in stack.rendered_table[-1].table.rows] == ["task-004"]
    assert stack.state.selected_ids == ()
    assert stack.rendered_toolbar[-1].show_done.checked is False
    assert stack.preferences.values["layout/todo/show_done"] == "0"


def test_check_box_toggles_done_and_reopen_without_opening_the_task() -> None:
    stack = _stack(make_task(1))

    stack.table.on_check_toggled("task-001")
    stack.settle()
    assert stack.task("task-001").state is TaskStateEnum.DONE

    stack.table.on_check_toggled("task-001")
    stack.settle()
    assert stack.task("task-001").state is TaskStateEnum.OPEN
    assert stack.task_window.shows == 0
    stack.table.on_check_toggled("missing")


def test_space_completes_the_open_selected_tasks_or_reopens_the_done_ones() -> None:
    stack = _stack(make_task(1), make_task(2, state=TaskStateEnum.DONE))
    stack.select("task-001", "task-002")

    stack.table.on_selection_toggled()
    stack.settle()
    assert {task.state for task in stack.tasks()} == {TaskStateEnum.DONE}

    stack.table.on_selection_toggled()
    stack.settle()
    assert {task.state for task in stack.tasks()} == {TaskStateEnum.OPEN}


def test_delete_asks_with_a_plural_text_and_can_be_refused() -> None:
    stack = _stack(make_task(1), make_task(2), make_task(3))
    stack.select("task-001", "task-002", "task-003")
    stack.dialogs.confirm_answer = False

    stack.toolbar.on_action_requested(int(ActionIdEnum.TASK_DELETE))
    stack.settle()
    assert len(stack.tasks()) == 3

    stack.dialogs.confirm_answer = True
    stack.toolbar.on_action_requested(int(ActionIdEnum.TASK_DELETE))
    stack.settle()

    assert stack.dialogs.texts("confirm")[0][1] == "en:todo.delete_tasks.message.other(count=3)"
    assert len(stack.tasks()) == 0
    assert stack.rendered_details[-1].empty_text == "en:todo.details.empty"


def test_move_duplicate_archive_and_unarchive_from_the_toolbar() -> None:
    stack = _stack(make_task(1))
    stack.select("task-001")

    stack.toolbar.on_action_requested(int(ActionIdEnum.TASK_DUPLICATE))
    stack.settle()
    assert stack.state.selected_ids == ("new-0001",)

    stack.toolbar.on_move_requested(HOME_LIST_ID)
    stack.settle()
    assert stack.task("new-0001").list_id == HOME_LIST_ID

    stack.select("task-001")
    stack.toolbar.on_action_requested(int(ActionIdEnum.TASK_ARCHIVE))
    stack.settle()
    stack.toolbar.on_action_requested(int(ActionIdEnum.TODO_TOGGLE_SHOW_ARCHIVED))
    stack.settle()
    stack.select("task-001")
    stack.toolbar.on_action_requested(int(ActionIdEnum.TASK_UNARCHIVE))
    stack.settle()
    assert stack.task("task-001").state is TaskStateEnum.OPEN


def test_actions_without_the_right_selection_do_nothing() -> None:
    stack = _stack(make_task(1), make_task(2))
    stack.select("task-001", "task-002")

    stack.toolbar.on_action_requested(int(ActionIdEnum.TASK_EDIT))
    stack.toolbar.on_action_requested(int(ActionIdEnum.TASK_DUPLICATE))
    stack.toolbar.on_action_requested(int(ActionIdEnum.LIST_ADD))
    stack.select()
    stack.toolbar.on_action_requested(int(ActionIdEnum.TASK_DELETE))

    assert stack.task_window.shows == 0
    assert len(stack.tasks()) == 2
    assert not stack.actions.handles(ActionIdEnum.LIST_ADD)
    assert stack.actions.run(ActionIdEnum.LIST_ADD).is_skipped


def test_details_show_the_selected_task_or_a_hint() -> None:
    stack = _stack(make_task(1, text="Report\nsecond line", due_date=TODAY), make_task(2))

    stack.select("task-001")
    details = stack.rendered_details[-1]
    assert details.text == "Report\nsecond line"
    assert [row.value for row in details.rows][:3] == [
        "Work",
        "en:format.date(day=06,month=11,year=2026)",
        "en:todo.state.open",
    ]

    stack.select("task-001", "task-002")
    assert stack.rendered_details[-1].empty_text == "en:todo.details.several.other(count=2)"

    stack.select("task-002")
    assert stack.rendered_details[-1].rows[1].value == "en:todo.details.no_due"


def test_quick_add_creates_the_task_empties_the_field_and_selects_it() -> None:
    stack = _stack()

    stack.quick_add.on_text_changed("Call the bank")
    stack.quick_add.on_submitted("Call the bank")
    stack.settle()

    assert [task.text.first_line for task in stack.tasks()] == ["Call the bank"]
    assert not stack.rendered_quick_add[-1].text
    assert stack.state.selected_ids == ("new-0001",)
    assert stack.rendered_quick_add[-1].placeholder == "en:todo.quick_add.placeholder"


def test_quick_add_ignores_an_empty_text_and_shows_other_refusals() -> None:
    stack = _stack()

    stack.quick_add.on_submitted("   ")
    stack.settle()
    assert not stack.rendered_quick_add[-1].error

    stack.quick_add.on_submitted("x" * 5001)
    stack.settle()
    assert stack.rendered_quick_add[-1].error == "en:error.task_text_too_long(max=5000)"
    assert stack.rendered_quick_add[-1].text == "x" * 5001

    stack.quick_add.on_text_changed("x")
    stack.settle()
    assert not stack.rendered_quick_add[-1].error


def test_double_click_opens_the_task_dialog_and_new_opens_an_empty_one() -> None:
    stack = _stack(make_task(1))

    stack.table.on_activated("task-001")
    stack.settle()
    stack.toolbar.on_action_requested(int(ActionIdEnum.TASK_NEW))
    stack.settle()

    assert stack.task_window.shows == 2


def test_minute_change_re_renders_the_table_for_the_due_marks() -> None:
    stack = _stack(make_task(1, due_date=TODAY, due_time=time(10, 1)))
    assert stack.rendered_table[-1].table.rows[0].tone is RowToneEnum.WARNING

    stack.table.on_tick()
    stack.clock.advance(seconds=61)
    stack.table.on_tick()
    stack.settle()

    assert stack.rendered_table[-1].table.rows[0].tone is RowToneEnum.ERROR


def test_another_data_file_shows_an_existing_list_and_clears_the_selection() -> None:
    stack = _stack(make_task(1))
    stack.select("task-001")
    stack.state.select_list("gone")

    stack.bus.publish(UserDataReplacedEvent(path=Path("C:/other.toml")))
    stack.settle()

    assert stack.state.list_id == WORK_LIST_ID
    assert stack.state.selected_ids == ()


@pytest.mark.parametrize(
    ("stored", "sort", "descending", "show_done", "show_archived"),
    [
        ({}, 4, True, True, False),
        (
            {
                "layout/todo/sort": "3",
                "layout/todo/sort_descending": "0",
                "layout/todo/show_done": "0",
                "layout/todo/show_archived": "1",
            },
            3,
            False,
            False,
            True,
        ),
        ({"layout/todo/sort": "x", "layout/todo/show_done": "maybe"}, 4, True, True, False),
        ({"layout/todo/sort": "99"}, 4, True, True, False),
    ],
)
def test_view_state_is_restored_from_the_layout_keys(
    stored: dict[str, str], sort: int, descending: bool, show_done: bool, show_archived: bool
) -> None:
    state = TodoUiStack(stored=stored).state

    assert (int(state.sort_key), state.descending, state.show_done, state.show_archived) == (
        sort,
        descending,
        show_done,
        show_archived,
    )


def test_reset_layout_brings_back_the_defaults() -> None:
    stack = TodoUiStack(stored={"layout/todo/sort": "2", "layout/todo/show_archived": "1"})

    stack.refresher.reset_layout()

    assert (int(stack.state.sort_key), stack.state.show_archived) == (4, False)


def test_menu_buttons_are_disabled_while_their_action_is_busy() -> None:
    stack = _stack(make_task(1))
    stack.select("task-001")

    stack.toolbar.on_action_requested(int(ActionIdEnum.TASK_COMPLETE))
    stack.scheduler.run_pending()

    assert _button(stack.rendered_toolbar[-1].menu, ActionIdEnum.TASK_COMPLETE).enabled is False


def test_a_bulk_change_follows_the_data_once_not_once_per_task() -> None:
    stack = _stack(*(make_task(number) for number in range(1, 51)))
    stack.select(*(f"task-{number:03d}" for number in range(1, 51)))
    calls: list[int] = []
    keep_visible = stack.state.keep_visible

    def counting(visible_ids: Iterable[str]) -> None:
        calls.append(1)
        keep_visible(visible_ids)

    stack.state.keep_visible = counting
    stack.toolbar.on_action_requested(int(ActionIdEnum.TASK_COMPLETE))
    stack.settle()

    assert len(calls) == 1
    assert {task.state for task in stack.tasks()} == {TaskStateEnum.DONE}
