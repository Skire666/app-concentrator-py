"""Business rules of the focus queue."""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Final

from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.entity_rules import ID_FIELD, EntityRules
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.severity_enum import SeverityEnum
from concentrator.domain.common.validation_issue import ValidationIssue
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.focus.focus_item import FocusItem
from concentrator.domain.focus.focus_items_collection import FocusItemsCollection
from concentrator.domain.focus.focus_limits import FocusLimits

TASK_ID_FIELD: Final = "task_id"


class FocusRules:
    """Stateless validation of the queue: only open tasks, no duplicate, a capacity.

    The rules see a task through its id and whether it is open (``AGENTS.md`` section 4.2: ``domain.focus``
    imports only identifiers of ``domain.todo``); the callers read the task.
    """

    @staticmethod
    def validate_add(
        task_id: str, *, is_open: bool, queue: FocusItemsCollection, limits: FocusLimits
    ) -> ValidationResult:
        """Check that a task can be queued.

        Args:
            task_id: Task to queue.
            is_open: Whether the task is open.
            queue: Current queue.
            limits: Bounds from ``concentrator.ini``.

        Returns:
            Success, ``FOCUS_TASK_NOT_OPEN``, ``FOCUS_TASK_ALREADY_QUEUED`` or ``FOCUS_QUEUE_FULL`` (``max``).
        """
        if not is_open:
            return ValidationResult.failure(ErrorCodeEnum.FOCUS_TASK_NOT_OPEN, field=TASK_ID_FIELD)
        if queue.contains_task(task_id):
            return ValidationResult.failure(ErrorCodeEnum.FOCUS_TASK_ALREADY_QUEUED, field=TASK_ID_FIELD)
        return FocusRules.validate_room(queue, 1, limits)

    @staticmethod
    def validate_room(queue: FocusItemsCollection, count: int, limits: FocusLimits) -> ValidationResult:
        """Check that some more items fit in the queue.

        Args:
            queue: Current queue.
            count: Number of items to add.
            limits: Bounds from ``concentrator.ini``.

        Returns:
            Success or ``FOCUS_QUEUE_FULL`` (``max``).
        """
        if len(queue) + count <= limits.max_items:
            return ValidationResult.success()
        return ValidationResult.failure(ErrorCodeEnum.FOCUS_QUEUE_FULL, max=limits.max_items)

    @staticmethod
    def can_queue(task_id: str, *, is_open: bool, queued: frozenset[str]) -> bool:
        """Tell whether a task is open and not queued yet (capacity aside).

        Args:
            task_id: Task.
            is_open: Whether the task is open.
            queued: Ids of the queued tasks (``FocusItemsCollection.task_ids()``, read once per query).

        Returns:
            Whether "Add to focus" applies to it.
        """
        return is_open and task_id not in queued

    @staticmethod
    def usable(
        items: Sequence[FocusItem], open_by_task: Mapping[str, bool], limits: FocusLimits
    ) -> DataResult[FocusItemsCollection]:
        """Keep the items read from a file that work, in position order (phase 7, lenient like the favorites).

        An item whose task is missing (``FOCUS_TASK_MISSING``) or not open, a repeated id or task, an item
        with a bad identity or beyond ``focus.max_items`` is left out; the first items by position win.
        Positions are renumbered from 0 (with the same ``updated_at``: nothing was edited). The items stay a
        sequence until checked: a file may repeat an id, which a collection refuses.

        Args:
            items: Items in file order.
            open_by_task: Every task of the file by id, ``True`` for an open task.
            limits: Bounds from ``concentrator.ini``.

        Returns:
            The kept items, with one WARNING issue per ignored item (fields ``<position in the file>.<field>``).
        """
        kept: list[FocusItem] = []
        warnings: list[ValidationIssue] = []
        for index, item in sorted(enumerate(items), key=lambda pair: pair[1].position):
            refused = FocusRules._refusal(item, open_by_task.get(item.task_id), kept, limits)
            if refused.is_failure:
                warnings.extend(
                    replace(issue, severity=SeverityEnum.WARNING) for issue in refused.prefixed(str(index)).issues
                )
                continue
            kept.append(replace(item, position=len(kept)))
        return DataResult.ok(FocusItemsCollection(kept), ValidationResult.of(*warnings))

    @staticmethod
    def _refusal(
        item: FocusItem, is_open: bool | None, kept: Sequence[FocusItem], limits: FocusLimits
    ) -> ValidationResult:
        """Tell why an item read from a file cannot be kept.

        Args:
            item: Item read from the file.
            is_open: Whether its task is open, ``None`` when the task is missing.
            kept: Items kept so far.
            limits: Bounds from ``concentrator.ini``.

        Returns:
            Success or the reason.
        """
        identity = EntityRules.validate_identity(item)
        if identity.is_failure:
            return identity
        if is_open is None:
            return ValidationResult.failure(ErrorCodeEnum.FOCUS_TASK_MISSING, field=TASK_ID_FIELD)
        if any(other.id == item.id for other in kept):
            return ValidationResult.failure(ErrorCodeEnum.ENTITY_DUPLICATE_ID, field=ID_FIELD)
        return FocusRules.validate_add(item.task_id, is_open=is_open, queue=FocusItemsCollection(kept), limits=limits)
