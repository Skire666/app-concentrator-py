"""Draft of the task dialog, validated on every change (``AGENTS.md`` section 8.4)."""

from dataclasses import dataclass, replace
from datetime import date, time

from concentrator.domain.common.multiline_text import MultilineText
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.todo.task import Task
from concentrator.domain.todo.task_draft import TaskDraft
from concentrator.domain.todo.task_list import TaskListId
from concentrator.domain.todo.task_rules import TaskRules
from concentrator.domain.todo.todo_limits import TodoLimits
from concentrator.presentation.common.form_state import FormState


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskEditDraft:
    """Values edited in the task dialog.

    Attributes:
        text: Text as typed (several lines).
        list_id: List of the task.
        due_date: Due date, ``None`` for "No date".
        due_time: Due time, ``None`` for the whole day.
    """

    text: str
    list_id: str
    due_date: date | None = None
    due_time: time | None = None

    @classmethod
    def of(cls, task: Task) -> TaskEditDraft:
        """Values of a stored task.

        Args:
            task: Task to edit.

        Returns:
            The draft.
        """
        return cls(text=task.text.as_text(), list_id=task.list_id, due_date=task.due_date, due_time=task.due_time)

    def to_task_draft(self) -> TaskDraft:
        """Values as the use cases take them (the text is normalized).

        Returns:
            The task draft.
        """
        return TaskDraft(
            list_id=TaskListId(self.list_id),
            text=MultilineText.from_text(self.text),
            due_date=self.due_date,
            due_time=self.due_time,
        )


class TaskEditForm:
    """``FormState`` over ``TaskEditDraft``: text and due rules of the domain.

    A new task starts empty: its inline errors show after the first change, and it can be saved once valid.
    An existing task can be saved once it changed.
    """

    def __init__(self, baseline: TaskEditDraft, *, limits: TodoLimits, task_id: str) -> None:
        """Start editing.

        Args:
            baseline: Values shown when the dialog opens.
            limits: Bounds from ``concentrator.ini``.
            task_id: Task being edited, ``""`` for a new one.
        """
        self._limits = limits
        self._task_id = task_id
        self._state = FormState(baseline, self._validate)

    @property
    def task_id(self) -> str:
        """Task being edited, ``""`` for a new one."""
        return self._task_id

    @property
    def is_new(self) -> bool:
        """Whether the dialog creates a task."""
        return not self._task_id

    @property
    def draft(self) -> TaskEditDraft:
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
        """Whether the inline errors are shown: always, except on a new task not changed yet."""
        return not self.is_new or self._state.is_dirty

    @property
    def can_submit(self) -> bool:
        """Whether Save is allowed: valid, and changed unless the task is new."""
        return (self.is_new or self._state.is_dirty) and not self._state.errors.is_failure

    def set_text(self, text: str) -> None:
        """Change the text.

        Args:
            text: Text as typed.
        """
        self._state.set_field("text", text)

    def set_list(self, list_id: str) -> None:
        """Change the list.

        Args:
            list_id: New list.
        """
        self._state.set_field("list_id", list_id)

    def set_due_date(self, due_date: date | None) -> None:
        """Change the due date; "No date" also removes the due time.

        Args:
            due_date: New date, ``None`` for "No date".
        """
        draft = self._state.draft
        self._state.set_draft(replace(draft, due_date=due_date, due_time=draft.due_time if due_date else None))

    def set_due_time(self, due_time: time | None) -> None:
        """Change the due time.

        Args:
            due_time: New time, ``None`` for the whole day.
        """
        self._state.set_field("due_time", due_time)

    def _validate(self, draft: TaskEditDraft) -> ValidationResult:
        """Validate a draft as it would be stored.

        Args:
            draft: Draft.

        Returns:
            The issues on ``text`` and ``due_time``.
        """
        return TaskRules.validate_draft(draft.to_task_draft(), self._limits)
