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
        self.store.reset(self.store.current().with_focus_queue(queue or FocusItemsCollection()))
        self.focus_events: list[FocusQueueChangedEvent] = []
        self.bus.subscribe(FocusQueueChangedEvent, self.focus_events.append)
        self.item_writer = StoreFocusItemWriter(self.store)
        self.focus_stores = FocusStores(
            items=StoreFocusItemReader(self.store),
            item_writer=self.item_writer,
            tasks=StoreTaskReader(self.store),
            lists=StoreTaskListReader(self.store),
        )
        self.translator = FakeTranslator()
        self.history = TaskFocusHistory(stores=self.todo_stores, clock=self.clock, limits=TODO_LIMITS)
        self.quick_add_list = QuickAddList(
            lists=self.focus_stores.lists,
            list_commands=self.list_commands,
            translator=self.translator,
            priority=PriorityEnum.NORMAL,
        )
        self.focus_commands = FocusCommands(
            stores=self.focus_stores,
            todo=FocusTodo(tasks=self.task_commands, history=self.history, quick_add_list=self.quick_add_list),
            ids=self.ids,
            clock=self.clock,
            event_bus=self.bus,
            limits=limits,
        )
        removal = FocusRemoval(stores=self.focus_stores, history=self.history, event_bus=self.bus)
        FocusReactions(stores=self.focus_stores, removal=removal).subscribe(self.bus)
        self.focus_queries = FocusQueries(self.focus_stores, self.quick_add_list)

    def queued(self) -> list[str]:
        """Task ids of the queue, in order."""
        return [item.task_id for item in self.focus_queries.queue()]
