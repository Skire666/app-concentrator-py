"""Wiring of the TODO manager: stores, use cases, view state, presenters and their dialogs."""

from concentrator.application.common.app_config import AppConfig
from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.application.storage.storage_events import UserDataReplacedEvent
from concentrator.application.todo.task_commands import TaskCommands
from concentrator.application.todo.task_list_commands import TaskListCommands, TodoStores
from concentrator.application.todo.todo_defaults import TodoDefaults
from concentrator.application.todo.todo_events import (
    TaskChangedEvent,
    TaskCreatedEvent,
    TaskDeletedEvent,
    TaskListChangedEvent,
    TaskStateChangedEvent,
)
from concentrator.application.todo.todo_queries import TodoQueries
from concentrator.bootstrap.core import Core
from concentrator.infrastructure.persistence.store_todo import (
    StoreTaskListReader,
    StoreTaskListWriter,
    StoreTaskReader,
    StoreTaskWriter,
)
from concentrator.infrastructure.persistence.user_data_store import UserDataStore
from concentrator.presentation.common.layout_state_keeper import LayoutStateKeeper
from concentrator.presentation.todo.list_edit_presenter import ListEditPresenter
from concentrator.presentation.todo.quick_add_presenter import QuickAddPresenter
from concentrator.presentation.todo.task_actions import TaskActions
from concentrator.presentation.todo.task_details_presenter import TaskDetailsPresenter
from concentrator.presentation.todo.task_edit_presenter import TaskEditPresenter
from concentrator.presentation.todo.task_table_presenter import TaskTablePresenter
from concentrator.presentation.todo.todo_layout import TodoLayout
from concentrator.presentation.todo.todo_presenters import TodoPresenters
from concentrator.presentation.todo.todo_refresher import TodoRefresher
from concentrator.presentation.todo.todo_tabs_presenter import TodoTabsPresenter
from concentrator.presentation.todo.todo_toolbar_presenter import TodoToolbarPresenter
from concentrator.presentation.todo.todo_view import TodoView
from concentrator.presentation.todo.todo_view_state import TodoViewState
from concentrator.ui.support.modal_host import DialogRunner
from concentrator.ui.support.qt_dialog_service import QtDialogService
from concentrator.ui.windows.todo_edit_dialogs import ListEditWindow, TaskEditWindow

TODO_EVENTS = (TaskListChangedEvent, TaskCreatedEvent, TaskChangedEvent, TaskStateChangedEvent, TaskDeletedEvent)


def _stores(store: UserDataStore) -> TodoStores:
    """Readers and writers of the lists and tasks on the in-memory store.

    Args:
        store: In-memory data of the open file.

    Returns:
        The stores.
    """
    return TodoStores(
        lists=StoreTaskListReader(store),
        list_writer=StoreTaskListWriter(store),
        tasks=StoreTaskReader(store),
        task_writer=StoreTaskWriter(store),
    )


def _view(core: Core, queries: TodoQueries, defaults: TodoDefaults) -> TodoView:
    """Create the view state (restored from ``layout/todo/*``) and the view.

    Args:
        core: Main-thread services (UI state).
        queries: Lists and tasks.
        defaults: Default sort.

    Returns:
        The view, on an existing list.
    """
    state = TodoViewState(LayoutStateKeeper(core.preferences), defaults)
    state.load()
    view = TodoView(queries, state)
    view.sync()
    return view


def _commands(stores: TodoStores, core: Core, defaults: TodoDefaults) -> tuple[TaskListCommands, TaskCommands]:
    """Create the list and task use cases.

    Args:
        stores: Readers and writers.
        core: Main-thread services (ids, clock, event bus).
        defaults: Limits.

    Returns:
        The list commands and the task commands.
    """
    lists = TaskListCommands(
        stores=stores, ids=core.ids, clock=core.clock, event_bus=core.event_bus, limits=defaults.limits
    )
    tasks = TaskCommands(
        stores=stores, ids=core.ids, clock=core.clock, event_bus=core.event_bus, limits=defaults.limits
    )
    return lists, tasks


def _editors(
    translator: TranslatorPort,
    core: Core,
    use_cases: tuple[TodoQueries, TaskListCommands, TaskCommands],
    view: TodoView,
    defaults: TodoDefaults,
) -> tuple[TaskEditPresenter, ListEditPresenter]:
    """Create the presenters of the task and list dialogs.

    Args:
        translator: Current-language translator.
        core: Main-thread services.
        use_cases: Queries, list commands and task commands.
        view: Current list and selection.
        defaults: Limits and the priority of a new list.

    Returns:
        The task dialog and list dialog presenters.
    """
    queries, lists, tasks = use_cases
    task_editor = TaskEditPresenter(
        translator,
        core.gate,
        core.renderer,
        queries=queries,
        commands=tasks,
        clock=core.clock,
        limits=defaults.limits,
        state=view.state,
    )
    list_editor = ListEditPresenter(
        translator, core.gate, core.renderer, queries=queries, commands=lists, defaults=defaults, state=view.state
    )
    return task_editor, list_editor


def build_todo(config: AppConfig, translator: TranslatorPort, core: Core, store: UserDataStore) -> TodoPresenters:
    """Create the TODO presenters and subscribe them to the data events.

    Args:
        config: Loaded configuration (``[todo]``).
        translator: Current-language translator.
        core: Main-thread services.
        store: In-memory data of the open file.

    Returns:
        The presenters; their dialogs are attached with the main window (``attach_todo_dialogs``).
    """
    defaults = TodoDefaults.from_section(config.todo)
    stores = _stores(store)
    lists, tasks = _commands(stores, core, defaults)
    queries = TodoQueries(stores.lists, stores.tasks)
    view = _view(core, queries, defaults)
    editors = _editors(translator, core, (queries, lists, tasks), view, defaults)
    presenters = _assemble(translator, core, view, (lists, tasks), editors)
    _subscribe(core, presenters.refresher)
    return presenters


def _assemble(
    translator: TranslatorPort,
    core: Core,
    view: TodoView,
    commands: tuple[TaskListCommands, TaskCommands],
    editors: tuple[TaskEditPresenter, ListEditPresenter],
) -> TodoPresenters:
    """Create the presenters of zone 1 around the dialogs.

    Args:
        translator: Current-language translator.
        core: Main-thread services.
        view: Current list, filters and selection.
        commands: List and task use cases.
        editors: Task and list dialog presenters.

    Returns:
        The presenters.
    """
    lists, tasks = commands
    task_editor, list_editor = editors
    actions = TaskActions(translator, core.gate, view=view, commands=tasks, editor=task_editor)
    toolbar = TodoToolbarPresenter(translator, core.gate, core.renderer, view=view, actions=actions)
    table = TaskTablePresenter(
        translator, core.gate, core.renderer, view=view, actions=actions, clock=core.clock, menu=toolbar.menu_builder
    )
    return TodoPresenters(
        tabs=TodoTabsPresenter(translator, core.gate, core.renderer, view=view, commands=lists, editor=list_editor),
        toolbar=toolbar,
        quick_add=QuickAddPresenter(translator, core.gate, core.renderer, view=view, commands=tasks),
        table=table,
        details=TaskDetailsPresenter(translator, core.clock, view),
        task_editor=task_editor,
        list_editor=list_editor,
        actions=actions,
        refresher=TodoRefresher(view, core.renderer),
    )


def _subscribe(core: Core, refresher: TodoRefresher) -> None:
    """Re-render the TODO manager when its data changes or another file opens.

    Args:
        core: Main-thread services (event bus).
        refresher: Follows the data.
    """
    for event_type in TODO_EVENTS:
        core.event_bus.subscribe(event_type, refresher.on_todo_changed)
    core.event_bus.subscribe(UserDataReplacedEvent, refresher.on_user_data_replaced)


def attach_todo_dialogs(
    todo: TodoPresenters, runner: DialogRunner, dialogs: QtDialogService, core: Core, layout: TodoLayout
) -> None:
    """Give the TODO presenters their dialogs over the main window (ADR-036).

    Args:
        todo: TODO presenters.
        runner: The main window's modal host.
        dialogs: Dialog service of the main window.
        core: Main-thread services (render coordinator).
        layout: Spacing of the dialogs.
    """
    renderer = core.renderer
    todo.task_editor.attach(TaskEditWindow(todo.task_editor, renderer, runner, layout), dialogs)
    todo.list_editor.attach(ListEditWindow(todo.list_editor, renderer, runner, layout), dialogs)
    todo.actions.attach(dialogs)
    todo.tabs.attach(dialogs)
