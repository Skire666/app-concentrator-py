"""TODO presenters on top of ``TodoStack``, with a gate, a renderer, scripted dialogs and view preferences."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.application.storage.storage_events import UserDataReplacedEvent
from concentrator.application.todo.todo_defaults import TodoDefaults
from concentrator.domain.todo.task import Task
from concentrator.domain.todo.task_list import TaskList
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.layout_state_keeper import LayoutStateKeeper
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.todo.list_edit_presenter import ListEditPresenter
from concentrator.presentation.todo.list_edit_snapshot import ListEditSnapshot
from concentrator.presentation.todo.quick_add_presenter import QuickAddPresenter
from concentrator.presentation.todo.quick_add_snapshot import QuickAddSnapshot
from concentrator.presentation.todo.task_actions import TaskActions
from concentrator.presentation.todo.task_details_presenter import TaskDetailsPresenter
from concentrator.presentation.todo.task_details_snapshot import TaskDetailsSnapshot
from concentrator.presentation.todo.task_edit_presenter import TaskEditPresenter
from concentrator.presentation.todo.task_edit_snapshot import TaskEditSnapshot
from concentrator.presentation.todo.task_filter_presenter import TaskFilterPresenter
from concentrator.presentation.todo.task_filter_snapshot import TaskFilterSnapshot
from concentrator.presentation.todo.task_table_presenter import TaskTablePresenter
from concentrator.presentation.todo.task_table_snapshot import TaskTableSnapshot
from concentrator.presentation.todo.todo_presenters import TodoPresenters
from concentrator.presentation.todo.todo_refresher import TodoRefresher
from concentrator.presentation.todo.todo_tabs_presenter import TodoTabsPresenter
from concentrator.presentation.todo.todo_tabs_snapshot import TodoTabsSnapshot
from concentrator.presentation.todo.todo_toolbar_presenter import TodoToolbarPresenter
from concentrator.presentation.todo.todo_toolbar_snapshot import TodoToolbarSnapshot
from concentrator.presentation.todo.todo_view import TodoView
from concentrator.presentation.todo.todo_view_state import TodoViewState
from tests.fakes.app_config_factory import make_todo_section
from tests.fakes.fake_dialogs import FakeDialogs
from tests.fakes.fake_translator import FakeTranslator
from tests.fakes.in_memory_view_preferences import InMemoryViewPreferences
from tests.fakes.manual_scheduler import ManualScheduler
from tests.fakes.timer_ui_stack import FakeEditorDialog
from tests.fakes.todo_stack import LINKS, TODO_EVENT_TYPES, TodoStack

COOLDOWN_MS: Final = 100
DEFAULTS: Final = TodoDefaults.from_section(make_todo_section())


@dataclass(frozen=True, slots=True, kw_only=True)
class SharedUi:
    """Collaborators of another harness (the main window's) the TODO presenters should use."""

    translator: TranslatorPort
    scheduler: ManualScheduler
    renderer: RenderCoordinator
    gate: ActionGate
    dialogs: FakeDialogs
    preferences: InMemoryViewPreferences


class TodoUiStack(TodoStack):
    """Every collaborator of the TODO presenters; rendered snapshots are recorded by section.

    With ``shared``, the presenters use the translator, renderer, gate, dialogs and preferences of another
    harness and register nothing (the main window registers its panels).
    """

    def __init__(
        self,
        lists: Sequence[TaskList] = (),
        tasks: Sequence[Task] = (),
        *,
        stored: dict[str, str] | None = None,
        shared: SharedUi | None = None,
        register_editors: bool = True,
    ) -> None:
        super().__init__(lists, tasks)
        self.scheduler = ManualScheduler() if shared is None else shared.scheduler
        self.renderer = RenderCoordinator(self.scheduler) if shared is None else shared.renderer
        self.translator: TranslatorPort = FakeTranslator() if shared is None else shared.translator
        self.gate = (
            ActionGate(self.clock, self.scheduler, self.renderer, cooldown_ms=COOLDOWN_MS, slow_threshold_ms=200)
            if shared is None
            else shared.gate
        )
        self.dialogs = FakeDialogs() if shared is None else shared.dialogs
        self.preferences = InMemoryViewPreferences(stored) if shared is None else shared.preferences
        self.layout = LayoutStateKeeper(self.preferences)
        self.state = TodoViewState(self.layout, DEFAULTS)
        self.state.load()
        self.view = TodoView(self.queries, self.state, self.clock)
        self.view.sync()
        self._build_presenters()
        if shared is None:
            self._register(register_editors=register_editors)

    def _build_presenters(self) -> None:
        tr, gate, renderer = self.translator, self.gate, self.renderer
        self.task_window = FakeEditorDialog()
        self.list_window = FakeEditorDialog()
        self.task_editor = TaskEditPresenter(
            tr,
            gate,
            renderer,
            queries=self.queries,
            commands=self.task_commands,
            clock=self.clock,
            defaults=DEFAULTS,
            state=self.state,
        )
        self.task_editor.attach(self.task_window, self.dialogs)
        self.list_editor = ListEditPresenter(
            tr, gate, renderer, queries=self.queries, commands=self.list_commands, defaults=DEFAULTS, state=self.state
        )
        self.list_editor.attach(self.list_window, self.dialogs)
        self.actions = TaskActions(tr, gate, view=self.view, commands=self.task_commands, editor=self.task_editor)
        self.actions.attach(self.dialogs)
        self.tabs = TodoTabsPresenter(
            tr, gate, renderer, view=self.view, commands=self.list_commands, editor=self.list_editor
        )
        self.tabs.attach(self.dialogs)
        self.toolbar = TodoToolbarPresenter(tr, gate, renderer, view=self.view, actions=self.actions)
        self.table = TaskTablePresenter(
            tr,
            gate,
            renderer,
            view=self.view,
            actions=self.actions,
            clock=self.clock,
            menu=self.toolbar.menu_builder,
            links=LINKS,
        )
        self.filters = TaskFilterPresenter(
            tr, gate, renderer, view=self.view, scheduler=self.scheduler, search_debounce_ms=DEFAULTS.search_debounce_ms
        )
        self.quick_add = QuickAddPresenter(tr, gate, renderer, view=self.view, commands=self.task_commands)
        self.details = TaskDetailsPresenter(tr, self.clock, self.view, LINKS)
        self.refresher = TodoRefresher(self.view, renderer)
        for event_type in TODO_EVENT_TYPES:
            self.bus.subscribe(event_type, self.refresher.on_todo_changed)
        self.bus.subscribe(UserDataReplacedEvent, self.refresher.on_user_data_replaced)

    def _register(self, *, register_editors: bool) -> None:
        self.rendered_tabs: list[TodoTabsSnapshot] = []
        self.rendered_toolbar: list[TodoToolbarSnapshot] = []
        self.rendered_filters: list[TaskFilterSnapshot] = []
        self.rendered_table: list[TaskTableSnapshot] = []
        self.rendered_quick_add: list[QuickAddSnapshot] = []
        self.rendered_details: list[TaskDetailsSnapshot] = []
        self.rendered_task_edit: list[TaskEditSnapshot] = []
        self.rendered_list_edit: list[ListEditSnapshot] = []
        renderer = self.renderer
        renderer.register(RenderSectionEnum.TODO_TABS, self.tabs.build_snapshot, self.rendered_tabs.append)
        renderer.register(RenderSectionEnum.TODO_TOOLBAR, self.toolbar.build_snapshot, self.rendered_toolbar.append)
        renderer.register(RenderSectionEnum.TODO_FILTERS, self.filters.build_snapshot, self.rendered_filters.append)
        renderer.register(RenderSectionEnum.TODO_TABLE, self.table.build_snapshot, self.rendered_table.append)
        renderer.register(RenderSectionEnum.QUICK_ADD, self.quick_add.build_snapshot, self.rendered_quick_add.append)
        renderer.register(RenderSectionEnum.TODO_DETAILS, self.details.build_snapshot, self.rendered_details.append)
        if register_editors:
            renderer.register(
                RenderSectionEnum.TASK_EDIT, self.task_editor.build_snapshot, self.rendered_task_edit.append
            )
            renderer.register(
                RenderSectionEnum.LIST_EDIT, self.list_editor.build_snapshot, self.rendered_list_edit.append
            )

    def presenters(self) -> TodoPresenters:
        """The presenters as the main window takes them."""
        return TodoPresenters(
            tabs=self.tabs,
            toolbar=self.toolbar,
            filters=self.filters,
            quick_add=self.quick_add,
            table=self.table,
            details=self.details,
            task_editor=self.task_editor,
            list_editor=self.list_editor,
            actions=self.actions,
            refresher=self.refresher,
        )

    def settle(self) -> None:
        """Run the pending renders and let every cooldown end."""
        self.scheduler.run_pending()
        self.clock.advance(ms=COOLDOWN_MS)
        self.scheduler.advance(COOLDOWN_MS)
        self.scheduler.run_pending()

    def select(self, *task_ids: str) -> None:
        """Select tasks in the table, as the panel reports it."""
        self.table.on_selection_changed(task_ids)
        self.settle()
