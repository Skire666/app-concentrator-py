"""Columns a task table can be sorted by."""

from concentrator.domain.common.base_int_enum import BaseIntEnum


class TaskSortKeyEnum(BaseIntEnum):
    """Sort key of the tasks of a list (``TasksCollection.ordered_by``)."""

    UNKNOWN = -1
    UNSET = 0
    STATE = 1
    TEXT = 2
    DUE = 3
    CREATED = 4
    UPDATED = 5
