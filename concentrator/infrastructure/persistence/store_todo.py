"""Readers and writers of the lists and tasks: the generic collection store on ``UserData``."""

from typing import override

from concentrator.application.ports.entity_reader_port import EntityQueryPort
from concentrator.application.ports.task_list_reader_port import TaskListReaderPort
from concentrator.application.ports.task_list_writer_port import TaskListWriterPort
from concentrator.application.ports.task_reader_port import TaskReaderPort
from concentrator.application.ports.task_writer_port import TaskWriterPort
from concentrator.application.storage.user_data import UserData
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.entity_collection import EntityCollection
from concentrator.domain.todo.task import Task
from concentrator.domain.todo.task_list import TaskList
from concentrator.domain.todo.task_lists_collection import TaskListsCollection
from concentrator.domain.todo.tasks_collection import TasksCollection
from concentrator.infrastructure.persistence.store_collection import (
    StoreCollectionReader,
    StoreCollectionWriter,
    UserDataSlot,
)
from concentrator.infrastructure.persistence.user_data_store import UserDataStore


def _read_lists(data: UserData) -> EntityCollection[TaskList]:
    """Extract the lists.

    Args:
        data: Snapshot.

    Returns:
        The lists, empty before the file was completed.
    """
    return data.task_lists or TaskListsCollection()


def _write_lists(data: UserData, lists: EntityCollection[TaskList]) -> UserData:
    """Replace the lists.

    Args:
        data: Snapshot.
        lists: Changed lists.

    Returns:
        The changed snapshot.
    """
    return data.with_task_lists(TaskListsCollection(lists))


def _read_tasks(data: UserData) -> EntityCollection[Task]:
    """Extract the tasks.

    Args:
        data: Snapshot.

    Returns:
        The tasks, empty before the file was completed.
    """
    return data.tasks or TasksCollection()


def _write_tasks(data: UserData, tasks: EntityCollection[Task]) -> UserData:
    """Replace the tasks.

    Args:
        data: Snapshot.
        tasks: Changed tasks.

    Returns:
        The changed snapshot.
    """
    return data.with_tasks(tasks if isinstance(tasks, TasksCollection) else TasksCollection(tasks))


class StoreTaskListReader(TaskListReaderPort):
    """``exists``, ``read_item``, ``all_items``, ``find`` on the lists (the generic reader, typed)."""

    def __init__(self, store: UserDataStore) -> None:
        """Create the reader.

        Args:
            store: In-memory store.
        """
        self._slot = UserDataSlot(store, _read_lists, _write_lists)
        self._generic = StoreCollectionReader(self._slot)

    @override
    def exists(self, entity_id: str) -> DataResult[bool]:
        return self._generic.exists(entity_id)

    @override
    def read_item(self, entity_id: str) -> DataResult[TaskList]:
        return self._generic.read_item(entity_id)

    @override
    def all_items(self) -> DataResult[TaskListsCollection]:
        return DataResult.ok(TaskListsCollection(self._slot.read()))

    @override
    def find(self, query: EntityQueryPort[TaskList]) -> DataResult[TaskListsCollection]:
        return DataResult.ok(TaskListsCollection(self._slot.read()).filtered(query.matches))


class StoreTaskListWriter(StoreCollectionWriter[TaskList], TaskListWriterPort):
    """The nine operations and the bulk changes on the lists."""

    def __init__(self, store: UserDataStore) -> None:
        """Create the writer.

        Args:
            store: In-memory store.
        """
        super().__init__(UserDataSlot(store, _read_lists, _write_lists))


class StoreTaskReader(TaskReaderPort):
    """``exists``, ``read_item``, ``all_items``, ``find`` on the tasks (the generic reader, typed).

    ``all_items`` returns the stored collection itself (no copy), so reading 1,000 tasks on every render
    costs nothing.
    """

    def __init__(self, store: UserDataStore) -> None:
        """Create the reader.

        Args:
            store: In-memory store.
        """
        self._slot = UserDataSlot(store, _read_tasks, _write_tasks)
        self._generic = StoreCollectionReader(self._slot)

    @override
    def exists(self, entity_id: str) -> DataResult[bool]:
        return self._generic.exists(entity_id)

    @override
    def read_item(self, entity_id: str) -> DataResult[Task]:
        return self._generic.read_item(entity_id)

    @override
    def all_items(self) -> DataResult[TasksCollection]:
        tasks = self._slot.read()
        return DataResult.ok(tasks if isinstance(tasks, TasksCollection) else TasksCollection(tasks))

    @override
    def find(self, query: EntityQueryPort[Task]) -> DataResult[TasksCollection]:
        return DataResult.ok(TasksCollection(self._slot.read()).filtered(query.matches))


class StoreTaskWriter(StoreCollectionWriter[Task], TaskWriterPort):
    """The nine operations and the bulk changes on the tasks."""

    def __init__(self, store: UserDataStore) -> None:
        """Create the writer.

        Args:
            store: In-memory store.
        """
        super().__init__(UserDataSlot(store, _read_tasks, _write_tasks))
