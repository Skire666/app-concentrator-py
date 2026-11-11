"""TODO use cases over the real in-memory store, with every published event recorded."""

from collections.abc import Sequence
from datetime import datetime
from typing import override

from concentrator.application.common.event_bus import EventBus
from concentrator.application.ports.task_writer_port import TaskWriterPort
from concentrator.application.todo.link_commands import LinkCommands
from concentrator.application.todo.task_commands import TaskCommands
from concentrator.application.todo.task_list_commands import TaskListCommands, TodoStores
from concentrator.application.todo.task_schedule_commands import TaskScheduleCommands
from concentrator.application.todo.todo_events import (
    TaskChangedEvent,
    TaskCreatedEvent,
    TaskDeletedEvent,
    TaskListChangedEvent,
    TaskOccurrenceCompletedEvent,
    TaskStateChangedEvent,
)
from concentrator.application.todo.todo_queries import TodoQueries
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.todo.link_detector import LinkDetector
from concentrator.domain.todo.task import Task
from concentrator.domain.todo.task_list import TaskList
from concentrator.domain.todo.task_lists_collection import TaskListsCollection
from concentrator.domain.todo.tasks_collection import TasksCollection
from concentrator.infrastructure.persistence.store_todo import (
    StoreTaskListReader,
    StoreTaskListWriter,
    StoreTaskReader,
    StoreTaskWriter,
)
from concentrator.infrastructure.persistence.user_data_store import UserDataStore
from tests.fakes.fake_clock import FakeClock
from tests.fakes.fake_desktop import FakeLinkOpener
from tests.fakes.fake_id_generator import FakeIdGenerator
from tests.fakes.recording_error_reporter import RecordingErrorReporter
from tests.fakes.todo_factory import TODO_LIMITS, make_lists
from tests.fakes.user_data_factory import make_user_data

type TodoEvent = (
    TaskListChangedEvent
    | TaskCreatedEvent
    | TaskChangedEvent
    | TaskStateChangedEvent
    | TaskOccurrenceCompletedEvent
    | TaskDeletedEvent
)

TODO_EVENT_TYPES = (
    TaskListChangedEvent,
    TaskCreatedEvent,
    TaskChangedEvent,
    TaskStateChangedEvent,
    TaskOccurrenceCompletedEvent,
    TaskDeletedEvent,
)
LINKS = LinkDetector.of(("http", "https"))

WRITE_FAILED = ValidationResult.failure(ErrorCodeEnum.STORAGE_WRITE_FAILED)


class ScriptedTaskWriter(TaskWriterPort):
    """The store writer, except that every write fails while ``fail`` is set."""

    def __init__(self, inner: StoreTaskWriter) -> None:
        self._inner = inner
        self.fail = False

    @override
    def create(self, entity: Task) -> DataResult[Task]:
        return DataResult.fail(WRITE_FAILED) if self.fail else self._inner.create(entity)

    @override
    def update(self, entity: Task) -> DataResult[Task]:
        return DataResult.fail(WRITE_FAILED) if self.fail else self._inner.update(entity)

    @override
    def delete(self, entity_id: str) -> DataResult[Task]:
        return DataResult.fail(WRITE_FAILED) if self.fail else self._inner.delete(entity_id)

    @override
    def copy_business(self, entity_id: str, new_id: str, now: datetime) -> DataResult[Task]:
        return DataResult.fail(WRITE_FAILED) if self.fail else self._inner.copy_business(entity_id, new_id, now)

    @override
    def copy_technical(self, entity_id: str) -> DataResult[Task]:
        return self._inner.copy_technical(entity_id)

    @override
    def update_many(self, entities: Sequence[Task]) -> DataResult[tuple[Task, ...]]:
        return DataResult.fail(WRITE_FAILED) if self.fail else self._inner.update_many(entities)

    @override
    def delete_many(self, entity_ids: Sequence[str]) -> DataResult[tuple[Task, ...]]:
        return DataResult.fail(WRITE_FAILED) if self.fail else self._inner.delete_many(entity_ids)


class TodoStack:
    """Lists and tasks in a ``UserDataStore``, the use cases, and the events they publish."""

    def __init__(self, lists: Sequence[TaskList] = (), tasks: Sequence[Task] = ()) -> None:
        self.bus = EventBus(RecordingErrorReporter())
        self.events: list[TodoEvent] = []
        for event_type in TODO_EVENT_TYPES:
            self.bus.subscribe(event_type, self.events.append)
        self.store = UserDataStore(self.bus)
        collection = TaskListsCollection(lists) if lists else make_lists()
        self.store.reset(make_user_data().with_task_lists(collection).with_tasks(TasksCollection(tasks)))
        self.clock = FakeClock()
        self.ids = FakeIdGenerator("new")
        self.task_writer = ScriptedTaskWriter(StoreTaskWriter(self.store))
        stores = TodoStores(
            lists=StoreTaskListReader(self.store),
            list_writer=StoreTaskListWriter(self.store),
            tasks=StoreTaskReader(self.store),
            task_writer=self.task_writer,
        )
        self.list_commands = TaskListCommands(
            stores=stores, ids=self.ids, clock=self.clock, event_bus=self.bus, limits=TODO_LIMITS
        )
        self.task_commands = TaskCommands(
            stores=stores, ids=self.ids, clock=self.clock, event_bus=self.bus, limits=TODO_LIMITS, links=LINKS
        )
        self.schedule_commands = TaskScheduleCommands(
            stores=stores, clock=self.clock, event_bus=self.bus, limits=TODO_LIMITS
        )
        self.opener = FakeLinkOpener()
        self.link_commands = LinkCommands(tasks=stores.tasks, links=LINKS, opener=self.opener)
        self.queries = TodoQueries(stores.lists, stores.tasks)

    def tasks(self) -> TasksCollection:
        """Every stored task."""
        return self.queries.all_tasks()

    def task(self, task_id: str) -> Task:
        """One stored task (the test fails if it is missing)."""
        found = self.queries.task(task_id).data
        assert found is not None
        return found

    def lists(self) -> TaskListsCollection:
        """Every list, in tab order."""
        return self.queries.lists()
