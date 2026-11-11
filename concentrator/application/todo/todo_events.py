"""Events published by the TODO use cases."""

from dataclasses import dataclass

from concentrator.domain.todo.task_state_enum import TaskStateEnum


@dataclass(frozen=True, slots=True)
class TaskListChangedEvent:
    """Lists were created, changed, moved or deleted.

    Attributes:
        list_ids: Lists concerned.
    """

    list_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TaskCreatedEvent:
    """A task was created (new, quick add or duplicate).

    Attributes:
        task_id: The new task.
    """

    task_id: str


@dataclass(frozen=True, slots=True)
class TaskChangedEvent:
    """Tasks changed their text, due date or list.

    Attributes:
        task_ids: Tasks concerned.
    """

    task_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TaskStateChangedEvent:
    """One task changed its state (one event per task of a bulk change).

    Attributes:
        task_id: The task.
        old_state: State before the change.
        new_state: State after the change.
    """

    task_id: str
    old_state: TaskStateEnum
    new_state: TaskStateEnum


@dataclass(frozen=True, slots=True)
class TaskOccurrenceCompletedEvent:
    """An occurrence of a recurring task was completed (the task moved to its next date, or became done).

    Attributes:
        task_id: The task.
        occurrence: Number of the occurrence completed (1 for the first).
    """

    task_id: str
    occurrence: int


@dataclass(frozen=True, slots=True)
class TaskDeletedEvent:
    """Tasks were deleted (by the user, or with their list).

    Attributes:
        task_ids: Deleted tasks.
    """

    task_ids: tuple[str, ...]
