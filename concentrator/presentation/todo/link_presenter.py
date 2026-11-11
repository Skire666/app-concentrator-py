"""Clicks on the links of the tasks (details pane, task table, "Open link" menu), run through the gate."""

import logging

from concentrator.application.todo.link_commands import LinkCommands
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.todo.todo_view import TodoView

_logger = logging.getLogger(__name__)


class LinkPresenter:
    """Opens a link as it is (``LINK_OPEN``): no check, no dialog; a refusal is only logged (ADR-014)."""

    def __init__(self, gate: ActionGate, *, view: TodoView, commands: LinkCommands) -> None:
        """Create the presenter.

        Args:
            gate: Runs every user action.
            view: The selected task (details pane, context menu).
            commands: Opens the links.
        """
        self._gate = gate
        self._view = view
        self._commands = commands

    def on_table_link(self, task_id: str, index: int) -> None:
        """A link of the task column was clicked.

        Args:
            task_id: Task of the row.
            index: Number of the link in the task.
        """
        self._open(task_id, index)

    def on_selected_link(self, index: int) -> None:
        """A link of the details pane, or an entry of the "Open link" menu, was chosen.

        Args:
            index: Number of the link in the only selected task.
        """
        selected = self._view.selected()
        if len(selected) != 1:
            _logger.warning("Link %d chosen without a single selected task", index)
            return
        self._open(selected[0].id, index)

    def _open(self, task_id: str, index: int) -> None:
        """Open a link through the gate.

        Args:
            task_id: Task.
            index: Number of the link.
        """
        result: ValidationResult = self._gate.run(
            ActionIdEnum.LINK_OPEN, lambda: self._commands.open_link(task_id, index)
        )
        if result.is_failure:
            _logger.warning("Link %d of a task not opened: %s", index, [code.name for code in result.error_codes])
