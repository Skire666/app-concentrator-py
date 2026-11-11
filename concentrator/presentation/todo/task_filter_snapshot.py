"""Snapshot of the filter bar above the task table (``TODO_FILTERS``)."""

from dataclasses import dataclass

from concentrator.presentation.common.button_snapshot import ButtonSnapshot
from concentrator.presentation.journal.journal_snapshot import SearchBoxSnapshot
from concentrator.presentation.settings.settings_snapshot import ChoiceFieldSnapshot


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskFilterSnapshot:
    """Due date filter, "Recurring only", search, scope and the counter of the tasks shown.

    Attributes:
        due: Due date filter.
        recurring_only: "Recurring only" toggle (``checked``).
        search: Search field (never disabled).
        scope: This list or all lists.
        counter: ``12 of 87 tasks``.
    """

    due: ChoiceFieldSnapshot
    recurring_only: ButtonSnapshot
    search: SearchBoxSnapshot
    scope: ChoiceFieldSnapshot
    counter: str
