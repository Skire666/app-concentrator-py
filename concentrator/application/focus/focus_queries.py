"""Read use cases of the focus queue."""

from dataclasses import dataclass

from concentrator.application.focus.focus_removal import FocusStores
from concentrator.application.focus.quick_add_list import QuickAddList
from concentrator.domain.focus.focus_item import FocusItem
from concentrator.domain.focus.focus_items_collection import FocusItemsCollection
from concentrator.domain.focus.focus_rules import FocusRules
from concentrator.domain.todo.task import Task
from concentrator.domain.todo.task_lists_collection import TaskListsCollection
from concentrator.domain.todo.tasks_collection import TasksCollection


@dataclass(frozen=True, slots=True, kw_only=True)
class FocusEntry:
    """One row of the queue: the item joined with its task and the name of its list.

    Attributes:
        item: The item.
        task: Its task.
        list_name: Name of the list of the task (``""`` if the list is gone).
    """

    item: FocusItem
    task: Task
    list_name: str


class FocusQueries:
    """The queue joined with its tasks, the queued task ids and the tasks the picker can propose."""

    def __init__(self, stores: FocusStores, quick_add_list: QuickAddList) -> None:
        """Create the queries.

        Args:
            stores: Queue, tasks and lists.
            quick_add_list: Finds the list of the quick-add field.
        """
        self._stores = stores
        self._quick_add_list = quick_add_list

    def queue(self) -> FocusItemsCollection:
        """Return the queue in order.

        Returns:
            The items.
        """
        return self._stores.queue().ordered()

    def queued_task_ids(self) -> frozenset[str]:
        """Return the queued tasks.

        Returns:
            Their ids.
        """
        return self._stores.queue().task_ids()

    def entries(self) -> tuple[FocusEntry, ...]:
        """Return the rows of the queue, in order.

        Returns:
            One entry per item whose task exists.
        """
        tasks = self._all_tasks()
        lists = self._stores.lists.all_items().value_or(TaskListsCollection())
        entries: list[FocusEntry] = []
        for item in self.queue():
            task = tasks.get(item.task_id).data
            if task is not None:
                task_list = lists.get(task.list_id).data
                entries.append(FocusEntry(item=item, task=task, list_name="" if task_list is None else task_list.name))
        return tuple(entries)

    def candidates(self) -> TasksCollection:
        """Return the tasks the picker may propose: open, of every list, not queued yet.

        Returns:
            The tasks in stored order (the presenter searches and limits them).
        """
        queue = self._stores.queue()
        return self._all_tasks().filtered(lambda task: FocusRules.can_queue(task, queue))

    def quick_add_list_name(self, preferred_list_id: str) -> str:
        """Name the list that will receive a quick-added task.

        Args:
            preferred_list_id: List chosen for the quick add (``""`` for none).

        Returns:
            Its name, or ``""`` when an Inbox will be created.
        """
        found = self._quick_add_list.find(preferred_list_id)
        return "" if found is None else found.name

    def _all_tasks(self) -> TasksCollection:
        """Return every task.

        Returns:
            The tasks.
        """
        return self._stores.tasks.all_items().value_or(TasksCollection())
