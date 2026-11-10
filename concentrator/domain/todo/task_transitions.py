"""State transitions of a task (phase 5 spec table)."""

from typing import Final

from concentrator.domain.todo.task_event_kind_enum import TaskEventKindEnum
from concentrator.domain.todo.task_state_enum import TaskStateEnum

TRANSITION_KINDS: Final = frozenset(
    {TaskEventKindEnum.COMPLETED, TaskEventKindEnum.REOPENED, TaskEventKindEnum.ARCHIVED, TaskEventKindEnum.UNARCHIVED}
)
"""Event kinds that change the state of a task."""

_TARGETS: Final = {
    (TaskStateEnum.OPEN, TaskEventKindEnum.COMPLETED): TaskStateEnum.DONE,
    (TaskStateEnum.DONE, TaskEventKindEnum.REOPENED): TaskStateEnum.OPEN,
    (TaskStateEnum.OPEN, TaskEventKindEnum.ARCHIVED): TaskStateEnum.ARCHIVED,
    (TaskStateEnum.DONE, TaskEventKindEnum.ARCHIVED): TaskStateEnum.ARCHIVED,
}


def transition_target(state: TaskStateEnum, kind: TaskEventKindEnum, *, was_completed: bool) -> TaskStateEnum | None:
    """Tell where a transition leads.

    Args:
        state: Current state.
        kind: Transition (``COMPLETED``, ``REOPENED``, ``ARCHIVED`` or ``UNARCHIVED``).
        was_completed: Whether the task has a completion instant (an unarchived task returns to ``DONE``).

    Returns:
        The new state, or ``None`` when the transition is not allowed from ``state``.
    """
    if state is TaskStateEnum.ARCHIVED and kind is TaskEventKindEnum.UNARCHIVED:
        return TaskStateEnum.DONE if was_completed else TaskStateEnum.OPEN
    return _TARGETS.get((state, kind))
