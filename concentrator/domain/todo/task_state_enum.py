"""State of a task."""

from concentrator.domain.common.base_int_enum import BaseIntEnum


class TaskStateEnum(BaseIntEnum):
    """Life cycle of a task (transitions in ``task_transitions.py``)."""

    UNKNOWN = -1
    UNSET = 0
    OPEN = 1
    DONE = 2
    ARCHIVED = 3
