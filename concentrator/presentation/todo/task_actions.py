"""Task actions of the toolbar, the context menu, the check boxes and the keyboard, run through the gate."""

import logging
from collections.abc import Callable
from typing import Final, Protocol

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.application.todo.task_commands import TaskCommands
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.todo.task_state_enum import TaskStateEnum
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.ports.dialog_port import DialogPort
from concentrator.presentation.todo.task_menu_builder import applicable
from concentrator.presentation.todo.todo_view import TodoView

_logger = logging.getLogger(__name__)

_NOT_ATTACHED: Final = "TaskActions.attach() was not called"
INTERACTIVE_ACTIONS: Final = frozenset({ActionIdEnum.TASK_NEW, ActionIdEnum.TASK_EDIT, ActionIdEnum.TASK_DELETE})


class TaskEditorOpener(Protocol):
    """Opens the task dialog (``TaskEditPresenter``)."""

    def open_new(self, list_id: str) -> ValidationResult:
        """Open the dialog on a new task.

        Args:
            list_id: List proposed for the task.

        Returns:
            Success once the dialog closed.
        """
        ...

    def open_edit(self, task_id: str) -> ValidationResult:
        """Open the dialog on a task.

        Args:
            task_id: Task to edit.

        Returns:
            Success once the dialog closed, or ``ENTITY_NOT_FOUND``.
        """
        ...


class TaskActions:
    """Runs the task actions on the selection; every action goes through ``ActionGate``.

    State actions apply to the selected tasks in a state that accepts them (Reopen in a mixed selection
    reopens the done ones). Deleting always asks first, with the number of tasks.
    """

    def __init__(
        self,
        translator: TranslatorPort,
        gate: ActionGate,
        *,
        view: TodoView,
        commands: TaskCommands,
        editor: TaskEditorOpener,
    ) -> None:
        """Create the actions; the dialog service comes with ``attach``.

        Args:
            translator: Confirmation texts.
            gate: Runs every user action.
            view: Current list and selected tasks.
            commands: Task use cases.
            editor: Opens the task dialog.
        """
        self._translator = translator
        self._gate = gate
        self._view = view
        self._commands = commands
        self._editor = editor
        self._dialogs: DialogPort | None = None
        self._operations: dict[ActionIdEnum, Callable[[], ValidationResult]] = {
            ActionIdEnum.TASK_NEW: lambda: editor.open_new(view.list_id),
            ActionIdEnum.TASK_EDIT: self._edit,
            ActionIdEnum.TASK_COMPLETE: lambda: commands.complete(self._ids(ActionIdEnum.TASK_COMPLETE)),
            ActionIdEnum.TASK_REOPEN: lambda: commands.reopen(self._ids(ActionIdEnum.TASK_REOPEN)),
            ActionIdEnum.TASK_ARCHIVE: lambda: commands.archive(self._ids(ActionIdEnum.TASK_ARCHIVE)),
            ActionIdEnum.TASK_UNARCHIVE: lambda: commands.unarchive(self._ids(ActionIdEnum.TASK_UNARCHIVE)),
            ActionIdEnum.TASK_DUPLICATE: self._duplicate,
            ActionIdEnum.TASK_DELETE: self._delete,
        }

    def attach(self, dialogs: DialogPort) -> None:
        """Set the dialog service (built with the main window).

        Args:
            dialogs: Delete confirmation over the main window (ADR-036).
        """
        self._dialogs = dialogs

    def handles(self, action: ActionIdEnum) -> bool:
        """Tell whether an action is a task action of the selection.

        Args:
            action: Action.

        Returns:
            Whether ``run`` handles it.
        """
        return action in self._operations

    def run(self, action: ActionIdEnum) -> ValidationResult:
        """Run a task action on the selection.

        Args:
            action: Toolbar or context menu action.

        Returns:
            The result of the action (skipped while busy or when not handled).
        """
        operation = self._operations.get(action)
        if operation is None:
            _logger.warning("Task action %s is not handled", action.name)
            return ValidationResult.skipped()
        return self._logged(action, self._gate.run(action, operation, interactive=action in INTERACTIVE_ACTIONS))

    def move_to(self, list_id: str) -> ValidationResult:
        """Move the selected tasks to a list (``TASK_MOVE``).

        Args:
            list_id: Target list.

        Returns:
            The result of the move.
        """
        task_ids = tuple(task.id for task in self._view.selected())
        result = self._gate.run(ActionIdEnum.TASK_MOVE, lambda: self._commands.move_to_list(task_ids, list_id))
        return self._logged(ActionIdEnum.TASK_MOVE, result)

    def toggle_done(self, task_id: str) -> ValidationResult:
        """Complete an open task or reopen a done one (check box, Space; ``TASK_TOGGLE_DONE``).

        Args:
            task_id: Task whose check box was clicked.

        Returns:
            The result, skipped for an archived or unknown task.
        """
        task = next((item for item in self._view.visible() if item.id == task_id), None)
        if task is None or task.state not in {TaskStateEnum.OPEN, TaskStateEnum.DONE}:
            return ValidationResult.skipped()
        operation = self._commands.complete if task.state is TaskStateEnum.OPEN else self._commands.reopen
        result = self._gate.run(ActionIdEnum.TASK_TOGGLE_DONE, lambda: operation((task_id,)))
        return self._logged(ActionIdEnum.TASK_TOGGLE_DONE, result)

    def toggle_selection(self) -> ValidationResult:
        """Space: complete the open selected tasks, or reopen the done ones when none is open.

        Returns:
            The result, skipped when no selected task can change.
        """
        selected = self._view.selected()
        to_complete = applicable(selected, ActionIdEnum.TASK_COMPLETE)
        if to_complete:
            ids = tuple(task.id for task in to_complete)
            result = self._gate.run(ActionIdEnum.TASK_TOGGLE_DONE, lambda: self._commands.complete(ids))
        else:
            ids = tuple(task.id for task in applicable(selected, ActionIdEnum.TASK_REOPEN))
            result = self._gate.run(ActionIdEnum.TASK_TOGGLE_DONE, lambda: self._commands.reopen(ids))
        return self._logged(ActionIdEnum.TASK_TOGGLE_DONE, result)

    def edit(self, task_id: str) -> ValidationResult:
        """Open the dialog on a task (double click, Enter; ``TASK_EDIT``).

        Args:
            task_id: Task activated in the table.

        Returns:
            The result of the dialog.
        """
        result = self._gate.run(ActionIdEnum.TASK_EDIT, lambda: self._editor.open_edit(task_id), interactive=True)
        return self._logged(ActionIdEnum.TASK_EDIT, result)

    def _ids(self, action: ActionIdEnum) -> tuple[str, ...]:
        """Ids of the selected tasks a state action applies to.

        Args:
            action: State action.

        Returns:
            The ids.
        """
        return tuple(task.id for task in applicable(self._view.selected(), action))

    def _edit(self) -> ValidationResult:
        """Edit the only selected task.

        Returns:
            The result of the dialog, skipped unless exactly one task is selected.
        """
        selected = self._view.selected()
        if len(selected) != 1:
            return ValidationResult.skipped()
        return self._editor.open_edit(selected[0].id)

    def _duplicate(self) -> ValidationResult:
        """Duplicate the only selected task and select the copy.

        Returns:
            The result, skipped unless exactly one task is selected.
        """
        selected = self._view.selected()
        if len(selected) != 1:
            return ValidationResult.skipped()
        copy = self._commands.duplicate(selected[0].id)
        if copy.data is not None:
            self._view.state.select_tasks((copy.data.id,))
        return copy.validation

    def _delete(self) -> ValidationResult:
        """Ask how many tasks will be deleted, then delete them.

        Returns:
            Success, skipped without selection or when the user said no, or the failure.
        """
        task_ids = tuple(task.id for task in self._view.selected())
        if not task_ids:
            return ValidationResult.skipped()
        tr = self._translator.tr
        confirmed = self._attached_dialogs().confirm(
            tr("todo.delete_tasks.title"),
            self._translator.tr_plural("todo.delete_tasks.message", len(task_ids)),
            tr("todo.delete_tasks.accept"),
            tr("dialog.button.cancel"),
        )
        if not confirmed:
            return ValidationResult.skipped()
        return self._commands.delete(task_ids)

    @staticmethod
    def _logged(action: ActionIdEnum, result: ValidationResult) -> ValidationResult:
        """Log a failed action.

        Args:
            action: Action.
            result: Its result.

        Returns:
            The result.
        """
        if result.is_failure:
            _logger.warning("Task action %s failed: %s", action.name, [code.name for code in result.error_codes])
        return result

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
