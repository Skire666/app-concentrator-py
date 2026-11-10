"""Snapshot of the details pane under the table (``TODO_DETAILS``)."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class DetailRowSnapshot:
    """One label and value.

    Attributes:
        label: Caption (``List``, ``Due``...).
        value: Formatted value.
    """

    label: str
    value: str


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskDetailsSnapshot:
    """The selected task in full, or a hint.

    Attributes:
        title: Pane caption.
        text: Full text of the task (several lines), ``""`` without a single selected task.
        rows: List, due, state, created, updated.
        empty_text: Shown instead of the details when no task or several tasks are selected.
    """

    title: str
    text: str
    rows: tuple[DetailRowSnapshot, ...]
    empty_text: str
