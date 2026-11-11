"""Readable lines of the history of a task (History tab)."""

from collections.abc import Mapping
from datetime import date, time
from types import MappingProxyType
from typing import Final

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.domain.focus.focus_removal_reason_enum import FocusRemovalReasonEnum
from concentrator.domain.todo.task_event import (
    DETAIL_DUE,
    DETAIL_FROM,
    DETAIL_NEXT,
    DETAIL_OCCURRENCE,
    DETAIL_REASON,
    DETAIL_SKIPPED,
    DETAIL_SOURCE,
    DETAIL_TO,
    SOURCE_FOCUS,
    TaskEvent,
)
from concentrator.domain.todo.task_event_kind_enum import TaskEventKindEnum
from concentrator.presentation.common.date_time_formatter import DateTimeFormatter

SIMPLE_KEYS: Final = MappingProxyType(
    {
        TaskEventKindEnum.CREATED: "todo.history.created",
        TaskEventKindEnum.TEXT_EDITED: "todo.history.text_edited",
        TaskEventKindEnum.COMPLETED: "todo.history.completed",
        TaskEventKindEnum.REOPENED: "todo.history.reopened",
        TaskEventKindEnum.ARCHIVED: "todo.history.archived",
        TaskEventKindEnum.UNARCHIVED: "todo.history.unarchived",
        TaskEventKindEnum.COPIED_FROM: "todo.history.copied_from",
        TaskEventKindEnum.RECURRENCE_CHANGED: "todo.history.recurrence_changed",
        TaskEventKindEnum.ADDED_TO_FOCUS: "todo.history.added_to_focus",
    }
)
"""Text of the events without details."""

REMOVAL_KEYS: Final = MappingProxyType(
    {
        FocusRemovalReasonEnum.COMPLETED: "todo.history.removed_from_focus.completed",
        FocusRemovalReasonEnum.OCCURRENCE_COMPLETED: "todo.history.removed_from_focus.occurrence_completed",
        FocusRemovalReasonEnum.ARCHIVED: "todo.history.removed_from_focus.archived",
    }
)
"""Text of a ``REMOVED_FROM_FOCUS`` event by reason; any other reason reads "Removed from the focus queue"."""
REMOVED_BY_USER_KEY: Final = "todo.history.removed_from_focus"
FROM_FOCUS_KEY: Final = "todo.history.from_focus"
COMPLETION_KINDS: Final = frozenset({TaskEventKindEnum.COMPLETED, TaskEventKindEnum.OCCURRENCE_COMPLETED})

UNKNOWN_EVENT_KEY: Final = "todo.history.unknown"
_DATE_TIME_SEPARATOR: Final = "T"
_SPACE: Final = " "


class TaskHistoryFormatter:
    """Turns events into lines ``<local date and time> - <what happened>``; details are ids and ISO dates only."""

    def __init__(self, translator: TranslatorPort, dates: DateTimeFormatter) -> None:
        """Create the formatter.

        Args:
            translator: Current-language translator.
            dates: Date and time templates.
        """
        self._translator = translator
        self._dates = dates

    def line(self, event: TaskEvent, list_names: Mapping[str, str]) -> str:
        """Describe one event.

        Args:
            event: Event of the history.
            list_names: Names of the existing lists by id (a moved task names its lists).

        Returns:
            ``06/11/2026 17:45 - Occurrence 3 completed (due 10/11/2026, next 17/11/2026)``.
        """
        return self._translator.tr(
            "todo.history.line", time=self._dates.date_time_minutes(event.at), text=self.text(event, list_names)
        )

    def text(self, event: TaskEvent, list_names: Mapping[str, str]) -> str:
        """Describe what happened.

        Args:
            event: Event of the history.
            list_names: Names of the existing lists by id.

        Returns:
            The translated description; a completion made from the focus queue says so.
        """
        text = self._what(event, list_names)
        if event.kind in COMPLETION_KINDS and event.detail(DETAIL_SOURCE) == SOURCE_FOCUS:
            return self._translator.tr(FROM_FOCUS_KEY, text=text)
        return text

    def _what(self, event: TaskEvent, list_names: Mapping[str, str]) -> str:
        """Describe what happened, without the source of a completion.

        Args:
            event: Event of the history.
            list_names: Names of the existing lists by id.

        Returns:
            The translated description.
        """
        tr = self._translator.tr
        match event.kind:
            case TaskEventKindEnum.DUE_CHANGED:
                return tr(
                    "todo.history.due_changed",
                    old=self.due(event.detail(DETAIL_FROM)),
                    new=self.due(event.detail(DETAIL_TO)),
                )
            case TaskEventKindEnum.MOVED:
                return tr(
                    "todo.history.moved",
                    old=self._list_name(event.detail(DETAIL_FROM), list_names),
                    new=self._list_name(event.detail(DETAIL_TO), list_names),
                )
            case TaskEventKindEnum.OCCURRENCE_COMPLETED:
                return self._occurrence(event)
            case TaskEventKindEnum.REMOVED_FROM_FOCUS:
                return tr(self._removal_key(event.detail(DETAIL_REASON)))
            case _:
                return tr(SIMPLE_KEYS.get(event.kind, UNKNOWN_EVENT_KEY))

    def due(self, iso: str) -> str:
        """Format a due date stored as ISO text (``2026-11-10`` or ``2026-11-10T14:30``).

        Args:
            iso: Detail value.

        Returns:
            The local date (and time), "no date" for ``""``, the text itself when it cannot be read.
        """
        if not iso:
            return self._translator.tr("todo.history.no_date")
        day_text, _separator, time_text = iso.partition(_DATE_TIME_SEPARATOR)
        try:
            text = self._dates.calendar_date(date.fromisoformat(day_text))
            if time_text:
                text += _SPACE + self._dates.clock_time(time.fromisoformat(time_text))
        except ValueError:
            return iso
        return text

    def _occurrence(self, event: TaskEvent) -> str:
        """Describe a completed occurrence.

        Args:
            event: ``OCCURRENCE_COMPLETED`` event.

        Returns:
            ``Occurrence 3 completed (due ..., next ...)``, with the dates skipped, or "last one".
        """
        occurrence = event.detail(DETAIL_OCCURRENCE)
        due = self.due(event.detail(DETAIL_DUE))
        following = event.detail(DETAIL_NEXT)
        if not following:
            return self._translator.tr("todo.history.occurrence_last", occurrence=occurrence, due=due)
        skipped = event.detail(DETAIL_SKIPPED)
        if skipped.isdigit():
            return self._translator.tr_plural(
                "todo.history.occurrence_skipped",
                int(skipped),
                occurrence=occurrence,
                due=due,
                next=self.due(following),
            )
        return self._translator.tr(
            "todo.history.occurrence_completed", occurrence=occurrence, due=due, next=self.due(following)
        )

    @staticmethod
    def _removal_key(reason: str) -> str:
        """Catalog key of a ``REMOVED_FROM_FOCUS`` event.

        Args:
            reason: ``FocusRemovalReasonEnum`` value stored as text.

        Returns:
            The key of that reason, or the one of a removal by the user.
        """
        parsed = FocusRemovalReasonEnum.parse(int(reason)) if reason.isdigit() else FocusRemovalReasonEnum.UNKNOWN
        return REMOVAL_KEYS.get(parsed, REMOVED_BY_USER_KEY)

    def _list_name(self, list_id: str, list_names: Mapping[str, str]) -> str:
        """Name of a list of a ``MOVED`` event.

        Args:
            list_id: Id stored in the event.
            list_names: Existing lists.

        Returns:
            Its name, or "a deleted list".
        """
        return list_names.get(list_id) or self._translator.tr("todo.history.deleted_list")
