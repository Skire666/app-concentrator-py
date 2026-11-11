"""List tabs: one tab per list, its context menu and the "+" button (``TODO_TABS``)."""

import logging
from collections.abc import Callable
from typing import Final, Protocol

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.application.todo.task_list_commands import TaskListCommands
from concentrator.application.todo.todo_queries import ListOverview
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.todo.task_list import TaskList
from concentrator.domain.todo.task_lists_collection import TaskListsCollection
from concentrator.presentation.common.action_button import action_button
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.button_snapshot import ButtonSnapshot
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.common.ui_texts import UiTexts
from concentrator.presentation.ports.dialog_port import DialogPort
from concentrator.presentation.todo.todo_tabs_snapshot import TabSnapshot, TodoTabsSnapshot
from concentrator.presentation.todo.todo_texts import PRIORITY_BADGE_KEYS, PRIORITY_KEYS, UNKNOWN_KEY
from concentrator.presentation.todo.todo_view import TodoView

_logger = logging.getLogger(__name__)

_NOT_ATTACHED: Final = "TodoTabsPresenter.attach() was not called"
LINE_BREAK: Final = "\n"
EARLIER: Final = -1
LATER: Final = 1
MENU_ACTIONS: Final = (
    ActionIdEnum.LIST_EDIT,
    ActionIdEnum.LIST_MOVE_EARLIER,
    ActionIdEnum.LIST_MOVE_LATER,
    ActionIdEnum.LIST_DELETE,
)
INTERACTIVE_ACTIONS: Final = frozenset({ActionIdEnum.LIST_ADD, ActionIdEnum.LIST_EDIT, ActionIdEnum.LIST_DELETE})
TODO_SECTIONS: Final = (
    RenderSectionEnum.TODO_TABS,
    RenderSectionEnum.TODO_TOOLBAR,
    RenderSectionEnum.TODO_TABLE,
    RenderSectionEnum.TODO_DETAILS,
    RenderSectionEnum.TODO_HISTORY,
)
"""Sections that show the current list or its tasks."""


class ListEditorOpener(Protocol):
    """Opens the list dialog (``ListEditPresenter``)."""

    def open_new(self) -> ValidationResult:
        """Open the dialog on a new list.

        Returns:
            Success once the dialog closed.
        """
        ...

    def open_edit(self, list_id: str) -> ValidationResult:
        """Open the dialog on a list.

        Args:
            list_id: List to edit.

        Returns:
            Success once the dialog closed, or ``ENTITY_NOT_FOUND``.
        """
        ...


class QuickAddListTarget(Protocol):
    """The list of the quick-add field of the focus queue (``QuickAddListChoice``)."""

    def current(self) -> TaskList | None:
        """Return the list that receives a quick-added task.

        Returns:
            The list, ``None`` when an Inbox will be created.
        """
        ...

    def choose(self, list_id: str) -> ValidationResult:
        """Use a list for the quick add.

        Args:
            list_id: List of the tab.

        Returns:
            Success.
        """
        ...


class TodoTabsPresenter:
    """Builds ``TODO_TABS`` and runs the list actions through the action gate."""

    def __init__(
        self,
        translator: TranslatorPort,
        gate: ActionGate,
        renderer: RenderCoordinator,
        *,
        view: TodoView,
        commands: TaskListCommands,
        editor: ListEditorOpener,
        quick_add_list: QuickAddListTarget | None = None,
    ) -> None:
        """Create the presenter; the dialog service comes with ``attach``.

        Args:
            translator: Current-language translator.
            gate: Runs every user action.
            renderer: Receives the render requests.
            view: Lists, open counts and the current list.
            commands: List use cases.
            editor: Opens the list dialog.
            quick_add_list: List of the focus quick add (adds "Use for focus quick add" to the tab menu).
        """
        self._translator = translator
        self._texts = UiTexts(translator)
        self._gate = gate
        self._renderer = renderer
        self._view = view
        self._commands = commands
        self._editor = editor
        self._quick_add_list = quick_add_list
        self._dialogs: DialogPort | None = None
        self._operations: dict[ActionIdEnum, Callable[[str], ValidationResult]] = {
            ActionIdEnum.LIST_SELECT: self._select,
            ActionIdEnum.LIST_EDIT: editor.open_edit,
            ActionIdEnum.LIST_MOVE_EARLIER: lambda list_id: commands.move(list_id, EARLIER),
            ActionIdEnum.LIST_MOVE_LATER: lambda list_id: commands.move(list_id, LATER),
            ActionIdEnum.LIST_DELETE: self._delete,
        }
        if quick_add_list is not None:
            self._operations[ActionIdEnum.FOCUS_SET_QUICK_ADD_LIST] = quick_add_list.choose

    def attach(self, dialogs: DialogPort) -> None:
        """Set the dialog service (built with the main window).

        Args:
            dialogs: Delete confirmation over the main window (ADR-036).
        """
        self._dialogs = dialogs

    def build_snapshot(self) -> TodoTabsSnapshot:
        """Describe the tabs now.

        Returns:
            The snapshot.
        """
        overviews = self._view.overviews()
        lists = self._view.lists()
        current = self._view.state.list_id
        tabs = tuple(self._tab(overview, lists) for overview in overviews)
        selected = next((index for index, item in enumerate(overviews) if item.task_list.id == current), -1)
        description = overviews[selected].task_list.description.as_text() if selected >= 0 else ""
        return TodoTabsSnapshot(
            tabs=tabs,
            selected_index=selected,
            description=description,
            add=action_button(self._texts, self._gate, ActionIdEnum.LIST_ADD),
        )

    def on_action_requested(self, action_value: int) -> None:
        """Handle the "+" button.

        Args:
            action_value: ``ActionIdEnum`` value emitted by the panel.
        """
        action = ActionIdEnum.parse(action_value)
        if action is not ActionIdEnum.LIST_ADD:
            _logger.warning("Tabs action %s (%d) is not handled", action.name, action_value)
            return
        self._run(action, self._editor.open_new)

    def on_list_action_requested(self, action_value: int, list_id: str) -> None:
        """Handle a click on a tab or an item of its context menu.

        Args:
            action_value: ``ActionIdEnum`` value emitted by the panel.
            list_id: List concerned.
        """
        action = ActionIdEnum.parse(action_value)
        operation = self._operations.get(action)
        if operation is None:
            _logger.warning("List action %s (%d) is not handled", action.name, action_value)
            return
        self._run(action, lambda: operation(list_id))

    def _run(self, action: ActionIdEnum, operation: Callable[[], ValidationResult]) -> None:
        """Run an action through the gate and re-render the TODO manager.

        Args:
            action: Action.
            operation: The work.
        """
        result = self._gate.run(action, operation, interactive=action in INTERACTIVE_ACTIONS)
        if result.is_failure:
            _logger.warning("List action %s failed: %s", action.name, [code.name for code in result.error_codes])
        self._renderer.request(*TODO_SECTIONS)

    def _select(self, list_id: str) -> ValidationResult:
        """Show a list.

        Args:
            list_id: List chosen.

        Returns:
            Success, or skipped when it is already shown.
        """
        return ValidationResult.success() if self._view.state.select_list(list_id) else ValidationResult.skipped()

    def _delete(self, list_id: str) -> ValidationResult:
        """Ask for confirmation (with the number of tasks), then delete a list and its tasks.

        Args:
            list_id: List to delete.

        Returns:
            Success, skipped when the user said no, or the failure.
        """
        task_list = next((item for item in self._view.lists() if item.id == list_id), None)
        if task_list is None:
            return self._commands.delete(list_id, delete_tasks=False)
        count = self._view_task_count(list_id)
        confirmed = self._attached_dialogs().confirm(
            self._translator.tr("todo.delete_list.title"),
            self._delete_message(task_list, count),
            self._translator.tr("todo.delete_list.accept"),
            self._translator.tr("dialog.button.cancel"),
        )
        if not confirmed:
            return ValidationResult.skipped()
        return self._commands.delete(list_id, delete_tasks=True)

    def _view_task_count(self, list_id: str) -> int:
        """Count every task of a list.

        Args:
            list_id: List.

        Returns:
            The number of tasks, whatever their state.
        """
        return next((item.task_count for item in self._view.overviews() if item.task_list.id == list_id), 0)

    def _delete_message(self, task_list: TaskList, count: int) -> str:
        """Question of the delete confirmation.

        Args:
            task_list: List to delete.
            count: Its tasks.

        Returns:
            The question, naming the list and the number of tasks deleted with it.
        """
        if not count:
            return self._translator.tr("todo.delete_list.message", name=task_list.name)
        return self._translator.tr_plural("todo.delete_list.message_with_tasks", count, name=task_list.name)

    def _tab(self, overview: ListOverview, lists: TaskListsCollection) -> TabSnapshot:
        """Describe one tab.

        Args:
            overview: List and open tasks.
            lists: Every list (moves and delete).

        Returns:
            The tab snapshot.
        """
        task_list = overview.task_list
        tr = self._translator.tr
        badge_key = PRIORITY_BADGE_KEYS.get(task_list.priority)
        badge = "" if badge_key is None else tr(badge_key)
        key = "todo.tab.text" if overview.open_count else "todo.tab.text_no_open"
        text = tr(key, badge=badge, name=task_list.name, count=overview.open_count)
        return TabSnapshot(
            list_id=task_list.id, text=text, tooltip=self._tooltip(task_list), menu=self._menu(task_list, lists)
        )

    def _tooltip(self, task_list: TaskList) -> str:
        """Tooltip of a tab.

        Args:
            task_list: List of the tab.

        Returns:
            Its priority, then its description.
        """
        tr = self._translator.tr
        priority = tr("todo.tab.tooltip", priority=tr(PRIORITY_KEYS.get(task_list.priority, UNKNOWN_KEY)))
        return LINE_BREAK.join(line for line in (priority, task_list.description.as_text()) if line)

    def _menu(self, task_list: TaskList, lists: TaskListsCollection) -> tuple[ButtonSnapshot, ...]:
        """Context menu of a tab.

        Args:
            task_list: List of the tab.
            lists: Every list.

        Returns:
            Edit, Move earlier, Move later (within the priority), Delete (unless it is the last list), then
            "Use for focus quick add", checked for the list that receives the quick-added tasks.
        """
        enabled = {
            ActionIdEnum.LIST_EDIT: True,
            ActionIdEnum.LIST_MOVE_EARLIER: lists.neighbor(task_list.id, EARLIER) is not None,
            ActionIdEnum.LIST_MOVE_LATER: lists.neighbor(task_list.id, LATER) is not None,
            ActionIdEnum.LIST_DELETE: len(lists) > 1,
        }
        menu = tuple(action_button(self._texts, self._gate, action, enabled=enabled[action]) for action in MENU_ACTIONS)
        if self._quick_add_list is None:
            return menu
        current = self._quick_add_list.current()
        chosen = current is not None and current.id == task_list.id
        return (*menu, action_button(self._texts, self._gate, ActionIdEnum.FOCUS_SET_QUICK_ADD_LIST, checked=chosen))

    def _attached_dialogs(self) -> DialogPort:
        """The dialog service.

        Returns:
            The service given to ``attach``.

        Raises:
            RuntimeError: If ``attach`` was not called (a wiring error).
        """
        if self._dialogs is None:
            raise RuntimeError(_NOT_ATTACHED)
        return self._dialogs
