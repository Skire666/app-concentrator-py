"""Editable draft of a form, validated on every change (AGENTS.md section 8.4)."""

from collections.abc import Callable
from dataclasses import fields, replace
from typing import TYPE_CHECKING

from concentrator.domain.common.validation_result import ValidationResult

if TYPE_CHECKING:
    from _typeshed import DataclassInstance


class FormState[TDraft: DataclassInstance]:
    """Baseline, draft and validation of one form. Owned by its presenter.

    ``TDraft`` is a frozen dataclass; ``set_field`` replaces one of its fields.
    """

    def __init__(self, baseline: TDraft, validate: Callable[[TDraft], ValidationResult]) -> None:
        """Start editing.

        Args:
            baseline: Value shown when the form opens (the stored value).
            validate: Domain rules applied to the draft after every change.
        """
        self._baseline = baseline
        self._draft = baseline
        self._validate = validate
        self._errors = validate(baseline)

    @property
    def baseline(self) -> TDraft:
        """Value the draft is compared with."""
        return self._baseline

    @property
    def draft(self) -> TDraft:
        """Value being edited."""
        return self._draft

    @property
    def errors(self) -> ValidationResult:
        """Validation of the current draft."""
        return self._errors

    @property
    def is_dirty(self) -> bool:
        """Whether the draft differs from the baseline."""
        return self._draft != self._baseline

    @property
    def can_submit(self) -> bool:
        """Whether the draft changed and has no failing issue."""
        return self.is_dirty and not self._errors.is_failure

    def set_field(self, name: str, value: object) -> None:
        """Change one field of the draft and validate it.

        Args:
            name: Dataclass field name.
            value: New value.
        """
        self.set_draft(replace(self._draft, **{name: value}))

    def set_draft(self, draft: TDraft) -> None:
        """Replace the whole draft and validate it.

        Args:
            draft: New draft.
        """
        self._draft = draft
        self._errors = self._validate(draft)

    def reset(self) -> None:
        """Discard the changes."""
        self.set_draft(self._baseline)

    def commit(self) -> None:
        """Make the draft the new baseline (after it was saved)."""
        self._baseline = self._draft

    def rebase(self, baseline: TDraft) -> None:
        """Take another baseline (the stored value changed elsewhere); untouched fields follow it.

        A field the user changed keeps the edited value; every other field takes the new stored value.

        Args:
            baseline: New stored value.
        """
        edited = {
            field.name: getattr(self._draft, field.name)
            for field in fields(self._draft)
            if getattr(self._draft, field.name) != getattr(self._baseline, field.name)
        }
        self._baseline = baseline
        self.set_draft(replace(baseline, **edited))
