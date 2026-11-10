from datetime import date, time

from concentrator.domain.todo.priority_enum import PriorityEnum
from concentrator.domain.todo.task_state_enum import TaskStateEnum
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from tests.fakes.todo_factory import HOME_LIST_ID, WORK_LIST_ID, make_task
from tests.fakes.todo_ui_stack import TodoUiStack

SAVE_TASK = int(ActionIdEnum.TASK_EDIT_SAVE)
CANCEL_TASK = int(ActionIdEnum.TASK_EDIT_CANCEL)
SAVE_LIST = int(ActionIdEnum.LIST_EDIT_SAVE)
CANCEL_LIST = int(ActionIdEnum.LIST_EDIT_CANCEL)


def test_new_task_dialog_starts_empty_in_the_current_list_without_errors() -> None:
    stack = TodoUiStack()
    stack.task_editor.open_new(WORK_LIST_ID)

    snapshot = stack.task_editor.build_snapshot()

    assert snapshot.title == "en:todo.task_edit.title.new"
    assert (snapshot.text.text, snapshot.text.error, snapshot.text.max_length) == ("", "", 5000)
    assert (snapshot.task_list.options, snapshot.task_list.selected) == (("Work", "Home"), 0)
    assert (snapshot.due.has_date, snapshot.due.time_enabled) == (False, False)
    assert (snapshot.due.year, snapshot.due.month, snapshot.due.day, snapshot.due.hour) == (2026, 11, 6, 9)
    assert snapshot.save.enabled is False


def test_new_task_is_saved_with_several_lines_a_due_date_and_time() -> None:
    stack = TodoUiStack()

    def act() -> None:
        editor = stack.task_editor
        editor.on_text_changed("Report\nwith sources")
        editor.on_list_selected(1)
        editor.on_due_date_changed(True, 2026, 11, 5)
        editor.on_due_time_changed(True, 14, 30)
        assert editor.build_snapshot().save.enabled
        editor.on_action_requested(SAVE_TASK)

    stack.task_window.while_open = act
    stack.task_editor.open_new(WORK_LIST_ID)

    task = stack.tasks().items[0]
    assert (task.text.lines, task.list_id, task.due_date, task.due_time) == (
        ("Report", "with sources"),
        HOME_LIST_ID,
        date(2026, 11, 5),
        time(14, 30),
    )
    assert stack.task_window.closes == 1
    assert stack.state.selected_ids == (task.id,)


def test_task_dialog_shows_inline_errors_after_a_change() -> None:
    stack = TodoUiStack()
    stack.task_editor.open_new(WORK_LIST_ID)

    stack.task_editor.on_text_changed("x")
    stack.task_editor.on_text_changed("   ")

    assert stack.task_editor.build_snapshot().text.error == "en:error.task_text_empty"
    stack.task_editor.on_action_requested(SAVE_TASK)
    assert len(stack.tasks()) == 0


def test_no_date_also_removes_the_time() -> None:
    stack = TodoUiStack(tasks=[make_task(1, due_date=date(2026, 11, 9), due_time=time(8, 0))])
    stack.task_editor.open_edit("task-001")

    stack.task_editor.on_due_date_changed(False, 2026, 11, 9)
    snapshot = stack.task_editor.build_snapshot()

    assert (snapshot.due.has_date, snapshot.due.has_time, snapshot.due.time_enabled) == (False, False, False)


def test_editing_a_task_needs_a_change_and_records_it() -> None:
    stack = TodoUiStack(tasks=[make_task(1)])
    stack.task_editor.open_edit("task-001")

    assert stack.task_editor.build_snapshot().title == "en:todo.task_edit.title.edit"
    assert stack.task_editor.build_snapshot().save.enabled is False

    stack.task_editor.on_text_changed("Task 1\nmore")
    stack.task_editor.on_action_requested(SAVE_TASK)

    assert stack.task("task-001").text.line_count == 2
    assert stack.task_editor.open_edit("missing").is_failure


def test_cancel_of_an_unchanged_task_closes_without_asking() -> None:
    stack = TodoUiStack(tasks=[make_task(1)])
    stack.task_editor.open_edit("task-001")

    stack.task_editor.on_action_requested(CANCEL_TASK)

    assert stack.task_window.closes == 1
    assert stack.dialogs.calls == []


def test_cancel_of_a_changed_task_asks_and_can_keep_editing() -> None:
    stack = TodoUiStack(tasks=[make_task(1)])
    stack.task_editor.open_edit("task-001")
    stack.task_editor.on_text_changed("Changed")
    stack.dialogs.confirm_answers = [False, True]

    stack.task_editor.on_action_requested(CANCEL_TASK)
    assert stack.task_window.closes == 0
    stack.clock.advance(ms=200)
    stack.scheduler.advance(200)

    stack.task_editor.on_action_requested(CANCEL_TASK)

    assert stack.task_window.closes == 1
    assert stack.dialogs.texts("confirm")[0][1] == "en:todo.discard.message"
    assert stack.task("task-001").text.first_line == "Task 1"


def test_unknown_task_dialog_actions_are_ignored() -> None:
    stack = TodoUiStack()
    stack.task_editor.on_action_requested(int(ActionIdEnum.LIST_ADD))
    stack.task_editor.on_list_selected(9)

    assert stack.task_window.closes == 0


def test_new_list_gets_the_default_priority_and_is_shown_once_saved() -> None:
    stack = TodoUiStack()

    def act() -> None:
        editor = stack.list_editor
        snapshot = editor.build_snapshot()
        assert (snapshot.title, snapshot.priority.selected, snapshot.save.enabled) == (
            "en:todo.list_edit.title.new",
            1,
            False,
        )
        editor.on_name_changed("Ideas")
        editor.on_description_changed("Later\nmaybe")
        editor.on_priority_selected(0)
        editor.on_action_requested(SAVE_LIST)

    stack.list_window.while_open = act
    stack.tabs.on_action_requested(int(ActionIdEnum.LIST_ADD))

    created = next(item for item in stack.lists() if item.name == "Ideas")
    assert (created.priority, created.description.lines) == (PriorityEnum.LOW, ("Later", "maybe"))
    assert stack.state.list_id == created.id


def test_list_dialog_refuses_a_duplicate_name_inline() -> None:
    stack = TodoUiStack()
    stack.list_editor.open_new()

    stack.list_editor.on_name_changed("WORK")
    stack.list_editor.on_action_requested(SAVE_LIST)

    assert stack.list_editor.build_snapshot().name.error == "en:error.list_name_duplicate"
    assert len(stack.lists()) == 2


def test_editing_a_list_and_cancelling_a_change() -> None:
    stack = TodoUiStack()
    stack.list_editor.open_edit(HOME_LIST_ID)
    assert stack.list_editor.build_snapshot().name.text == "Home"

    stack.list_editor.on_priority_selected(3)
    stack.list_editor.on_action_requested(SAVE_LIST)
    assert [item.name for item in stack.lists()] == ["Home", "Work"]

    stack.list_editor.open_edit(HOME_LIST_ID)
    stack.list_editor.on_name_changed("House")
    stack.dialogs.confirm_answer = True
    stack.clock.advance(ms=200)
    stack.scheduler.advance(200)
    stack.list_editor.on_action_requested(CANCEL_LIST)

    assert stack.dialogs.texts("confirm") == [
        ("en:todo.discard.title", "en:todo.discard.message", "en:todo.discard.accept", "en:todo.discard.keep")
    ]
    assert [item.name for item in stack.lists()] == ["Home", "Work"]
    assert stack.list_editor.open_edit("missing").is_failure
    stack.list_editor.on_action_requested(int(ActionIdEnum.TASK_NEW))
    stack.list_editor.on_priority_selected(-1)


def test_tab_edit_opens_the_list_dialog() -> None:
    stack = TodoUiStack(tasks=[make_task(1, state=TaskStateEnum.DONE)])

    stack.tabs.on_list_action_requested(int(ActionIdEnum.LIST_EDIT), WORK_LIST_ID)

    assert stack.list_window.shows == 1
