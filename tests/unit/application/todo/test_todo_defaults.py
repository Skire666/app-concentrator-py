import pytest

from concentrator.application.todo.task_query import TaskQuery
from concentrator.application.todo.todo_defaults import TodoDefaults
from concentrator.domain.todo.priority_enum import PriorityEnum
from concentrator.domain.todo.task_sort_key_enum import TaskSortKeyEnum
from concentrator.domain.todo.task_state_enum import TaskStateEnum
from concentrator.domain.todo.todo_limits import TodoLimits
from tests.fakes.app_config_factory import make_todo_section


def test_defaults_gather_the_todo_section() -> None:
    defaults = TodoDefaults.from_section(make_todo_section(default_sort=TaskSortKeyEnum.DUE, max_history_events=7))

    assert defaults == TodoDefaults(
        limits=TodoLimits(
            max_task_text_length=5000,
            max_list_name_length=80,
            max_list_description_length=2000,
            max_history_events=7,
            max_recurrence_interval=999,
            max_recurrence_count=9999,
        ),
        list_priority=PriorityEnum.NORMAL,
        sort_key=TaskSortKeyEnum.DUE,
        sort_descending=True,
        table_ratio_percent=75,
        column_widths_px=(60, 140, 140, 140),
        recurrence_preview_count=4,
    )


@pytest.mark.parametrize(
    ("show_done", "show_archived", "states"),
    [
        (False, False, {TaskStateEnum.OPEN}),
        (True, False, {TaskStateEnum.OPEN, TaskStateEnum.DONE}),
        (False, True, {TaskStateEnum.OPEN, TaskStateEnum.ARCHIVED}),
        (True, True, {TaskStateEnum.OPEN, TaskStateEnum.DONE, TaskStateEnum.ARCHIVED}),
    ],
)
def test_query_states_follow_the_toggles(show_done: bool, show_archived: bool, states: set[TaskStateEnum]) -> None:
    query = TaskQuery(
        list_id="l", show_done=show_done, show_archived=show_archived, sort_key=TaskSortKeyEnum.TEXT, descending=False
    )

    assert query.states == states
