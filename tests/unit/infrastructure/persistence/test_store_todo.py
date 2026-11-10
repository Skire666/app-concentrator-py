"""Readers and writers of the lists and tasks on the in-memory store, bulk changes included."""

from dataclasses import replace
from datetime import UTC, datetime

from concentrator.application.common.event_bus import EventBus
from concentrator.application.storage.storage_events import UserDataChangedEvent
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.todo.task import Task
from concentrator.domain.todo.task_lists_collection import TaskListsCollection
from concentrator.domain.todo.task_state_enum import TaskStateEnum
from concentrator.domain.todo.tasks_collection import TasksCollection
from concentrator.infrastructure.persistence.store_todo import (
    StoreTaskListReader,
    StoreTaskListWriter,
    StoreTaskReader,
    StoreTaskWriter,
)
from concentrator.infrastructure.persistence.user_data_store import UserDataStore
from tests.fakes.recording_error_reporter import RecordingErrorReporter
from tests.fakes.todo_factory import SPEC_LIST_ID, make_list, make_task
from tests.fakes.user_data_factory import make_user_data

NOW = datetime(2026, 11, 10, 9, 0, tzinfo=UTC)


class _Matching:
    def __init__(self, state: TaskStateEnum) -> None:
        self._state = state

    def matches(self, entity: Task) -> bool:
        return entity.state is self._state


def _store(*tasks: Task) -> tuple[UserDataStore, list[UserDataChangedEvent]]:
    bus = EventBus(RecordingErrorReporter())
    events: list[UserDataChangedEvent] = []
    bus.subscribe(UserDataChangedEvent, events.append)
    store = UserDataStore(bus)
    store.reset(make_user_data().with_tasks(TasksCollection(tasks)))
    return store, events


def test_task_reader_returns_the_stored_collection_and_finds_by_query() -> None:
    store, _events = _store(make_task(1, list_id=SPEC_LIST_ID), make_task(2, state=TaskStateEnum.DONE))
    reader = StoreTaskReader(store)

    every = reader.all_items().data
    done = reader.find(_Matching(TaskStateEnum.DONE)).data

    assert every is store.current().tasks
    assert done is not None
    assert [task.id for task in done] == ["task-002"]
    assert reader.exists("task-001").data is True
    assert reader.read_item("missing").validation.error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)


def test_update_many_writes_once_and_is_all_or_nothing() -> None:
    store, events = _store(make_task(1), make_task(2))
    writer = StoreTaskWriter(store)
    changed = replace(make_task(2), state=TaskStateEnum.DONE)

    refused = writer.update_many([changed, make_task(9)])
    assert refused.validation.error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)
    assert events == []

    written = writer.update_many([changed])

    assert written.data == (changed,)
    assert len(events) == 1
    tasks = store.current().tasks
    assert tasks is not None
    assert tasks.items == (make_task(1), changed)


def test_delete_many_returns_the_removed_tasks_and_is_all_or_nothing() -> None:
    store, events = _store(make_task(1), make_task(2), make_task(3))
    writer = StoreTaskWriter(store)

    assert writer.delete_many(["task-001", "missing"]).validation.error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)

    removed = writer.delete_many(["task-003", "task-001"])

    assert removed.data == (make_task(1), make_task(3))
    assert len(events) == 1
    assert [task.id for task in StoreTaskReader(store).all_items().value_or(TasksCollection())] == ["task-002"]


def test_task_list_reader_and_writer_use_the_lists_section() -> None:
    store, _events = _store()
    reader = StoreTaskListReader(store)
    writer = StoreTaskListWriter(store)

    created = writer.create(make_list("Home", position=1))
    lists = reader.all_items().data

    assert created.is_success
    assert lists is not None
    assert [item.name for item in lists.ordered()] == ["Work", "Home"]
    assert reader.exists(SPEC_LIST_ID).data is True
    assert reader.read_item("list-home").is_success
    found = reader.find(_NameIs("Home")).data
    assert found is not None
    assert len(found) == 1


class _NameIs:
    def __init__(self, name: str) -> None:
        self._name = name

    def matches(self, entity: object) -> bool:
        return getattr(entity, "name", None) == self._name


def test_readers_return_empty_collections_before_the_file_is_completed() -> None:
    store, _events = _store()
    store.reset(replace(make_user_data(), task_lists=None, tasks=None))

    assert len(StoreTaskListReader(store).all_items().value_or(TaskListsCollection((make_list("x"),)))) == 0
    assert len(StoreTaskReader(store).all_items().value_or(TasksCollection((make_task(1),)))) == 0
