"""Wiring of the focus queue: stores, use cases, reactions and presenters, on top of the TODO manager."""

from dataclasses import dataclass

from concentrator.application.common.app_config import AppConfig
from concentrator.application.focus.focus_commands import FocusCommands, FocusTodo
from concentrator.application.focus.focus_defaults import FocusDefaults
from concentrator.application.focus.focus_events import FocusQueueChangedEvent
from concentrator.application.focus.focus_queries import FocusQueries
from concentrator.application.focus.focus_reactions import FocusReactions
from concentrator.application.focus.focus_removal import FocusRemoval, FocusStores
from concentrator.application.focus.quick_add_list import QuickAddList
from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.application.storage.storage_events import UserDataReplacedEvent
from concentrator.application.todo.task_commands import TaskCommands
from concentrator.application.todo.task_focus_history import TaskFocusHistory
from concentrator.application.todo.task_list_commands import TaskListCommands, TodoStores
from concentrator.application.todo.todo_defaults import TodoDefaults
from concentrator.bootstrap.core import Core
from concentrator.domain.todo.link_detector import LinkDetector
from concentrator.infrastructure.persistence.store_focus import StoreFocusItemReader, StoreFocusItemWriter
from concentrator.infrastructure.persistence.user_data_store import UserDataStore
from concentrator.presentation.common.date_time_formatter import DateTimeFormatter
from concentrator.presentation.focus.focus_presenters import FocusPresenters
from concentrator.presentation.focus.focus_queue_presenter import FocusQueuePresenter, FocusServices
from concentrator.presentation.focus.focus_row_formatter import FocusRowFormatter
from concentrator.presentation.focus.focus_task_actions import FocusTaskActions
from concentrator.presentation.focus.quick_add_list_choice import QuickAddListChoice
from concentrator.presentation.todo.task_actions import TaskActions
from concentrator.presentation.todo.task_row_formatter import TaskRowFormatter
from concentrator.presentation.todo.todo_view import TodoView

FOCUS_PRESENTER_EVENTS = (FocusQueueChangedEvent, UserDataReplacedEvent)
"""Events that change the queue besides the TODO events."""


@dataclass(frozen=True, slots=True, kw_only=True)
class TodoParts:
    """The TODO pieces the focus queue builds on.

    Attributes:
        stores: Readers and writers of the lists and tasks.
        lists: List use cases (creates the Inbox of the quick add).
        tasks: Task use cases (creates and completes the tasks).
        defaults: Priority of a created Inbox and the history cap.
    """

    stores: TodoStores
    lists: TaskListCommands
    tasks: TaskCommands
    defaults: TodoDefaults


@dataclass(frozen=True, slots=True, kw_only=True)
class FocusCore:
    """The focus use cases, built before the TODO presenters (the star and the tab menu read them).

    Attributes:
        services: Queries, commands, quick-add list choice and limits.
    """

    services: FocusServices

    def queued_task_ids(self) -> frozenset[str]:
        """Return the queued tasks (stars of the task table).

        Returns:
            Their ids.
        """
        return self.services.queries.queued_task_ids()


def _stores(store: UserDataStore, todo: TodoStores) -> FocusStores:
    """Readers and writer of the queue on the in-memory store, with the TODO readers.

    Args:
        store: In-memory data of the open file.
        todo: Readers of the lists and tasks.

    Returns:
        The stores.
    """
    return FocusStores(
        items=StoreFocusItemReader(store), item_writer=StoreFocusItemWriter(store), tasks=todo.tasks, lists=todo.lists
    )


def _subscribe_reactions(stores: FocusStores, history: TaskFocusHistory, core: Core) -> None:
    """Take done, archived and deleted tasks out of the queue (``FocusReactions``).

    Args:
        stores: Queue and tasks.
        history: Records the removals.
        core: Main-thread services (event bus).
    """
    removal = FocusRemoval(stores=stores, history=history, event_bus=core.event_bus)
    FocusReactions(stores=stores, removal=removal).subscribe(core.event_bus)


def build_focus_core(
    config: AppConfig, translator: TranslatorPort, core: Core, store: UserDataStore, todo: TodoParts
) -> FocusCore:
    """Create the focus use cases and subscribe the reactions to the task events.

    Args:
        config: Loaded configuration (``[focus]``).
        translator: Names the Inbox of the quick add.
        core: Main-thread services.
        store: In-memory data of the open file.
        todo: TODO stores and use cases.

    Returns:
        The use cases.
    """
    defaults = FocusDefaults.from_section(config.focus)
    stores = _stores(store, todo.stores)
    history = TaskFocusHistory(stores=todo.stores, clock=core.clock, limits=todo.defaults.limits)
    quick_add_list = QuickAddList(
        lists=stores.lists, list_commands=todo.lists, translator=translator, priority=todo.defaults.list_priority
    )
    commands = FocusCommands(
        stores=stores,
        todo=FocusTodo(tasks=todo.tasks, history=history, quick_add_list=quick_add_list, limits=todo.defaults.limits),
        ids=core.ids,
        clock=core.clock,
        event_bus=core.event_bus,
        limits=defaults.limits,
    )
    _subscribe_reactions(stores, history, core)
    queries = FocusQueries(stores, quick_add_list)
    choice = QuickAddListChoice(core.preferences, queries, core.renderer)
    return FocusCore(services=FocusServices(queries=queries, commands=commands, choice=choice, defaults=defaults))


def build_focus_presenters(
    translator: TranslatorPort,
    core: Core,
    focus: FocusCore,
    zone1: tuple[TodoView, TaskActions, LinkDetector],
    todo_events: tuple[type, ...],
) -> FocusPresenters:
    """Create the presenters of the queue and of the focus actions of zone 1, and subscribe them.

    Args:
        translator: Current-language translator.
        core: Main-thread services.
        focus: Focus use cases.
        zone1: Current list and selection, task actions (they get "Add to focus" and "Remove from focus"),
            links of the texts (due texts are shared with the task table).
        todo_events: Events of the TODO use cases (the rows show the tasks).

    Returns:
        The presenters.
    """
    view, actions, links = zone1
    services = focus.services
    rows = FocusRowFormatter(
        translator, core.gate, TaskRowFormatter(translator, DateTimeFormatter(translator, core.clock), links)
    )
    queue = FocusQueuePresenter(
        translator, core.gate, core.renderer, services=services, view=view, clock=core.clock, rows=rows
    )
    focus_actions = FocusTaskActions(
        core.gate,
        core.renderer,
        view=view,
        queries=services.queries,
        commands=services.commands,
        feedback=queue.feedback,
    )
    focus_actions.register(actions)
    for event_type in (*todo_events, *FOCUS_PRESENTER_EVENTS):
        core.event_bus.subscribe(event_type, queue.on_data_changed)
    return FocusPresenters(queue=queue, actions=focus_actions)
