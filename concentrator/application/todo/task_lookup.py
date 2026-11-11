"""Reads the tasks a bulk command works on."""

from collections.abc import Sequence

from concentrator.application.ports.task_reader_port import TaskReaderPort
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.todo.task import Task
from concentrator.domain.todo.tasks_collection import TasksCollection


def find_tasks(reader: TaskReaderPort, task_ids: Sequence[str]) -> DataResult[TasksCollection]:
    """Read every task of a bulk command, or none.

    Args:
        reader: Tasks reader.
        task_ids: Ids, in the order given (repeats are ignored).

    Returns:
        The tasks, skipped for no id, or ``ENTITY_NOT_FOUND`` when one is missing.
    """
    if not task_ids:
        return DataResult.fail(ValidationResult.skipped())
    tasks = reader.all_items().value_or(TasksCollection())
    found: list[Task] = []
    for task_id in dict.fromkeys(task_ids):
        item = tasks.get(task_id)
        if item.data is None:
            return DataResult.fail(item.validation)
        found.append(item.data)
    return DataResult.ok(TasksCollection(found))
