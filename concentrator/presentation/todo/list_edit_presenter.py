"""List dialog: name, description and priority of a new or existing list (``LIST_EDIT``)."""

import logging
from collections.abc import Callable

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.application.todo.task_list_commands import TaskListCommands
from concentrator.application.todo.todo_defaults import TodoDefaults
from concentrator.application.todo.todo_queries import TodoQueries
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.todo.task_list_rules import DESCRIPTION_FIELD, NAME_FIELD, PRIORITY_FIELD
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
from concentrator.presentation.todo.list_edit_form import ListEditDraft, ListEditForm
from concentrator.presentation.todo.list_edit_snapshot import ListEditSnapshot
from concentrator.presentation.todo.task_edit_snapshot import TextFieldSnapshot
from concentrator.presentation.todo.todo_texts import PRIORITIES, PRIORITY_KEYS
from concentrator.presentation.todo.todo_view_state import TodoViewState

_logger = logging.getLogger(__name__)


class ListEditPresenter:
    """Owns the list form while the dialog is open; builds ``LIST_EDIT`` and handles its buttons.

    A new list gets the priority ``todo.default_list_priority`` and is shown once saved. Cancel, Escape and
    the close button ask before discarding changes.
    """

    def __init__(
        self,
        translator: TranslatorPort,
        gate: ActionGate,
        renderer: RenderCoordinator,
        *,
        queries: TodoQueries,
        commands: TaskListCommands,
        defaults: TodoDefaults,
        state: TodoViewState,
    ) -> None:
        """Create the presenter; the dialog and the dialog service come with ``attach``.

        Args:
            translator: Current-language translator.
            gate: Runs every user action.
            renderer: Receives the render requests.
            queries: Lists (unique names).
            commands: Stores the list.
            defaults: Limits and the priority of a new list.
            state: Current list (a created list is shown).
        """
        self._translator = translator
        self._texts = UiTexts(translator)
        self._gate = gate
        self._renderer = renderer
        self._queries = queries
        self._commands = commands
        self._defaults = defaults
        self._state = state
        self._host = EditDialogHost(translator, RenderSectionEnum.LIST_EDIT, renderer)
        self._form = self._new_form()
        self._actions: dict[ActionIdEnum, Callable[[], ValidationResult]] = {
            ActionIdEnum.LIST_EDIT_SAVE: self._save,
            ActionIdEnum.LIST_EDIT_CANCEL: lambda: self._host.cancel(is_dirty=self._form.is_dirty),
        }

    def attach(self, window: EditorDialogPort, dialogs: DialogPort) -> None:
        """Set the dialog and the dialog service (built with the main window).

        Args:
            window: The list dialog.
            dialogs: Discard confirmation.
        """
        self._host.attach(window, dialogs)

    def open_new(self) -> ValidationResult:
        """Create a list (``LIST_ADD``).

        Returns:
            Success once the dialog closed.
        """
        self._form = self._new_form()
        return self._host.show()

    def open_edit(self, list_id: str) -> ValidationResult:
        """Edit a list (``LIST_EDIT``).

        Args:
            list_id: List to edit.

        Returns:
            Success once the dialog closed, or ``ENTITY_NOT_FOUND``.
        """
        task_list = self._queries.task_list(list_id)
        if task_list.data is None:
            return task_list.validation
        self._form = ListEditForm(
            ListEditDraft.of(task_list.data), limits=self._defaults.limits, lists=self._queries.lists(), list_id=list_id
        )
        return self._host.show()

    def build_snapshot(self) -> ListEditSnapshot:
        """Describe the dialog.

        Returns:
            The snapshot of the draft.
        """
        tr = self._translator.tr
        form = self._form
        limits = self._defaults.limits
        return ListEditSnapshot(
            title=tr("todo.list_edit.title.new") if form.is_new else tr("todo.list_edit.title.edit"),
            name=TextFieldSnapshot(
                label=tr("todo.list_edit.name"),
                text=form.draft.name,
                placeholder=tr("todo.list_edit.name_placeholder"),
                max_length=limits.max_list_name_length,
                error=self._error(NAME_FIELD),
            ),
            description=TextFieldSnapshot(
                label=tr("todo.list_edit.description"),
                text=form.draft.description,
                placeholder="",
                max_length=limits.max_list_description_length,
                error=self._error(DESCRIPTION_FIELD),
            ),
            priority=self._priority_field(),
            save=action_button(self._texts, self._gate, ActionIdEnum.LIST_EDIT_SAVE, enabled=form.can_submit),
            cancel=action_button(self._texts, self._gate, ActionIdEnum.LIST_EDIT_CANCEL),
        )

    def on_name_changed(self, text: str) -> None:
        """Handle a change of the name.

        Args:
            text: Name as typed.
        """
        self._form.set_name(text)
        self._renderer.request(RenderSectionEnum.LIST_EDIT)

    def on_description_changed(self, text: str) -> None:
        """Handle a change of the description.

        Args:
            text: Description as typed.
        """
        self._form.set_description(text)
        self._renderer.request(RenderSectionEnum.LIST_EDIT)

    def on_priority_selected(self, index: int) -> None:
        """Handle a choice in the priority field.

        Args:
            index: Index in ``PRIORITIES`` (lowest first).
        """
        if 0 <= index < len(PRIORITIES):
            self._form.set_priority(PRIORITIES[index])
        self._renderer.request(RenderSectionEnum.LIST_EDIT)

    def on_action_requested(self, action_value: int) -> None:
        """Handle a button of the dialog, Escape or its close button (``LIST_EDIT_CANCEL``).

        Args:
            action_value: ``ActionIdEnum`` value emitted by the dialog.
        """
        action = ActionIdEnum.parse(action_value)
        operation = self._actions.get(action)
        if operation is None:
            _logger.warning("List dialog action %s (%d) is not handled", action.name, action_value)
            return
        result = self._gate.run(action, operation, interactive=action is ActionIdEnum.LIST_EDIT_CANCEL)
        if result.is_failure:
            _logger.warning("List dialog action %s: %s", action.name, [code.name for code in result.error_codes])
        self._renderer.request(RenderSectionEnum.LIST_EDIT)

    def _save(self) -> ValidationResult:
        """Store the draft, show the list and close the dialog.

        Returns:
            Success, skipped when there is nothing valid to save, or the failure (the dialog stays open).
        """
        form = self._form
        if not form.can_submit:
            return ValidationResult.skipped()
        values = form.draft.to_values()
        result = self._commands.create(values) if form.is_new else self._commands.update(form.list_id, values)
        if result.data is None:
            return result.validation
        self._state.select_list(result.data.id)
        return self._host.close()

    def _priority_field(self) -> ChoiceFieldSnapshot:
        """Describe the priority field.

        Returns:
            The priorities, lowest first, the draft's one selected.
        """
        tr = self._translator.tr
        priority = self._form.draft.priority
        return ChoiceFieldSnapshot(
            label=tr("todo.list_edit.priority"),
            tooltip=tr("todo.list_edit.priority_tooltip"),
            options=tuple(tr(PRIORITY_KEYS[item]) for item in PRIORITIES),
            selected=PRIORITIES.index(priority) if priority in PRIORITIES else -1,
            error=self._error(PRIORITY_FIELD),
        )

    def _new_form(self) -> ListEditForm:
        """Form of a new list.

        Returns:
            The form: empty name and description, default priority.
        """
        draft = ListEditDraft(name="", description="", priority=self._defaults.list_priority)
        return ListEditForm(draft, limits=self._defaults.limits, lists=self._queries.lists(), list_id="")

    def _error(self, field: str) -> str:
        """Return the inline message of a field.

        Args:
            field: Field path of the rules.

        Returns:
            The first message, ``""`` when the field is valid or the errors are not shown yet.
        """
        return self._texts.field_message(self._form.errors, field) if self._form.shows_errors else ""
