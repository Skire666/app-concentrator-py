"""Wiring of the TODO manager and of its focus queue: stores, use cases, view state, presenters and dialogs."""

from collections.abc import Callable

from concentrator.application.common.app_config import AppConfig
from concentrator.application.focus.focus_events import FocusQueueChangedEvent
from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.application.storage.storage_events import UserDataReplacedEvent
from concentrator.application.todo.link_commands import LinkCommands
from concentrator.application.todo.task_commands import TaskCommands
from concentrator.application.todo.task_list_commands import TaskListCommands, TodoStores
from concentrator.application.todo.task_schedule_commands import TaskScheduleCommands
from concentrator.application.todo.todo_defaults import TodoDefaults
from concentrator.application.todo.todo_events import (
    TaskChangedEvent,
    TaskCreatedEvent,
    TaskDeletedEvent,
    TaskListChangedEvent,
    TaskOccurrenceCompletedEvent,
    TaskStateChangedEvent,
)
from concentrator.application.todo.todo_queries import TodoQueries
from concentrator.bootstrap.core import Core
from concentrator.bootstrap.focus import FocusCore, TodoParts, build_focus_core, build_focus_presenters
from concentrator.domain.todo.link_detector import LinkDetector
from concentrator.infrastructure.persistence.store_todo import (
    StoreTaskListReader,
    StoreTaskListWriter,
    StoreTaskReader,
    StoreTaskWriter,
)
from concentrator.infrastructure.persistence.user_data_store import UserDataStore
from concentrator.infrastructure.qt.qt_link_opener import QtLinkOpener
from concentrator.presentation.common.layout_state_keeper import LayoutStateKeeper
from concentrator.presentation.focus.focus_presenters import FocusPresenters
from concentrator.presentation.todo.link_presenter import LinkPresenter
from concentrator.presentation.todo.list_edit_presenter import ListEditPresenter
from concentrator.presentation.todo.quick_add_presenter import QuickAddPresenter
from concentrator.presentation.todo.task_actions import TaskActions
from concentrator.presentation.todo.task_details_presenter import TaskDetailsPresenter
from concentrator.presentation.todo.task_edit_presenter import TaskEditPresenter
from concentrator.presentation.todo.task_filter_presenter import TaskFilterPresenter
from concentrator.presentation.todo.task_history_presenter import TaskHistoryPresenter
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

TODO_EVENTS = (
    TaskListChangedEvent,
    TaskCreatedEvent,
    TaskChangedEvent,
    TaskStateChangedEvent,
    TaskOccurrenceCompletedEvent,
    TaskDeletedEvent,
)


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
    view = TodoView(queries, state, core.clock)
    view.sync()
    return view


def _commands(
    stores: TodoStores, core: Core, defaults: TodoDefaults, links: LinkDetector
) -> tuple[TaskListCommands, TaskCommands]:
    """Create the list and task use cases.

    Args:
        stores: Readers and writers.
        core: Main-thread services (ids, clock, event bus).
        defaults: Limits.
        links: Finds the paths to normalize in a task text.

    Returns:
        The list commands and the task commands.
    """
    lists = TaskListCommands(
        stores=stores, ids=core.ids, clock=core.clock, event_bus=core.event_bus, limits=defaults.limits
    )
    tasks = TaskCommands(
        stores=stores, ids=core.ids, clock=core.clock, event_bus=core.event_bus, limits=defaults.limits, links=links
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
        defaults=defaults,
        state=view.state,
    )
    list_editor = ListEditPresenter(
        translator, core.gate, core.renderer, queries=queries, commands=lists, defaults=defaults, state=view.state
    )
    return task_editor, list_editor


def build_todo(
    config: AppConfig, translator: TranslatorPort, core: Core, store: UserDataStore
) -> tuple[TodoPresenters, FocusPresenters]:
    """Create the TODO and focus queue presenters and subscribe them to the data events.

    The focus use cases come before the TODO presenters (the stars of the table and the tab menu read them),
    the focus presenters after them ("Add to focus" joins the task actions).

    Args:
        config: Loaded configuration (``[todo]``).
        translator: Current-language translator.
        core: Main-thread services.
        store: In-memory data of the open file.

    Returns:
        The TODO presenters, whose dialogs are attached with the main window (``attach_todo_dialogs``), and
        the focus presenters.
    """
    defaults = TodoDefaults.from_section(config.todo)
    stores = _stores(store)
    links = LinkDetector.of(config.links.url_schemes)
    lists, tasks = _commands(stores, core, defaults, links)
    queries = TodoQueries(stores.lists, stores.tasks)
    view = _view(core, queries, defaults)
    editors = _editors(translator, core, (queries, lists, tasks), view, defaults)
    use_cases = (lists, tasks, *_side_commands(stores, core, defaults, links))
    focus = build_focus_core(
        config, translator, core, store, TodoParts(stores=stores, lists=lists, tasks=tasks, defaults=defaults)
    )
    presenters = _assemble(translator, core, (view, config, links), use_cases, editors, focus)
    _subscribe(core, presenters.refresher)
    return presenters, build_focus_presenters(translator, core, focus, (view, presenters.actions, links), TODO_EVENTS)


def _side_commands(
    stores: TodoStores, core: Core, defaults: TodoDefaults, links: LinkDetector
) -> tuple[LinkCommands, TaskScheduleCommands]:
    """Create the link and due date use cases.

    Args:
        stores: Readers and writers.
        core: Main-thread services (clock, event bus).
        defaults: Limits.
        links: Finds the links of a task text.

    Returns:
        The link commands and the due date commands.
    """
    link_commands = LinkCommands(tasks=stores.tasks, links=links, opener=QtLinkOpener())
    schedule = TaskScheduleCommands(stores=stores, clock=core.clock, event_bus=core.event_bus, limits=defaults.limits)
    return link_commands, schedule


def _assemble(
    translator: TranslatorPort,
    core: Core,
    shown: tuple[TodoView, AppConfig, LinkDetector],
    commands: tuple[TaskListCommands, TaskCommands, LinkCommands, TaskScheduleCommands],
    editors: tuple[TaskEditPresenter, ListEditPresenter],
    focus: FocusCore,
) -> TodoPresenters:
    """Create the presenters of zone 1 around the dialogs.

    Args:
        translator: Current-language translator.
        core: Main-thread services.
        shown: Current list, filters and selection; configuration; links of the texts.
        commands: List, task, link and due date use cases.
        editors: Task and list dialog presenters.
        focus: Queued tasks (stars, focus actions) and the quick-add list (tab menu).

    Returns:
        The presenters.
    """
    view = shown[0]
    task_editor, list_editor = editors
    actions = _actions(translator, core, view, (commands[1], commands[3]), task_editor)
    toolbar, table, filters = _table_presenters(translator, core, shown, actions, focus)
    details, history, links = _info_presenters(translator, core, shown, commands[2])
    return TodoPresenters(
        tabs=_tabs(translator, core, view, (commands[0], list_editor), focus),
        toolbar=toolbar,
        filters=filters,
        quick_add=QuickAddPresenter(translator, core.gate, core.renderer, view=view, commands=commands[1]),
        table=table,
        details=details,
        history=history,
        links=links,
        task_editor=task_editor,
        list_editor=list_editor,
        actions=actions,
        refresher=TodoRefresher(view, core.renderer),
    )


def _tabs(
    translator: TranslatorPort,
    core: Core,
    view: TodoView,
    lists: tuple[TaskListCommands, ListEditPresenter],
    focus: FocusCore,
) -> TodoTabsPresenter:
    """Create the presenter of the list tabs.

    Args:
        translator: Current-language translator.
        core: Main-thread services.
        view: Lists and the current list.
        lists: List use cases and the list dialog.
        focus: Quick-add list of the focus queue (tab menu).

    Returns:
        The presenter.
    """
    commands, editor = lists
    return TodoTabsPresenter(
        translator,
        core.gate,
        core.renderer,
        view=view,
        commands=commands,
        editor=editor,
        quick_add_list=focus.services.choice,
    )


def _actions(
    translator: TranslatorPort,
    core: Core,
    view: TodoView,
    commands: tuple[TaskCommands, TaskScheduleCommands],
    editor: TaskEditPresenter,
) -> TaskActions:
    """Create the task actions of the toolbar, the context menu and the keyboard.

    Args:
        translator: Current-language translator.
        core: Main-thread services.
        view: Current list and selection.
        commands: Task and due date use cases.
        editor: Task dialog.

    Returns:
        The actions.
    """
    tasks, schedule = commands
    return TaskActions(
        translator, core.gate, view=view, commands=tasks, editor=editor, schedule=schedule, clock=core.clock
    )


def _info_presenters(
    translator: TranslatorPort, core: Core, shown: tuple[TodoView, AppConfig, LinkDetector], commands: LinkCommands
) -> tuple[TaskDetailsPresenter, TaskHistoryPresenter, LinkPresenter]:
    """Create the presenters of the Details and History tabs and of the link clicks.

    Args:
        translator: Current-language translator.
        core: Main-thread services.
        shown: Current list and selection; configuration; links of the texts.
        commands: Opens the links.

    Returns:
        The details, history and link presenters.
    """
    view, _config, links = shown
    return (
        TaskDetailsPresenter(translator, core.clock, view, links),
        TaskHistoryPresenter(translator, core.clock, view),
        LinkPresenter(core.gate, view=view, commands=commands),
    )


def _table_presenters(
    translator: TranslatorPort,
    core: Core,
    shown: tuple[TodoView, AppConfig, LinkDetector],
    actions: TaskActions,
    focus: FocusCore,
) -> tuple[TodoToolbarPresenter, TaskTablePresenter, TaskFilterPresenter]:
    """Create the presenters of the toolbar, of the task table and of its filter bar.

    Args:
        translator: Current-language translator.
        core: Main-thread services.
        shown: Current list, filters and selection; configuration; links of the texts.
        actions: Task actions (the toolbar and the context menu of the table share them).
        focus: Queued tasks (stars, "Add to focus" and "Remove from focus").

    Returns:
        The toolbar, table and filter bar presenters.
    """
    view, config, links = shown
    toolbar = TodoToolbarPresenter(
        translator,
        core.gate,
        core.renderer,
        view=view,
        actions=actions,
        links=links,
        max_links=config.links.max_links_in_menu,
        queued=focus.queued_task_ids,
    )
    table = TaskTablePresenter(
        translator,
        core.gate,
        core.renderer,
        view=view,
        actions=actions,
        clock=core.clock,
        menu=toolbar.menu_builder,
        links=links,
    )
    return toolbar, table, _filters(translator, core, view, config)


def _filters(translator: TranslatorPort, core: Core, view: TodoView, config: AppConfig) -> TaskFilterPresenter:
    """Create the presenter of the filter bar.

    Args:
        translator: Current-language translator.
        core: Main-thread services (gate, renderer, scheduler).
        view: Filters of the table.
        config: ``todo.search_debounce_ms``.

    Returns:
        The presenter.
    """
    return TaskFilterPresenter(
        translator,
        core.gate,
        core.renderer,
        view=view,
        scheduler=core.scheduler,
        search_debounce_ms=config.todo.search_debounce_ms,
    )


def _subscribe(core: Core, refresher: TodoRefresher) -> None:
    """Re-render the TODO manager when its data or the focus queue changes, or another file opens.

    Args:
        core: Main-thread services (event bus).
        refresher: Follows the data.
    """
    for event_type in (*TODO_EVENTS, FocusQueueChangedEvent):
        core.event_bus.subscribe(event_type, refresher.on_todo_changed)
    core.event_bus.subscribe(UserDataReplacedEvent, refresher.on_user_data_replaced)


def attach_todo_dialogs(
    todo: TodoPresenters,
    runner: DialogRunner,
    dialogs: tuple[QtDialogService, Callable[[], bool]],
    core: Core,
    config: AppConfig,
) -> None:
    """Give the TODO presenters their dialogs over the main window (ADR-036).

    Args:
        todo: TODO presenters.
        runner: The main window's modal host.
        dialogs: Dialog service of the main window, and whether the Windows session ends (the task and
            list dialogs then close without asking).
        core: Main-thread services (render coordinator).
        config: Loaded configuration (spacing of the dialogs).
    """
    renderer = core.renderer
    layout = TodoLayout.from_config(config)
    service, session_ending = dialogs
    todo.task_editor.attach(TaskEditWindow(todo.task_editor, renderer, runner, layout), service, session_ending)
    todo.list_editor.attach(ListEditWindow(todo.list_editor, renderer, runner, layout), service, session_ending)
    todo.actions.attach(service)
    todo.tabs.attach(service)
