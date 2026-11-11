"""``FocusItemSchema`` elements <-> ``FocusItemsCollection``."""

import logging
from collections.abc import Sequence
from typing import Final

from concentrator.domain.common.data_result import DataResult
from concentrator.domain.focus.focus_item import FocusItem, FocusItemId
from concentrator.domain.focus.focus_items_collection import FocusItemsCollection
from concentrator.domain.focus.focus_limits import FocusLimits
from concentrator.domain.focus.focus_rules import FocusRules
from concentrator.domain.todo.task import TaskId
from concentrator.domain.todo.task_state_enum import TaskStateEnum
from concentrator.domain.todo.tasks_collection import TasksCollection
from concentrator.infrastructure.persistence.schemas.focus_item_schema import FocusItemSchema

_logger = logging.getLogger(__name__)

_FIELD_SEPARATOR: Final = "."


class FocusQueueMapper:
    """Converts the ``[[focus_queue]]`` elements."""

    @staticmethod
    def to_domain(
        schemas: Sequence[FocusItemSchema], field_prefix: str, tasks: TasksCollection, limits: FocusLimits
    ) -> DataResult[FocusItemsCollection]:
        """Build the queue, keeping the items that work (phase 7 spec, lenient like the favorites).

        An item whose task is missing (``FOCUS_TASK_MISSING``) or not open, a repeated item and the items
        beyond ``focus.max_items`` are left out with a WARNING in the log; the next save drops them from
        the file. Positions are renumbered ``0, 1, 2...``.

        Args:
            schemas: Validated DTOs, in file order.
            field_prefix: Dotted path of the collection in the file (``focus_queue``).
            tasks: Tasks of the file, already mapped.
            limits: Bounds from ``concentrator.ini``.

        Returns:
            The kept items (always a success).
        """
        items = [
            FocusItem(
                id=FocusItemId(schema.id),
                created_at=schema.created_at,
                updated_at=schema.updated_at,
                task_id=TaskId(schema.task_id),
                position=schema.position,
            )
            for schema in schemas
        ]
        open_by_task: dict[str, bool] = {task.id: task.state is TaskStateEnum.OPEN for task in tasks}
        usable = FocusRules.usable(items, open_by_task, limits)
        for issue in usable.validation.issues:
            index = issue.field.partition(_FIELD_SEPARATOR)[0]
            _logger.warning(
                "Focus item %s.%s (%s) of the data file ignored: %s",
                field_prefix,
                index,
                items[int(index)].id,
                issue.code.name,
            )
        return DataResult.ok(usable.value_or(FocusItemsCollection()))

    @staticmethod
    def to_schema(queue: FocusItemsCollection) -> tuple[FocusItemSchema, ...]:
        """Build the DTOs written to the file, in queue order.

        Args:
            queue: The queue.

        Returns:
            The DTOs sorted by position.
        """
        return tuple(
            FocusItemSchema(
                id=item.id,
                created_at=item.created_at,
                updated_at=item.updated_at,
                task_id=item.task_id,
                position=item.position,
            )
            for item in queue.ordered()
        )
