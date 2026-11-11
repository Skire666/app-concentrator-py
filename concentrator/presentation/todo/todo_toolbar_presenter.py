"""Task toolbar: the task actions and the Show done / Show archived toggles (``TODO_TOOLBAR``)."""

import logging
from collections.abc import Callable

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.todo.link_detector import LinkDetector
from concentrator.presentation.common.action_button import action_button
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.ui_texts import UiTexts
from concentrator.presentation.todo.task_actions import TaskActions
from concentrator.presentation.todo.task_menu_builder import TaskMenuBuilder, no_task_queued
from concentrator.presentation.todo.todo_tabs_presenter import TODO_SECTIONS
from concentrator.presentation.todo.todo_toolbar_snapshot import TodoToolbarSnapshot
from concentrator.presentation.todo.todo_view import TodoView

_logger = logging.getLogger(__name__)


class TodoToolbarPresenter:
    """Builds ``TODO_TOOLBAR``; task actions run through ``TaskActions``, toggles change the view."""

    def __init__(
        self,
        translator: TranslatorPort,
        gate: ActionGate,
        renderer: RenderCoordinator,
        *,
        view: TodoView,
        actions: TaskActions,
        links: LinkDetector,
        max_links: int,
        queued: Callable[[], frozenset[str]] = no_task_queued,
    ) -> None:
        """Create the presenter.

        Args:
            translator: Current-language translator.
            gate: Runs every user action.
            renderer: Receives the render requests.
            view: Lists, filters and selection.
            actions: Task actions.
            links: Finds the links of a task (context menu of the table).
            max_links: Most links listed by "Open link".
            queued: Ids of the tasks in the focus queue ("Add to focus", "Remove from focus").
        """
        self._texts = UiTexts(translator)
        self._gate = gate
        self._renderer = renderer
        self._view = view
        self._actions = actions
        self._menu = TaskMenuBuilder(self._texts, gate, links=links, max_links=max_links, queued=queued)
        self._toggles: dict[ActionIdEnum, Callable[[], None]] = {
            ActionIdEnum.TODO_TOGGLE_SHOW_DONE: view.state.toggle_show_done,
            ActionIdEnum.TODO_TOGGLE_SHOW_ARCHIVED: view.state.toggle_show_archived,
        }

    @property
    def menu_builder(self) -> TaskMenuBuilder:
        """Builds the task actions (the table shows the same ones in its context menu)."""
        return self._menu

    def build_snapshot(self) -> TodoToolbarSnapshot:
        """Describe the toolbar now.

        Returns:
            The snapshot.
        """
        state = self._view.state
        menu = self._menu.build(self._view.selected(), self._view.lists(), state.list_id)
        return TodoToolbarSnapshot(
            menu=menu,
            show_done=action_button(
                self._texts, self._gate, ActionIdEnum.TODO_TOGGLE_SHOW_DONE, checked=state.show_done
            ),
            show_archived=action_button(
                self._texts, self._gate, ActionIdEnum.TODO_TOGGLE_SHOW_ARCHIVED, checked=state.show_archived
            ),
        )

    def on_action_requested(self, action_value: int) -> None:
        """Handle a toolbar button, a toggle, or an item of the table's context menu.

        Args:
            action_value: ``ActionIdEnum`` value emitted by the panel.
        """
        action = ActionIdEnum.parse(action_value)
        toggle = self._toggles.get(action)
        if toggle is not None:
            self._gate.run(action, lambda: _done(toggle))
        elif self._actions.handles(action):
            self._actions.run(action)
        else:
            _logger.warning("Toolbar action %s (%d) is not handled", action.name, action_value)
            return
        self._renderer.request(*TODO_SECTIONS)

    def on_move_requested(self, list_id: str) -> None:
        """Handle an item of the "Move to list" menu.

        Args:
            list_id: Target list.
        """
        self._actions.move_to(list_id)
        self._renderer.request(*TODO_SECTIONS)


def _done(change: Callable[[], None]) -> ValidationResult:
    """Run a change that cannot fail.

    Args:
        change: The change.

    Returns:
        Success.
    """
    change()
    return ValidationResult.success()
