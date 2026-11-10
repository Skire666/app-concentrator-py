"""The TODO lists, ordered by priority then position."""

from datetime import datetime
from typing import Final, Self

from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.entity_collection import EntityCollection
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.todo.task_list import TaskList, normalize_list_name

FIRST_POSITION: Final = 0
LIST_ID_FIELD: Final = "id"


def _display_key(task_list: TaskList) -> tuple[int, int]:
    """Sort key of the tabs: the most urgent priority first, then the position.

    Args:
        task_list: A list.

    Returns:
        The key.
    """
    return (-task_list.priority.value, task_list.position)


class TaskListsCollection(EntityCollection[TaskList]):
    """Group logic of the lists: display order, next position, name lookup, moves.

    Positions are numbered across every list; the display order is the priority (URGENT first), then the
    position, so a move only swaps two lists of the same priority. ``TaskListRules`` checks the unique
    names and that one list always remains.
    """

    def ordered(self) -> Self:
        """Sort in display order (stable).

        Returns:
            The lists as the tabs show them.
        """
        return self.sorted_by(_display_key)

    def first(self) -> TaskList | None:
        """First tab.

        Returns:
            The first list in display order, ``None`` when there is none.
        """
        return next(iter(self.ordered()), None)

    def next_position(self) -> int:
        """Return the position of a list added last among its priority.

        Returns:
            One more than the highest position, ``0`` when empty.
        """
        return max((task_list.position for task_list in self), default=FIRST_POSITION - 1) + 1

    def with_name(self, name: str, except_id: str = "") -> TaskList | None:
        """Find the list with a name, without regard to case or extra spaces.

        Args:
            name: Name to look for.
            except_id: List to ignore (the one being edited).

        Returns:
            The list, or ``None``.
        """
        wanted = normalize_list_name(name).casefold()
        return next((item for item in self if item.name.casefold() == wanted and item.id != except_id), None)

    def neighbor(self, list_id: str, offset: int) -> TaskList | None:
        """Find the tab ``offset`` places away that has the same priority.

        Args:
            list_id: List to move.
            offset: ``-1`` for the previous tab, ``1`` for the next one.

        Returns:
            The neighbor, or ``None`` at the edge of the priority group or when the list is unknown.
        """
        ordered = self.ordered().items
        index = next((position for position, item in enumerate(ordered) if item.id == list_id), None)
        if index is None or not 0 <= index + offset < len(ordered):
            return None
        other = ordered[index + offset]
        return other if other.priority is ordered[index].priority else None

    def moved(self, list_id: str, offset: int, now: datetime) -> DataResult[Self]:
        """Swap a list with its neighbor of the same priority and renumber the positions ``0, 1, 2...``.

        Args:
            list_id: List to move.
            offset: ``-1`` (earlier) or ``1`` (later).
            now: Change instant; the lists whose position changes get it as ``updated_at``.

        Returns:
            The lists, ``ENTITY_NOT_FOUND``, or a skipped result at the edge of the priority group.
        """
        if not self.contains(list_id):
            return DataResult.fail(ValidationResult.failure(ErrorCodeEnum.ENTITY_NOT_FOUND, field=LIST_ID_FIELD))
        other = self.neighbor(list_id, offset)
        if other is None:
            return DataResult.fail(ValidationResult.skipped())
        ordered = list(self.ordered())
        first = next(position for position, item in enumerate(ordered) if item.id == list_id)
        second = first + offset
        ordered[first], ordered[second] = ordered[second], ordered[first]
        renumbered = (
            item if item.position == position else item.with_position(position, now)
            for position, item in enumerate(ordered)
        )
        return DataResult.ok(self._with_items(renumbered))
