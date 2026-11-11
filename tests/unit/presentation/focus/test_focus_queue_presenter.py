from datetime import date, timedelta

import pytest

from concentrator.domain.focus.focus_limits import FocusLimits
from concentrator.domain.todo.task import Task
from concentrator.domain.todo.task_event import DETAIL_SOURCE, SOURCE_FOCUS
from concentrator.domain.todo.task_state_enum import TaskStateEnum
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.row_tone_enum import RowToneEnum
from concentrator.presentation.focus.focus_queue_snapshot import FocusQueueSnapshot
from concentrator.presentation.focus.quick_add_list_choice import QUICK_ADD_LIST_KEY
from tests.fakes.focus_factory import FOCUS_LIMITS, make_queue
from tests.fakes.focus_ui_stack import FocusUiStack
from tests.fakes.todo_factory import HOME_LIST_ID, WORK_LIST_ID, make_list, make_task

TODAY = date(2026, 11, 6)
"""Local date of ``FakeClock``."""


def _stack(*tasks: Task, queue: tuple[int, ...] = (), limits: FocusLimits = FOCUS_LIMITS) -> FocusUiStack:
    stack = FocusUiStack(tasks=tasks, queue=make_queue(*queue), limits=limits)
    stack.renderer.request_all()
    stack.settle()
    return stack


def _queue(stack: FocusUiStack) -> FocusQueueSnapshot:
    stack.settle()
    return stack.queue.build_snapshot()


def test_rows_show_the_queued_tasks_with_their_list_due_badge_and_marks() -> None:
    stack = _stack(
        make_task(1, text="Report\nwith sources", due_date=TODAY - timedelta(days=1)),
        make_task(2, list_id=HOME_LIST_ID, due_date=TODAY),
        queue=(1, 2),
    )

    snapshot = _queue(stack)

    assert snapshot.capacity == "en:focus.capacity(count=2,max=20)"
    first, second = snapshot.rows
    assert (first.item_id, first.text, first.list_name, first.tone) == ("item-001", "Report", "Work", RowToneEnum.ERROR)
    assert first.tooltip == "Report\nwith sources\nen:focus.row.list(name=Work)"
    assert first.due_text == "en:format.date(day=05,month=11,year=2026)"
    assert (second.list_name, second.tone) == ("Home", RowToneEnum.WARNING)
    assert [button.enabled for button in first.menu] == [False, True, True]
    assert [button.enabled for button in second.menu] == [True, False, True]
    assert (first.complete.action, first.remove.action) == (ActionIdEnum.FOCUS_COMPLETE, ActionIdEnum.FOCUS_REMOVE)
    assert stack.rendered_focus[-1] == snapshot


def test_empty_queue_shows_the_empty_text_and_the_inbox_in_the_quick_add_hint() -> None:
    snapshot = _queue(_stack())

    assert (snapshot.rows, snapshot.empty_text, snapshot.error) == ((), "en:focus.empty", "")
    assert snapshot.quick_add.placeholder == "en:focus.quick_add.placeholder(list=en:todo.default_list_name)"
    assert snapshot.picker.placeholder == "en:focus.picker.placeholder"


def test_check_box_completes_the_task_from_the_queue() -> None:
    stack = _stack(make_task(1), queue=(1,))

    stack.queue.on_row_action(int(ActionIdEnum.FOCUS_COMPLETE), "item-001")

    task = stack.task("task-001")
    assert task.state is TaskStateEnum.DONE
    last = task.history.last
    assert last is not None
    assert last.detail(DETAIL_SOURCE) == SOURCE_FOCUS
    assert _queue(stack).rows == ()
    assert not stack.rendered_table[-1].table.rows[0].cells[1]


def test_row_actions_remove_move_and_ignore_unknown_actions(caplog: pytest.LogCaptureFixture) -> None:
    stack = _stack(make_task(1), make_task(2), make_task(3), queue=(1, 2, 3))

    stack.queue.on_row_action(int(ActionIdEnum.FOCUS_MOVE_DOWN), "item-001")
    stack.settle()
    stack.queue.on_row_action(int(ActionIdEnum.FOCUS_REMOVE), "item-003")
    stack.settle()
    stack.queue.on_row_action(int(ActionIdEnum.FOCUS_MOVE_UP), "item-002")
    stack.queue.on_row_action(int(ActionIdEnum.TASK_NEW), "item-002")

    assert [row.item_id for row in _queue(stack).rows] == ["item-002", "item-001"]
    assert stack.task("task-003").state is TaskStateEnum.OPEN
    assert "Focus row action TASK_NEW" in caplog.text


def test_show_in_list_selects_the_task_in_its_list_without_filters() -> None:
    stack = _stack(make_task(1), make_task(2, list_id=HOME_LIST_ID), queue=(2,))
    stack.filters.on_search_changed("nothing matches")
    stack.clock.advance(ms=200)
    stack.scheduler.advance(200)
    stack.settle()

    stack.queue.on_row_action(int(ActionIdEnum.FOCUS_SHOW_IN_LIST), "item-002")
    stack.settle()

    assert stack.state.list_id == HOME_LIST_ID
    assert stack.state.search.is_empty
    table = stack.rendered_table[-1].table
    assert [row.key for row in table.rows] == ["task-002"]
    assert table.selection == (0,)


def test_show_in_list_of_an_unknown_item_shows_a_message() -> None:
    stack = _stack(make_task(1))

    stack.queue.on_row_action(int(ActionIdEnum.FOCUS_SHOW_IN_LIST), "item-404")

    assert _queue(stack).error == "en:error.entity_not_found"


def test_picker_proposes_open_tasks_not_queued_ignoring_accents_and_limited() -> None:
    tasks = [
        make_task(1, text="État du rapport"),
        make_task(2, text="etat des lieux", list_id=HOME_LIST_ID, due_date=TODAY),
        make_task(3, text="Etat final", state=TaskStateEnum.DONE),
        make_task(4, text="etat queued"),
        make_task(5, text="etat 5"),
        make_task(6, text="etat 6"),
    ]
    stack = _stack(*tasks, queue=(4,))

    assert _queue(stack).choices == ()
    stack.queue.on_picker_text_changed("ETAT")
    choices = _queue(stack).choices

    assert [choice.task_id for choice in choices] == ["task-002", "task-001", "task-005"]
    assert choices[0].text == "en:focus.picker.choice(text=etat des lieux,list=Home)"


def test_picking_a_task_queues_it_and_empties_the_field() -> None:
    stack = _stack(make_task(1, text="Report"))
    stack.queue.on_picker_text_changed("rep")

    stack.queue.on_picked("task-001")

    snapshot = _queue(stack)
    assert [row.item_id for row in snapshot.rows] == ["new-0001"]
    assert (snapshot.picker.text, snapshot.picker.cleared_count, snapshot.choices) == ("", 1, ())


def test_quick_add_creates_the_task_in_the_chosen_list_and_queues_it() -> None:
    stack = _stack()
    stack.choice.choose(HOME_LIST_ID)
    stack.queue.on_quick_add_text_changed("Call the bank")

    stack.queue.on_quick_add_submitted("Call the bank")

    snapshot = _queue(stack)
    assert [row.list_name for row in snapshot.rows] == ["Home"]
    assert (snapshot.quick_add.text, snapshot.quick_add.cleared_count) == ("", 1)
    assert snapshot.quick_add.placeholder == "en:focus.quick_add.placeholder(list=Home)"


def test_quick_add_of_an_empty_text_says_nothing_and_a_full_queue_says_why() -> None:
    stack = _stack(make_task(1), queue=(1,), limits=FocusLimits(max_items=1))

    stack.queue.on_quick_add_submitted("   ")
    assert not _queue(stack).error
    stack.queue.on_quick_add_submitted("More")

    snapshot = _queue(stack)
    assert snapshot.error == "en:error.focus_queue_full(max=1)"
    assert snapshot.quick_add.text == "More"
    stack.queue.on_quick_add_text_changed("More!")
    assert not _queue(stack).error


def test_star_of_the_table_queues_and_unqueues_and_reports_a_full_queue() -> None:
    stack = _stack(make_task(1), make_task(2), limits=FocusLimits(max_items=1))

    stack.focus_actions.on_task_toggled("task-001")
    stack.settle()
    rows = {row.key: row for row in stack.rendered_table[-1].table.rows}
    assert rows["task-001"].cells[1] == "en:todo.table.focus_on"
    stack.focus_actions.on_task_toggled("task-002")

    assert _queue(stack).error == "en:error.focus_queue_full(max=1)"
    stack.queue.on_picker_text_changed("x")
    assert not _queue(stack).error
    stack.focus_actions.on_task_toggled("task-001")
    assert _queue(stack).rows == ()


def test_toolbar_adds_and_removes_the_selected_tasks() -> None:
    stack = _stack(make_task(1), make_task(2, state=TaskStateEnum.DONE), make_task(3), queue=(3,))
    stack.select("task-001", "task-002", "task-003")
    buttons = {button.action: button.enabled for button in stack.toolbar.build_snapshot().menu.buttons}
    assert (buttons[ActionIdEnum.FOCUS_ADD_SELECTED], buttons[ActionIdEnum.FOCUS_REMOVE_SELECTED]) == (True, True)

    stack.toolbar.on_action_requested(int(ActionIdEnum.FOCUS_ADD_SELECTED))
    stack.settle()
    assert stack.focus.queued() == ["task-003", "task-001"]

    stack.toolbar.on_action_requested(int(ActionIdEnum.FOCUS_REMOVE_SELECTED))
    stack.settle()
    assert stack.focus.queued() == []


def test_tab_menu_marks_and_changes_the_quick_add_list() -> None:
    inbox = make_list("en:todo.default_list_name", list_id="list-inbox", position=2)
    stack = FocusUiStack(lists=[make_list("Work"), make_list("Home", position=1), inbox])
    stack.renderer.request_all()
    stack.settle()

    def checked() -> dict[str, bool]:
        snapshot = stack.tabs.build_snapshot()
        return {tab.list_id: tab.menu[-1].checked for tab in snapshot.tabs}

    assert checked() == {WORK_LIST_ID: False, HOME_LIST_ID: False, "list-inbox": True}
    stack.tabs.on_list_action_requested(int(ActionIdEnum.FOCUS_SET_QUICK_ADD_LIST), WORK_LIST_ID)
    stack.settle()

    assert stack.preferences.values[QUICK_ADD_LIST_KEY] == WORK_LIST_ID
    assert checked() == {WORK_LIST_ID: True, HOME_LIST_ID: False, "list-inbox": False}
    assert _queue(stack).quick_add.placeholder == "en:focus.quick_add.placeholder(list=Work)"


def test_tick_renders_again_when_the_minute_changes() -> None:
    stack = _stack(make_task(1, due_date=TODAY), queue=(1,))
    count = len(stack.rendered_focus)

    stack.queue.on_tick()
    stack.settle()
    assert len(stack.rendered_focus) == count
    stack.clock.advance(seconds=60)
    stack.queue.on_tick()
    stack.scheduler.run_pending()

    assert stack.queue.build_snapshot().rows[0].tone is RowToneEnum.WARNING
