"""Snapshot of the quick add field (``QUICK_ADD``)."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class QuickAddSnapshot:
    """The one-line field above the table.

    Attributes:
        text: Text of the field (emptied once a task is added).
        placeholder: "Add a task..." hint.
        tooltip: Says that Enter adds the task to the current list.
        error: Inline message of the last refused text, ``""`` when none.
        added_count: Tasks added from the field; it changes on every addition, so the field is emptied even
            when the last rendered snapshot already had an empty text (keys typed between two renders).

    The field is never disabled, so it keeps the focus between two tasks typed in a row; an Enter during
    the cooldown is ignored by the action gate.
    """

    text: str
    placeholder: str
    tooltip: str
    error: str
    added_count: int
