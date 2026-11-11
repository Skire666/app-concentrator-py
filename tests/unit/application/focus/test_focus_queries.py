from concentrator.application.common.app_config import FocusSection
from concentrator.application.focus.focus_defaults import FocusDefaults
from concentrator.domain.focus.focus_items_collection import FocusItemsCollection
from concentrator.domain.focus.focus_limits import FocusLimits
from concentrator.domain.focus.focus_removal_reason_enum import FocusRemovalReasonEnum
from concentrator.domain.todo.task_list import TaskList, TaskListId
from concentrator.domain.todo.task_state_enum import TaskStateEnum
from tests.fakes.focus_factory import make_item, make_queue
from tests.fakes.focus_stack import FocusStack
from tests.fakes.todo_factory import HOME_LIST_ID, make_task


def _name(task_list: TaskList | None) -> str:
    assert task_list is not None
    return task_list.name


def test_entries_join_the_items_with_their_task_and_list_in_queue_order() -> None:
    tasks = [make_task(1), make_task(2, list_id=HOME_LIST_ID), make_task(3, list_id="list-gone")]
    stack = FocusStack(tasks=tasks, queue=make_queue(2, 1, 3))

    entries = stack.focus_queries.entries()

    assert [(entry.item.id, entry.task.id, entry.list_name) for entry in entries] == [
        ("item-002", "task-002", "Home"),
        ("item-001", "task-001", "Work"),
        ("item-003", "task-003", ""),
    ]


def test_entries_skip_an_item_whose_task_is_missing() -> None:
    stack = FocusStack(tasks=[make_task(1)], queue=FocusItemsCollection((make_item(1), make_item(2))))

    assert [entry.task.id for entry in stack.focus_queries.entries()] == ["task-001"]


def test_candidates_are_the_open_tasks_not_queued() -> None:
    tasks = [make_task(1), make_task(2), make_task(3, state=TaskStateEnum.DONE), make_task(4, list_id=HOME_LIST_ID)]
    stack = FocusStack(tasks=tasks, queue=make_queue(1))

    assert [task.id for task in stack.focus_queries.candidates()] == ["task-002", "task-004"]
    assert stack.focus_queries.queued_task_ids() == {"task-001"}


def test_quick_add_list_name_prefers_the_chosen_list() -> None:
    stack = FocusStack()

    assert _name(stack.focus_queries.quick_add_list(HOME_LIST_ID)) == "Home"
    assert stack.focus_queries.quick_add_list(TaskListId("list-gone")) is None


def test_history_records_nothing_for_missing_tasks() -> None:
    stack = FocusStack()

    assert stack.history.record_removed(["task-404"], FocusRemovalReasonEnum.BY_USER).is_skipped


def test_defaults_come_from_the_focus_section() -> None:
    defaults = FocusDefaults.from_section(FocusSection(max_items=7, picker_max_results=9))

    assert defaults == FocusDefaults(limits=FocusLimits(max_items=7), picker_max_results=9)
