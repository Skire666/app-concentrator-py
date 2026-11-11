"""Task dialog: text, list, due date and time of a new or existing task (``TASK_EDIT``)."""

import logging
from collections.abc import Callable
from datetime import date, time
from typing import Final

from concentrator.application.ports.clock_port import ClockPort
from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.application.todo.task_commands import TaskCommands
from concentrator.application.todo.todo_queries import TodoQueries
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.todo.task_rules import DUE_TIME_FIELD, TEXT_FIELD
from concentrator.domain.todo.todo_limits import TodoLimits
from concentrator.presentation.common.action_button import action_button
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.common.ui_texts import UiTexts
from concentrator.presentation.ports.dialog_port import DialogPort
from concentrator.presentation.ports.editor_dialog_port import EditorDialogPort
from concentrator.presentation.settings.settings_snapshot import ChoiceFieldSnapshot
from concentrator.presentation.todo.edit_dialog_host import EditDialogHost
from concentrator.presentation.todo.task_edit_form import TaskEditDraft, TaskEditForm
from concentrator.presentation.todo.task_edit_snapshot import DueFieldSnapshot, TaskEditSnapshot, TextFieldSnapshot
from concentrator.presentation.todo.todo_view_state import TodoViewState

_logger = logging.getLogger(__name__)

DEFAULT_DUE_TIME: Final = time(9, 0)
"""Time shown by the time field while the task has no due time."""


class TaskEditPresenter:
    """Owns the task form while the dialog is open; builds ``TASK_EDIT`` and handles its buttons.

    Cancel, Escape and the close button ask before discarding changes (owner decision at the phase 5 plan
    review); an unchanged dialog closes at once.
    """

    def __init__(
        self,
        translator: TranslatorPort,
        gate: ActionGate,
        renderer: RenderCoordinator,
        *,
        queries: TodoQueries,
        commands: TaskCommands,
        clock: ClockPort,
        limits: TodoLimits,
        state: TodoViewState,
    ) -> None:
        """Create the presenter; the dialog and the dialog service come with ``attach``.

        Args:
            translator: Current-language translator.
            gate: Runs every user action.
            renderer: Receives the render requests.
            queries: Lists and tasks.
            commands: Stores the task.
            clock: Today's date, proposed when a due date is switched on.
            limits: Bounds from ``concentrator.ini``.
            state: Selection (a created task is selected).
        """
        self._translator = translator
        self._texts = UiTexts(translator)
        self._gate = gate
        self._renderer = renderer
        self._queries = queries
        self._commands = commands
        self._clock = clock
        self._limits = limits
        self._state = state
        self._host = EditDialogHost(translator, RenderSectionEnum.TASK_EDIT, renderer)
        self._form = TaskEditForm(TaskEditDraft(text="", list_id=""), limits=limits, task_id="")
        self._actions: dict[ActionIdEnum, Callable[[], ValidationResult]] = {
            ActionIdEnum.TASK_EDIT_SAVE: self._save,
            ActionIdEnum.TASK_EDIT_CANCEL: lambda: self._host.cancel(is_dirty=self._form.is_dirty),
        }

    def attach(
        self, window: EditorDialogPort, dialogs: DialogPort, session_ending: Callable[[], bool] | None = None
    ) -> None:
        """Set the dialog and the dialog service (built with the main window).

        Args:
            window: The task dialog.
            dialogs: Discard confirmation.
            session_ending: Tells whether Windows announced the end of the session (no question then).
        """
        self._host.attach(window, dialogs, session_ending)

    def open_new(self, list_id: str) -> ValidationResult:
        """Create a task in a list (``TASK_NEW``).

        Args:
            list_id: List proposed (the current one).

        Returns:
            Success once the dialog closed.
        """
        self._form = TaskEditForm(TaskEditDraft(text="", list_id=list_id), limits=self._limits, task_id="")
        return self._host.show()

    def open_edit(self, task_id: str) -> ValidationResult:
        """Edit a task (``TASK_EDIT``).

        Args:
            task_id: Task to edit.

        Returns:
            Success once the dialog closed, or ``ENTITY_NOT_FOUND``.
        """
        task = self._queries.task(task_id)
        if task.data is None:
            return task.validation
        self._form = TaskEditForm(TaskEditDraft.of(task.data), limits=self._limits, task_id=task_id)
        return self._host.show()

    def build_snapshot(self) -> TaskEditSnapshot:
        """Describe the dialog.

        Returns:
            The snapshot of the draft.
        """
        tr = self._translator.tr
        form = self._form
        return TaskEditSnapshot(
            title=tr("todo.task_edit.title.new") if form.is_new else tr("todo.task_edit.title.edit"),
            text=TextFieldSnapshot(
                label=tr("todo.task_edit.text"),
                text=form.draft.text,
                placeholder=tr("todo.task_edit.text_placeholder"),
                max_length=self._limits.max_task_text_length,
                error=self._error(TEXT_FIELD),
            ),
            task_list=self._list_field(),
            due=self._due_field(),
            save=action_button(self._texts, self._gate, ActionIdEnum.TASK_EDIT_SAVE, enabled=form.can_submit),
            cancel=action_button(self._texts, self._gate, ActionIdEnum.TASK_EDIT_CANCEL),
        )

    def on_text_changed(self, text: str) -> None:
        """Handle a change of the text.

        Args:
            text: Text as typed.
        """
        self._form.set_text(text)
        self._renderer.request(RenderSectionEnum.TASK_EDIT)

    def on_list_selected(self, index: int) -> None:
        """Handle a choice in the list field.

        Args:
            index: Index of the list in tab order.
        """
        lists = self._queries.lists().items
        if 0 <= index < len(lists):
            self._form.set_list(lists[index].id)
        self._renderer.request(RenderSectionEnum.TASK_EDIT)

    def on_due_date_changed(self, has_date: bool, year: int, month: int, day: int) -> None:
        """Handle the due date check box or calendar.

        Args:
            has_date: Whether a due date is set.
            year: Year of the date field.
            month: Month of the date field.
            day: Day of the date field.
        """
        self._form.set_due_date(date(year, month, day) if has_date else None)
        self._renderer.request(RenderSectionEnum.TASK_EDIT)

    def on_due_time_changed(self, has_time: bool, hour: int, minute: int) -> None:
        """Handle the due time check box or field.

        Args:
            has_time: Whether a due time is set.
            hour: Hour of the time field.
            minute: Minute of the time field.
        """
        self._form.set_due_time(time(hour, minute) if has_time else None)
        self._renderer.request(RenderSectionEnum.TASK_EDIT)

    def on_action_requested(self, action_value: int) -> None:
        """Handle a button of the dialog, Escape or its close button (``TASK_EDIT_CANCEL``).

        Args:
            action_value: ``ActionIdEnum`` value emitted by the dialog.
        """
        action = ActionIdEnum.parse(action_value)
        operation = self._actions.get(action)
        if operation is None:
            _logger.warning("Task dialog action %s (%d) is not handled", action.name, action_value)
            return
        result = self._gate.run(action, operation, interactive=action is ActionIdEnum.TASK_EDIT_CANCEL)
        if result.is_failure:
            _logger.warning("Task dialog action %s: %s", action.name, [code.name for code in result.error_codes])
        self._renderer.request(RenderSectionEnum.TASK_EDIT)

    def _save(self) -> ValidationResult:
        """Store the draft, select the task and close the dialog.

        Returns:
            Success, skipped when there is nothing valid to save, or the failure (the dialog stays open).
        """
        form = self._form
        if not form.can_submit:
            return ValidationResult.skipped()
        draft = form.draft.to_task_draft()
        result = self._commands.create(draft) if form.is_new else self._commands.update(form.task_id, draft)
        if result.data is None:
            return result.validation
        self._state.select_tasks((result.data.id,))
        return self._host.close()

    def _list_field(self) -> ChoiceFieldSnapshot:
        """Describe the list field.

        Returns:
            The lists in tab order, the draft's list selected.
        """
        lists = self._queries.lists().items
        selected = next((index for index, item in enumerate(lists) if item.id == self._form.draft.list_id), -1)
        return ChoiceFieldSnapshot(
            label=self._translator.tr("todo.task_edit.list"),
            tooltip="",
            options=tuple(item.name for item in lists),
            selected=selected,
            error="",
        )

    def _due_field(self) -> DueFieldSnapshot:
        """Describe the due date and time fields; today and 09:00 are proposed when they are off.

        Returns:
            The field snapshot.
        """
        tr = self._translator.tr
        draft = self._form.draft
        shown_date = draft.due_date or self._clock.now_local().date()
        shown_time = draft.due_time or DEFAULT_DUE_TIME
        return DueFieldSnapshot(
            date_label=tr("todo.task_edit.due_date"),
            has_date=draft.due_date is not None,
            year=shown_date.year,
            month=shown_date.month,
            day=shown_date.day,
            date_format=tr("todo.task_edit.date_format"),
            time_label=tr("todo.task_edit.due_time"),
            has_time=draft.due_time is not None,
            time_enabled=draft.due_date is not None,
            hour=shown_time.hour,
            minute=shown_time.minute,
            error=self._error(DUE_TIME_FIELD),
        )

    def _error(self, field: str) -> str:
        """Return the inline message of a field.

        Args:
            field: Field path of the rules.

        Returns:
            The first message, ``""`` when the field is valid or the errors are not shown yet.
        """
        return self._texts.field_message(self._form.errors, field) if self._form.shows_errors else ""
