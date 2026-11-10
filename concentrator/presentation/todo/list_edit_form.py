"""Draft of the list dialog, validated on every change (``AGENTS.md`` section 8.4)."""

from dataclasses import dataclass

from concentrator.application.todo.task_list_commands import ListValues
from concentrator.domain.common.multiline_text import MultilineText
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.todo.priority_enum import PriorityEnum
from concentrator.domain.todo.task_list import TaskList
from concentrator.domain.todo.task_list_rules import TaskListRules
from concentrator.domain.todo.task_lists_collection import TaskListsCollection
from concentrator.domain.todo.todo_limits import TodoLimits
from concentrator.presentation.common.form_state import FormState


@dataclass(frozen=True, slots=True, kw_only=True)
class ListEditDraft:
    """Values edited in the list dialog.

    Attributes:
        name: Name as typed.
        description: Description as typed (several lines).
        priority: Priority.
    """

    name: str
    description: str
    priority: PriorityEnum

    @classmethod
    def of(cls, task_list: TaskList) -> ListEditDraft:
        """Values of a stored list.

        Args:
            task_list: List to edit.

        Returns:
            The draft.
        """
        return cls(name=task_list.name, description=task_list.description.as_text(), priority=task_list.priority)

    def to_values(self) -> ListValues:
        """Values as the use cases take them.

        Returns:
            The list values.
        """
        return ListValues(name=self.name, description=MultilineText.from_text(self.description), priority=self.priority)


class ListEditForm:
    """``FormState`` over ``ListEditDraft``: name, description, priority and unique name.

    A new list starts with an empty name: its inline errors show after the first change. An existing list
    can be saved once it changed.
    """

    def __init__(
        self, baseline: ListEditDraft, *, limits: TodoLimits, lists: TaskListsCollection, list_id: str
    ) -> None:
        """Start editing.

        Args:
            baseline: Values shown when the dialog opens.
            limits: Bounds from ``concentrator.ini``.
            lists: Current lists (unique names).
            list_id: List being edited, ``""`` for a new one.
        """
        self._limits = limits
        self._lists = lists
        self._list_id = list_id
        self._state = FormState(baseline, self._validate)

    @property
    def list_id(self) -> str:
        """List being edited, ``""`` for a new one."""
        return self._list_id

    @property
    def is_new(self) -> bool:
        """Whether the dialog creates a list."""
        return not self._list_id

    @property
    def draft(self) -> ListEditDraft:
        """Values being edited."""
        return self._state.draft

    @property
    def errors(self) -> ValidationResult:
        """Validation of the draft."""
        return self._state.errors

    @property
    def is_dirty(self) -> bool:
        """Whether the draft differs from the values shown when the dialog opened."""
        return self._state.is_dirty

    @property
    def shows_errors(self) -> bool:
        """Whether the inline errors are shown: always, except on a new list not changed yet."""
        return not self.is_new or self._state.is_dirty

    @property
    def can_submit(self) -> bool:
        """Whether Save is allowed: valid, and changed unless the list is new."""
        return (self.is_new or self._state.is_dirty) and not self._state.errors.is_failure

    def set_name(self, name: str) -> None:
        """Change the name.

        Args:
            name: Name as typed.
        """
        self._state.set_field("name", name)

    def set_description(self, description: str) -> None:
        """Change the description.

        Args:
            description: Description as typed.
        """
        self._state.set_field("description", description)

    def set_priority(self, priority: PriorityEnum) -> None:
        """Change the priority.

        Args:
            priority: New priority.
        """
        self._state.set_field("priority", priority)

    def _validate(self, draft: ListEditDraft) -> ValidationResult:
        """Validate a draft as it would be stored.

        Args:
            draft: Draft.

        Returns:
            The issues on ``name``, ``description`` and ``priority``.
        """
        values = draft.to_values()
        return TaskListRules.validate_values(values.name, values.description, values.priority, self._limits).merge(
            TaskListRules.validate_unique_name(self._lists, values.name, except_id=self._list_id)
        )
