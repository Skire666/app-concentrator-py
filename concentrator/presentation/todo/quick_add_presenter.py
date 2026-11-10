"""Quick add field: Enter creates a task in the current list (``QUICK_ADD``)."""

from typing import Final

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.application.todo.task_commands import TaskCommands
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.common.ui_texts import UiTexts
from concentrator.presentation.todo.quick_add_snapshot import QuickAddSnapshot
from concentrator.presentation.todo.todo_view import TodoView

SILENT_CODES: Final = frozenset({ErrorCodeEnum.TASK_TEXT_EMPTY})
"""Enter on an empty field does nothing and shows no message."""


class QuickAddPresenter:
    """Keeps the text of the field; a created task empties it, a refused text shows the reason under it."""

    def __init__(
        self,
        translator: TranslatorPort,
        gate: ActionGate,
        renderer: RenderCoordinator,
        *,
        view: TodoView,
        commands: TaskCommands,
    ) -> None:
        """Create the presenter.

        Args:
            translator: Current-language translator.
            gate: Runs every user action.
            renderer: Receives the render requests.
            view: Current list.
            commands: Creates the task.
        """
        self._translator = translator
        self._texts = UiTexts(translator)
        self._gate = gate
        self._renderer = renderer
        self._view = view
        self._commands = commands
        self._text = ""
        self._error = ValidationResult.success()

    def build_snapshot(self) -> QuickAddSnapshot:
        """Describe the field now.

        Returns:
            The snapshot.
        """
        issue = self._error.first_failure
        return QuickAddSnapshot(
            text=self._text,
            placeholder=self._translator.tr("todo.quick_add.placeholder"),
            tooltip=self._texts.action_tooltip(ActionIdEnum.TASK_QUICK_ADD),
            error="" if issue is None else self._texts.issue_message(issue),
            enabled=not self._gate.is_busy(ActionIdEnum.TASK_QUICK_ADD),
        )

    def on_text_changed(self, text: str) -> None:
        """Remember the text typed; a previous message disappears.

        Args:
            text: Text of the field.
        """
        self._text = text
        if self._error.is_failure:
            self._error = ValidationResult.success()
            self._renderer.request(RenderSectionEnum.QUICK_ADD)

    def on_submitted(self, text: str) -> None:
        """Enter: create the task in the current list and select it.

        Args:
            text: Text of the field.
        """
        self._text = text
        self._gate.run(ActionIdEnum.TASK_QUICK_ADD, self._add)
        self._renderer.request(RenderSectionEnum.QUICK_ADD)

    def _add(self) -> ValidationResult:
        """Create the task.

        Returns:
            The result of the use case.
        """
        created = self._commands.quick_add(self._view.state.list_id, self._text)
        if created.data is None:
            failing = set(created.validation.error_codes)
            self._error = ValidationResult.success() if failing <= SILENT_CODES else created.validation
            return created.validation
        self._text = ""
        self._error = ValidationResult.success()
        self._view.state.select_tasks((created.data.id,))
        return created.validation
