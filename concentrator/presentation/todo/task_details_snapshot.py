"""Snapshot of the details pane under the table (``TODO_DETAILS``)."""

from dataclasses import dataclass
from typing import Final

NO_LINK: Final = -1
"""``link_index`` of a line without link."""


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
class TextLineSnapshot:
    """One line of the text of a task; a line may hold one link (ADR-014).

    Attributes:
        text: The line as stored.
        link_start: Index of the first character of the link.
        link_end: Index after its last character.
        link_index: Number of the link in the task (``NO_LINK`` for plain text).
    """

    text: str
    link_start: int = 0
    link_end: int = 0
    link_index: int = NO_LINK


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskDetailsSnapshot:
    """The selected task in full, or a hint.

    Attributes:
        title: Pane caption.
        lines: Lines of the text, with their links; ``()`` without a single selected task.
        rows: List, due, repeat, occurrences, state, created, updated.
        empty_text: Shown instead of the details when no task or several tasks are selected.
    """

    title: str
    lines: tuple[TextLineSnapshot, ...]
    rows: tuple[DetailRowSnapshot, ...]
    empty_text: str
