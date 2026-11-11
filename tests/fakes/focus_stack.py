"""Focus queue use cases over the real in-memory store, next to the TODO use cases."""

from collections.abc import Sequence

from concentrator.application.focus.focus_commands import FocusCommands, FocusTodo
from concentrator.application.focus.focus_events import FocusQueueChangedEvent
from concentrator.application.focus.focus_queries import FocusQueries
from concentrator.application.focus.focus_reactions import FocusReactions
from concentrator.application.focus.focus_removal import FocusRemoval, FocusStores
from concentrator.application.focus.quick_add_list import QuickAddList
from concentrator.application.todo.task_focus_history import TaskFocusHistory
from concentrator.domain.focus.focus_items_collection import FocusItemsCollection
from concentrator.domain.focus.focus_limits import FocusLimits
from concentrator.domain.todo.priority_enum import PriorityEnum
from concentrator.domain.todo.task import Task
from concentrator.domain.todo.task_list import TaskList
from concentrator.infrastructure.persistence.store_focus import StoreFocusItemReader, StoreFocusItemWriter
from concentrator.infrastructure.persistence.store_todo import StoreTaskListReader, StoreTaskReader
from tests.fakes.fake_translator import FakeTranslator
from tests.fakes.focus_factory import FOCUS_LIMITS
from tests.fakes.todo_factory import TODO_LIMITS
from tests.fakes.todo_stack import TodoStack


class FocusParts:
    """The focus use cases and reactions built on a ``TodoStack``; focus events are recorded."""

    def __init__(self, stack: TodoStack, queue: FocusItemsCollection | None, limits: FocusLimits) -> None:
        stack.store.reset(stack.store.current().with_focus_queue(queue or FocusItemsCollection()))
        self.events: list[FocusQueueChangedEvent] = []
        stack.bus.subscribe(FocusQueueChangedEvent, self.events.append)
        self.stores = FocusStores(
            items=StoreFocusItemReader(stack.store),
            item_writer=StoreFocusItemWriter(stack.store),
            tasks=StoreTaskReader(stack.store),
            lists=StoreTaskListReader(stack.store),
        )
        self.history = TaskFocusHistory(stores=stack.todo_stores, clock=stack.clock, limits=TODO_LIMITS)
        self.quick_add_list = QuickAddList(
            lists=self.stores.lists,
            list_commands=stack.list_commands,
            translator=FakeTranslator(),
            priority=PriorityEnum.NORMAL,
        )
        self.commands = FocusCommands(
            stores=self.stores,
            todo=FocusTodo(tasks=stack.task_commands, history=self.history, quick_add_list=self.quick_add_list),
            ids=stack.ids,
            clock=stack.clock,
            event_bus=stack.bus,
            limits=limits,
        )
        removal = FocusRemoval(stores=self.stores, history=self.history, event_bus=stack.bus)
        FocusReactions(stores=self.stores, removal=removal).subscribe(stack.bus)
        self.queries = FocusQueries(self.stores, self.quick_add_list)

    def queued(self) -> list[str]:
        """Task ids of the queue, in order."""
        return [item.task_id for item in self.queries.queue()]


class FocusStack(TodoStack):
    """The TODO stack plus the focus queue, its reactions and the focus events."""

    def __init__(
        self,
        lists: Sequence[TaskList] = (),
        tasks: Sequence[Task] = (),
        queue: FocusItemsCollection | None = None,
        limits: FocusLimits = FOCUS_LIMITS,
    ) -> None:
        super().__init__(lists, tasks)
        self.focus = FocusParts(self, queue, limits)
        self.focus_events = self.focus.events
        self.focus_commands = self.focus.commands
        self.focus_queries = self.focus.queries
        self.history = self.focus.history

    def queued(self) -> list[str]:
        """Task ids of the queue, in order."""
        return self.focus.queued()
