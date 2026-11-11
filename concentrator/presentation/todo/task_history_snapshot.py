"""Snapshot of the History tab of the details pane (``TODO_HISTORY``)."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskHistorySnapshot:
    """The events of the selected task, newest first.

    Attributes:
        title: Tab caption.
        lines: ``06/11/2026 17:45 - Occurrence 3 completed (due 10/11/2026, next 17/11/2026)``.
        empty_text: Shown instead of the events when no task or several tasks are selected.
    """

    title: str
    lines: tuple[str, ...]
    empty_text: str
