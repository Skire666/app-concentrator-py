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
        enabled: Whether the field accepts input (not during the cooldown).
    """

    text: str
    placeholder: str
    tooltip: str
    error: str
    enabled: bool
