from dataclasses import replace

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.severity_enum import SeverityEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.focus.focus_item import FocusItemId
from concentrator.domain.focus.focus_items_collection import FocusItemsCollection
from concentrator.domain.focus.focus_limits import FocusLimits
from concentrator.domain.focus.focus_rules import FocusRules
from concentrator.domain.todo.task import Task
from concentrator.domain.todo.task_state_enum import TaskStateEnum
from tests.fakes.focus_factory import FOCUS_LIMITS, make_item, make_queue
from tests.fakes.todo_factory import make_task

SMALL = FocusLimits(max_items=2)


def _tasks(*tasks: Task) -> dict[str, bool]:
    return {task.id: task.state is TaskStateEnum.OPEN for task in tasks}


def _add(task: Task, queue: FocusItemsCollection, limits: FocusLimits = FOCUS_LIMITS) -> ValidationResult:
    return FocusRules.validate_add(task.id, is_open=task.state is TaskStateEnum.OPEN, queue=queue, limits=limits)


def _can(task: Task, queue: FocusItemsCollection) -> bool:
    return FocusRules.can_queue(task.id, is_open=task.state is TaskStateEnum.OPEN, queued=queue.task_ids())


def test_validate_add_accepts_an_open_task_not_queued() -> None:
    assert _add(make_task(3), make_queue(1, 2), FOCUS_LIMITS).is_success


def test_validate_add_refuses_a_task_that_is_not_open() -> None:
    for state in (TaskStateEnum.DONE, TaskStateEnum.ARCHIVED):
        result = _add(make_task(3, state=state), make_queue(), FOCUS_LIMITS)

        assert result.error_codes == (ErrorCodeEnum.FOCUS_TASK_NOT_OPEN,)


def test_validate_add_refuses_a_duplicate() -> None:
    result = _add(make_task(1), make_queue(1), FOCUS_LIMITS)

    assert result.error_codes == (ErrorCodeEnum.FOCUS_TASK_ALREADY_QUEUED,)


def test_validate_add_refuses_beyond_the_capacity() -> None:
    result = _add(make_task(3), make_queue(1, 2), SMALL)

    assert result.error_codes == (ErrorCodeEnum.FOCUS_QUEUE_FULL,)
    issue = result.first_failure
    assert issue is not None
    assert dict(issue.params) == {"max": "2"}


def test_validate_room_counts_every_item_to_add() -> None:
    assert FocusRules.validate_room(make_queue(1), 1, SMALL).is_success
    assert FocusRules.validate_room(make_queue(1), 2, SMALL).is_failure


def test_can_queue_needs_an_open_task_not_queued() -> None:
    queue = make_queue(1)

    assert _can(make_task(2), queue)
    assert not _can(make_task(1), queue)
    assert not _can(make_task(2, state=TaskStateEnum.DONE), queue)


def test_usable_keeps_valid_items_in_position_order_and_renumbers() -> None:
    items = (make_item(1, position=5), make_item(2, position=3))

    result = FocusRules.usable(items, _tasks(make_task(1), make_task(2)), FOCUS_LIMITS)

    queue = result.data
    assert queue is not None
    assert [(item.task_id, item.position) for item in queue] == [("task-002", 0), ("task-001", 1)]
    assert result.validation.is_success


def test_usable_drops_a_missing_task_with_a_warning() -> None:
    result = FocusRules.usable((make_item(1), make_item(2)), _tasks(make_task(2)), FOCUS_LIMITS)

    assert result.data == FocusItemsCollection((make_item(2, position=0),))
    issue = result.validation.issues[0]
    assert issue.code is ErrorCodeEnum.FOCUS_TASK_MISSING
    assert issue.severity is SeverityEnum.WARNING
    assert issue.field == "0.task_id"
    assert not result.validation.is_failure


def test_usable_drops_closed_duplicate_and_extra_items() -> None:
    items = (
        make_item(1, position=0),
        make_item(1, 2, position=1),
        make_item(3, 1, position=2),
        make_item(4, position=3),
        make_item(5, position=4),
        make_item(6, position=5),
    )
    tasks = _tasks(make_task(1), make_task(2), make_task(4, state=TaskStateEnum.DONE), make_task(5), make_task(6))

    result = FocusRules.usable(items, tasks, SMALL)

    queue = result.data
    assert queue is not None
    assert [item.task_id for item in queue] == ["task-001", "task-005"]
    assert result.validation.error_codes == (
        ErrorCodeEnum.ENTITY_DUPLICATE_ID,
        ErrorCodeEnum.FOCUS_TASK_ALREADY_QUEUED,
        ErrorCodeEnum.FOCUS_TASK_NOT_OPEN,
        ErrorCodeEnum.FOCUS_QUEUE_FULL,
    )


def test_usable_drops_an_item_with_a_bad_identity() -> None:
    bad = replace(make_item(1), id=FocusItemId(" "))

    result = FocusRules.usable((bad,), _tasks(make_task(1)), FOCUS_LIMITS)

    assert result.data == FocusItemsCollection()
    assert result.validation.error_codes == (ErrorCodeEnum.REQUIRED_VALUE_MISSING,)
