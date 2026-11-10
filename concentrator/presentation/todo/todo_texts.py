"""Catalog keys of the TODO enums (written as literals so that the catalog test checks them)."""

from types import MappingProxyType
from typing import Final

from concentrator.domain.todo.priority_enum import PriorityEnum
from concentrator.domain.todo.task_state_enum import TaskStateEnum

PRIORITIES: Final = (PriorityEnum.LOW, PriorityEnum.NORMAL, PriorityEnum.HIGH, PriorityEnum.URGENT)
"""Priorities offered by the list dialog, lowest first."""

PRIORITY_KEYS: Final = MappingProxyType(
    {
        PriorityEnum.LOW: "todo.priority.low",
        PriorityEnum.NORMAL: "todo.priority.normal",
        PriorityEnum.HIGH: "todo.priority.high",
        PriorityEnum.URGENT: "todo.priority.urgent",
    }
)
"""Name of each priority."""

PRIORITY_BADGE_KEYS: Final = MappingProxyType(
    {
        PriorityEnum.LOW: "todo.priority.badge.low",
        PriorityEnum.HIGH: "todo.priority.badge.high",
        PriorityEnum.URGENT: "todo.priority.badge.urgent",
    }
)
"""Short mark shown in a tab before the name (none for NORMAL)."""

STATE_KEYS: Final = MappingProxyType(
    {
        TaskStateEnum.OPEN: "todo.state.open",
        TaskStateEnum.DONE: "todo.state.done",
        TaskStateEnum.ARCHIVED: "todo.state.archived",
    }
)
"""Name of each task state."""

UNKNOWN_KEY: Final = "todo.value.unknown"
"""Shown for a value a newer version wrote."""
