"""A TODO list, shown as a tab of zone 1."""

from dataclasses import dataclass, replace
from datetime import datetime
from typing import NewType, Self

from concentrator.domain.common.multiline_text import MultilineText
from concentrator.domain.todo.priority_enum import PriorityEnum

TaskListId = NewType("TaskListId", str)


def normalize_list_name(text: str) -> str:
    """Clean a list name: no leading or trailing spaces, one space between words, no line break.

    Args:
        text: Name as typed.

    Returns:
        The name to store.
    """
    return " ".join(text.split())


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskList:
    """One list (``[[task_lists]]``); checked by ``TaskListRules``.

    Attributes:
        id: UUIDv7 identifying the list.
        created_at: Creation instant, timezone-aware UTC.
        updated_at: Last change instant, timezone-aware UTC.
        name: Tab text, unique among the lists without regard to case.
        description: Shown under the tabs and as the tab tooltip.
        priority: The tabs show the most urgent lists first.
        position: Order of the lists of the same priority (lowest first).
    """

    id: TaskListId
    created_at: datetime
    updated_at: datetime
    name: str
    description: MultilineText
    priority: PriorityEnum
    position: int

    @classmethod
    def create(
        cls,
        new_id: TaskListId,
        now: datetime,
        *,
        name: str,
        description: MultilineText,
        priority: PriorityEnum,
        position: int,
    ) -> Self:
        """Create a list.

        Args:
            new_id: Id from ``IdGeneratorPort``.
            now: Creation instant (timezone-aware UTC).
            name: Name as typed (normalized here).
            description: Description.
            priority: Priority.
            position: Sort key (``TaskListsCollection.next_position()`` for a new last list).

        Returns:
            The list; validate it with ``TaskListRules``.
        """
        return cls(
            id=new_id,
            created_at=now,
            updated_at=now,
            name=normalize_list_name(name),
            description=description,
            priority=priority,
            position=position,
        )

    def with_values(self, name: str, description: MultilineText, priority: PriorityEnum, now: datetime) -> Self:
        """Return a copy with other editable values (list dialog).

        Args:
            name: Name as typed (normalized here).
            description: New description.
            priority: New priority.
            now: Change instant (timezone-aware UTC).

        Returns:
            The changed list.
        """
        return replace(self, name=normalize_list_name(name), description=description, priority=priority, updated_at=now)

    def with_position(self, position: int, now: datetime) -> Self:
        """Return a copy at another position.

        Args:
            position: New sort key.
            now: Change instant (timezone-aware UTC).

        Returns:
            The moved list.
        """
        return replace(self, position=position, updated_at=now)

    def business_copy(self, new_id: str, now: datetime) -> Self:
        """Return a duplicate with a new identity (``BusinessCopyable``).

        Args:
            new_id: Id of the duplicate.
            now: Creation instant of the duplicate.

        Returns:
            The duplicate; its name must be changed before it is stored (names are unique).
        """
        return replace(self, id=TaskListId(new_id), created_at=now, updated_at=now)
