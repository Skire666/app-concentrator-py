"""Focus actions of zone 1: "Add to focus", "Remove from focus" and the star of the task table."""

from concentrator.application.focus.focus_commands import FocusCommands
from concentrator.application.focus.focus_queries import FocusQueries
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.focus.focus_feedback import FocusFeedback
from concentrator.presentation.todo.task_actions import TaskActions
from concentrator.presentation.todo.task_menu_builder import focus_applicable
from concentrator.presentation.todo.todo_tabs_presenter import TODO_SECTIONS
from concentrator.presentation.todo.todo_view import TodoView


class FocusTaskActions:
    """Queues and unqueues the selected tasks; a refusal shows under the queue (``FocusFeedback``)."""

    def __init__(
        self,
        gate: ActionGate,
        renderer: RenderCoordinator,
        *,
        view: TodoView,
        queries: FocusQueries,
        commands: FocusCommands,
        feedback: FocusFeedback,
    ) -> None:
        """Create the actions.

        Args:
            gate: Runs the star clicks.
            renderer: Receives the render requests.
            view: Selected tasks.
            queries: Queued tasks.
            commands: Queue use cases.
            feedback: Inline message of the queue.
        """
        self._gate = gate
        self._renderer = renderer
        self._view = view
        self._queries = queries
        self._commands = commands
        self._feedback = feedback

    def register(self, actions: TaskActions) -> None:
        """Add "Add to focus" and "Remove from focus" to the toolbar and context menu actions.

        Args:
            actions: Task actions of zone 1 (they run them through the gate).
        """
        actions.register(ActionIdEnum.FOCUS_ADD_SELECTED, self.add_selected)
        actions.register(ActionIdEnum.FOCUS_REMOVE_SELECTED, self.remove_selected)

    def add_selected(self) -> ValidationResult:
        """Queue the selected open tasks that are not queued yet.

        Returns:
            The result of the use case (``FOCUS_QUEUE_FULL`` when they do not all fit).
        """
        return self._feedback.report(self._commands.add_tasks(self._ids(ActionIdEnum.FOCUS_ADD_SELECTED)))

    def remove_selected(self) -> ValidationResult:
        """Take the selected queued tasks out of the queue.

        Returns:
            The result of the use case.
        """
        return self._feedback.report(self._commands.remove_tasks(self._ids(ActionIdEnum.FOCUS_REMOVE_SELECTED)))

    def on_task_toggled(self, task_id: str) -> None:
        """Star of a row clicked: queue the task, or take it out of the queue.

        Args:
            task_id: Task of the row.
        """
        result = self._gate.run(ActionIdEnum.FOCUS_TOGGLE_TASK, lambda: self._commands.toggle_task(task_id))
        self._feedback.report(result)
        self._renderer.request(*TODO_SECTIONS)

    def _ids(self, action: ActionIdEnum) -> tuple[str, ...]:
        """Selected tasks an action applies to.

        Args:
            action: ``FOCUS_ADD_SELECTED`` or ``FOCUS_REMOVE_SELECTED``.

        Returns:
            Their ids, in table order.
        """
        selected = self._view.selected()
        return tuple(task.id for task in focus_applicable(selected, action, self._queries.queued_task_ids()))
