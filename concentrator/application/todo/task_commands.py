"""Write use cases of the tasks."""

import logging
from collections.abc import Sequence
from dataclasses import replace
from datetime import date, datetime

from concentrator.application.common.event_bus import EventBus
from concentrator.application.ports.clock_port import ClockPort
from concentrator.application.ports.id_generator_port import IdGeneratorPort
from concentrator.application.todo.task_list_commands import TodoStores
from concentrator.application.todo.task_lookup import find_tasks
from concentrator.application.todo.todo_events import (
    TaskChangedEvent,
    TaskCreatedEvent,
    TaskDeletedEvent,
    TaskOccurrenceCompletedEvent,
    TaskStateChangedEvent,
)
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.multiline_text import MultilineText
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.todo.link_detector import LinkDetector
from concentrator.domain.todo.task import Task, TaskId
from concentrator.domain.todo.task_draft import TaskDraft
from concentrator.domain.todo.task_event_kind_enum import TaskEventKindEnum
from concentrator.domain.todo.task_list import TaskListId
from concentrator.domain.todo.task_lists_collection import TaskListsCollection
from concentrator.domain.todo.task_rules import TaskRules
from concentrator.domain.todo.todo_limits import TodoLimits

_logger = logging.getLogger(__name__)


class TaskCommands:
    """Create, edit, delete, change the state of, move and duplicate tasks.

    Bulk commands check every task first and change all of them in one write, or none. Texts never reach
    the log. The paths of a created or edited text are written with ``/`` (``LinkDetector.normalized``).
    """

    def __init__(
        self,
        *,
        stores: TodoStores,
        ids: IdGeneratorPort,
        clock: ClockPort,
        event_bus: EventBus,
        limits: TodoLimits,
        links: LinkDetector,
    ) -> None:
        """Create the use cases.

        Args:
            stores: Readers and writers of the lists and tasks.
            ids: Ids of new tasks.
            clock: Change instants.
            event_bus: Receives the events.
            limits: Bounds from ``concentrator.ini``.
            links: Finds the paths to normalize in a text.
        """
        self._stores = stores
        self._ids = ids
        self._clock = clock
        self._event_bus = event_bus
        self._limits = limits
        self._links = links

    def quick_add(self, list_id: str, text: str) -> DataResult[Task]:
        """Create a task from the quick add field (no due date).

        Args:
            list_id: Current list.
            text: Text as typed (a pasted text may hold several lines).

        Returns:
            The stored task, or the rule failures (``TASK_TEXT_EMPTY``, ``TASK_LIST_NOT_FOUND``...).
        """
        return self.create(TaskDraft(list_id=TaskListId(list_id), text=MultilineText.from_text(text.strip())))

    def create(self, draft: TaskDraft) -> DataResult[Task]:
        """Create a task from the editor.

        Args:
            draft: Values entered.

        Returns:
            The stored task, or the rule failures.
        """
        draft = self._normalized(draft)
        validation = self._validate_draft(draft)
        if validation.is_failure:
            return DataResult.fail(validation)
        task = Task.create(TaskId(self._ids.new_id()), self._clock.now_utc(), draft)
        return self._created(self._stores.task_writer.create(task))

    def update(self, task_id: str, draft: TaskDraft) -> DataResult[Task]:
        """Apply the values of the editor; each changed part adds a history event.

        Args:
            task_id: Task to change.
            draft: New values.

        Returns:
            The stored task (unchanged values are not written), ``ENTITY_NOT_FOUND`` or the rule failures.
        """
        current = self._stores.tasks.read_item(task_id)
        if current.data is None:
            return current
        draft = self._normalized(draft)
        changed = current.data.with_draft(draft, self._clock.now_utc(), self._limits.max_history_events)
        if changed is current.data:
            return current
        validation = self._validate_draft(draft)
        if validation.is_failure:
            return DataResult.fail(validation)
        written = self._stores.task_writer.update(changed)
        if written.data is not None:
            _logger.info("Task edited")
            self._event_bus.publish(TaskChangedEvent(task_ids=(task_id,)))
        return written

    def delete(self, task_ids: Sequence[str]) -> ValidationResult:
        """Delete tasks.

        Args:
            task_ids: Tasks to delete.

        Returns:
            Success, skipped for no task, or ``ENTITY_NOT_FOUND`` (nothing deleted).
        """
        if not task_ids:
            return ValidationResult.skipped()
        removed = self._stores.task_writer.delete_many(task_ids)
        if removed.data is None:
            return removed.validation
        _logger.info("%d tasks deleted", len(removed.data))
        self._event_bus.publish(TaskDeletedEvent(task_ids=tuple(task_ids)))
        return ValidationResult.success()

    def complete(self, task_ids: Sequence[str], *, source: str = "") -> ValidationResult:
        """Mark open tasks done; a recurring task completes its current occurrence and moves to its next date.

        Args:
            task_ids: Tasks to complete (all must be open).
            source: Where the completion was made (``SOURCE_FOCUS`` for the focus queue), ``""`` for zone 1;
                it is recorded in the completion events.

        Returns:
            Success, skipped for no task, ``ENTITY_NOT_FOUND`` or ``TASK_STATE_TRANSITION_INVALID``.
        """
        return self._transition(task_ids, TaskEventKindEnum.COMPLETED, source=source)

    def reopen(self, task_ids: Sequence[str]) -> ValidationResult:
        """Reopen done tasks.

        Args:
            task_ids: Tasks to reopen (all must be done).

        Returns:
            Success, skipped for no task, ``ENTITY_NOT_FOUND`` or ``TASK_STATE_TRANSITION_INVALID``.
        """
        return self._transition(task_ids, TaskEventKindEnum.REOPENED)

    def archive(self, task_ids: Sequence[str]) -> ValidationResult:
        """Archive open or done tasks.

        Args:
            task_ids: Tasks to archive.

        Returns:
            Success, skipped for no task, ``ENTITY_NOT_FOUND`` or ``TASK_STATE_TRANSITION_INVALID``.
        """
        return self._transition(task_ids, TaskEventKindEnum.ARCHIVED)

    def unarchive(self, task_ids: Sequence[str]) -> ValidationResult:
        """Bring archived tasks back (done if they were completed, open otherwise).

        Args:
            task_ids: Tasks to unarchive (all must be archived).

        Returns:
            Success, skipped for no task, ``ENTITY_NOT_FOUND`` or ``TASK_STATE_TRANSITION_INVALID``.
        """
        return self._transition(task_ids, TaskEventKindEnum.UNARCHIVED)

    def move_to_list(self, task_ids: Sequence[str], list_id: str) -> ValidationResult:
        """Move tasks to another list (tasks already there are left alone).

        Args:
            task_ids: Tasks to move.
            list_id: Target list.

        Returns:
            Success, skipped when nothing moves, ``TASK_LIST_NOT_FOUND`` or ``ENTITY_NOT_FOUND``.
        """
        lists = self._stores.lists.all_items().value_or(TaskListsCollection())
        target = TaskRules.validate_list_exists(lists, list_id)
        if target.is_failure:
            return target
        found = find_tasks(self._stores.tasks, task_ids)
        if found.data is None:
            return found.validation
        now = self._clock.now_utc()
        moved = [
            task.moved_to(TaskListId(list_id), now, self._limits.max_history_events)
            for task in found.data
            if task.list_id != list_id
        ]
        return self._changed(moved)

    def duplicate(self, task_id: str) -> DataResult[Task]:
        """Duplicate a task (``copy_business``): new id, open, history restarted with ``COPIED_FROM``.

        Args:
            task_id: Task to duplicate.

        Returns:
            The stored duplicate, or ``ENTITY_NOT_FOUND``.
        """
        return self._created(self._stores.task_writer.copy_business(task_id, self._ids.new_id(), self._clock.now_utc()))

    def _validate_draft(self, draft: TaskDraft) -> ValidationResult:
        """Check the values of a task and its list.

        Args:
            draft: Values entered.

        Returns:
            The merged result.
        """
        lists = self._stores.lists.all_items().value_or(TaskListsCollection())
        return TaskRules.validate_draft(draft, self._limits).merge(TaskRules.validate_list_exists(lists, draft.list_id))

    def _normalized(self, draft: TaskDraft) -> TaskDraft:
        """Write the paths of a text with ``/``.

        Args:
            draft: Values entered.

        Returns:
            The draft to store.
        """
        text = self._links.normalized(draft.text)
        return draft if text is draft.text else replace(draft, text=text)

    def _transition(self, task_ids: Sequence[str], kind: TaskEventKindEnum, *, source: str = "") -> ValidationResult:
        """Change the state of every task, or of none.

        Args:
            task_ids: Tasks to change.
            kind: Transition.
            source: Where a completion was made, ``""`` for zone 1.

        Returns:
            Success, skipped, ``ENTITY_NOT_FOUND`` or ``TASK_STATE_TRANSITION_INVALID``.
        """
        found = find_tasks(self._stores.tasks, task_ids)
        if found.data is None:
            return found.validation
        moment = (self._clock.now_utc(), self._clock.now_local().date())
        changed: list[Task] = []
        for task in found.data:
            result = self._transitioned(task, kind, moment, source)
            if result.data is None:
                return result.validation
            changed.append(result.data)
        written = self._stores.task_writer.update_many(changed)
        if written.data is None:
            return written.validation
        _logger.info("%d tasks %s", len(changed), kind.name.lower())
        for before, after in zip(found.data, changed, strict=True):
            self._publish_state(before, after)
        return ValidationResult.success()

    def _transitioned(
        self, task: Task, kind: TaskEventKindEnum, moment: tuple[datetime, date], source: str
    ) -> DataResult[Task]:
        """Apply one transition (a completion of a recurring task completes its occurrence).

        Args:
            task: Task to change.
            kind: Transition.
            moment: Change instant (UTC) and current local date, the same for every task of the command.
            source: Where a completion was made, ``""`` for zone 1.

        Returns:
            The changed task, or ``TASK_STATE_TRANSITION_INVALID``.
        """
        now, today = moment
        if kind is TaskEventKindEnum.COMPLETED:
            return task.completed(now, today, self._limits.max_history_events, source=source)
        return task.transitioned(kind, now, self._limits.max_history_events)

    def _publish_state(self, before: Task, after: Task) -> None:
        """Publish what a transition changed: the state, an occurrence, or both.

        Args:
            before: Task before the change.
            after: Task after the change.
        """
        if after.occurrences_done != before.occurrences_done:
            self._event_bus.publish(TaskOccurrenceCompletedEvent(task_id=after.id, occurrence=after.occurrences_done))
        if after.state is not before.state:
            self._event_bus.publish(
                TaskStateChangedEvent(task_id=after.id, old_state=before.state, new_state=after.state)
            )

    def _changed(self, tasks: Sequence[Task]) -> ValidationResult:
        """Write changed tasks in one write and publish ``TaskChangedEvent``.

        Args:
            tasks: Changed tasks.

        Returns:
            Success, skipped when there is nothing to write, or the writer failure.
        """
        if not tasks:
            return ValidationResult.skipped()
        written = self._stores.task_writer.update_many(tasks)
        if written.data is None:
            return written.validation
        _logger.info("%d tasks moved", len(tasks))
        self._event_bus.publish(TaskChangedEvent(task_ids=tuple(task.id for task in tasks)))
        return ValidationResult.success()

    def _created(self, written: DataResult[Task]) -> DataResult[Task]:
        """Publish the creation of a successful write.

        Args:
            written: Writer result.

        Returns:
            The writer result.
        """
        if written.data is not None:
            _logger.info("Task created")
            self._event_bus.publish(TaskCreatedEvent(task_id=written.data.id))
        return written
