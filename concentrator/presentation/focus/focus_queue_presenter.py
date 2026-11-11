"""Focus queue of zone 2 (``FOCUS_QUEUE``): rows, search field, quick-add field, capacity, inline message."""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Final

from concentrator.application.focus.focus_commands import FocusCommands
from concentrator.application.focus.focus_defaults import FocusDefaults
from concentrator.application.focus.focus_queries import FocusQueries
from concentrator.application.ports.clock_port import ClockPort
from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.application.storage.user_data_defaults import INBOX_NAME_KEY
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.multiline_text import MultilineText
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.todo.task import Task
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.common.text_search import TextSearch, fold
from concentrator.presentation.common.ui_texts import UiTexts
from concentrator.presentation.focus.focus_feedback import FocusFeedback
from concentrator.presentation.focus.focus_queue_snapshot import (
    FocusFieldSnapshot,
    FocusQueueSnapshot,
    PickerChoiceSnapshot,
)
from concentrator.presentation.focus.focus_row_formatter import DOWN, UP, FocusRowFormatter
from concentrator.presentation.focus.quick_add_list_choice import QuickAddListChoice
from concentrator.presentation.todo.todo_tabs_presenter import TODO_SECTIONS
from concentrator.presentation.todo.todo_view import TodoView

_logger = logging.getLogger(__name__)

SILENT_CODES: Final = frozenset({ErrorCodeEnum.TASK_TEXT_EMPTY})
"""Enter on an empty quick-add field does nothing and shows no message."""
REVEAL_SECTIONS: Final = (*TODO_SECTIONS, RenderSectionEnum.TODO_FILTERS)
"""Sections changed by "Show in list" (list, filters, search and selection of zone 1)."""
FOLD_CACHE_SIZE: Final = 4096


@dataclass(frozen=True, slots=True, kw_only=True)
class FocusServices:
    """What the queue presenter works with.

    Attributes:
        queries: Queue, candidates, quick-add list.
        commands: Queue use cases.
        choice: Quick-add list chosen by the user.
        defaults: Capacity and number of search results.
    """

    queries: FocusQueries
    commands: FocusCommands
    choice: QuickAddListChoice
    defaults: FocusDefaults


def _due_order(task: Task) -> tuple[bool, date, time, datetime]:
    """Order of the search results: the tasks due first, then by creation.

    Args:
        task: Candidate.

    Returns:
        The sort key.
    """
    return (task.due_date is None, task.due_date or date.max, task.due_time or time.max, task.created_at)


class FocusQueuePresenter:
    """Builds ``FOCUS_QUEUE`` and runs the queue actions through the action gate.

    The rows follow the data through ``on_data_changed`` and the minute through ``on_tick`` (due marks).
    """

    def __init__(
        self,
        translator: TranslatorPort,
        gate: ActionGate,
        renderer: RenderCoordinator,
        *,
        services: FocusServices,
        view: TodoView,
        clock: ClockPort,
        rows: FocusRowFormatter,
    ) -> None:
        """Create the presenter.

        Args:
            translator: Current-language translator.
            gate: Runs every user action.
            renderer: Receives the render requests.
            services: Queue queries and commands, quick-add list, limits.
            view: Zone 1 ("Show in list").
            clock: Current local time (due marks).
            rows: Row and search entry texts.
        """
        self._translator = translator
        self._texts = UiTexts(translator)
        self._gate = gate
        self._renderer = renderer
        self._services = services
        self._view = view
        self._clock = clock
        self._rows = rows
        self._feedback = FocusFeedback(renderer)
        self._fields = {ActionIdEnum.FOCUS_PICK: "", ActionIdEnum.FOCUS_QUICK_ADD: ""}
        self._cleared = {ActionIdEnum.FOCUS_PICK: 0, ActionIdEnum.FOCUS_QUICK_ADD: 0}
        self._folded: dict[MultilineText, str] = {}
        self._minute = self._current_minute()
        self._row_operations = self._build_row_operations()

    def _build_row_operations(self) -> dict[ActionIdEnum, Callable[[str], ValidationResult]]:
        """Map every row action to its operation on an item.

        Returns:
            The operations.
        """
        commands = self._services.commands
        return {
            ActionIdEnum.FOCUS_COMPLETE: commands.complete,
            ActionIdEnum.FOCUS_REMOVE: commands.remove,
            ActionIdEnum.FOCUS_MOVE_UP: lambda item_id: commands.move(item_id, UP),
            ActionIdEnum.FOCUS_MOVE_DOWN: lambda item_id: commands.move(item_id, DOWN),
            ActionIdEnum.FOCUS_SHOW_IN_LIST: self._show_in_list,
        }

    @property
    def feedback(self) -> FocusFeedback:
        """Inline message of the queue, shared with the focus actions of zone 1."""
        return self._feedback

    def build_snapshot(self) -> FocusQueueSnapshot:
        """Describe the queue now.

        Returns:
            The snapshot.
        """
        queries = self._services.queries
        queue = queries.queue()
        now = self._clock.now_local()
        issue = self._feedback.issue
        tr = self._translator.tr
        return FocusQueueSnapshot(
            title=tr("focus.title"),
            capacity=tr("focus.capacity", count=len(queue), max=self._services.defaults.limits.max_items),
            capacity_tooltip=tr("focus.capacity.tooltip"),
            rows=tuple(self._rows.row(entry, now, queue) for entry in queries.entries()),
            empty_text=tr("focus.empty"),
            picker=self._field(ActionIdEnum.FOCUS_PICK, tr("focus.picker.placeholder")),
            choices=self._choices(),
            quick_add=self._field(ActionIdEnum.FOCUS_QUICK_ADD, self._quick_add_placeholder()),
            error="" if issue is None else self._texts.issue_message(issue),
        )

    def on_picker_text_changed(self, text: str) -> None:
        """Search the open tasks of every list.

        Args:
            text: Text of the search field.
        """
        self._fields[ActionIdEnum.FOCUS_PICK] = text
        self._feedback.clear()
        self._renderer.request(RenderSectionEnum.FOCUS_QUEUE)

    def on_picked(self, task_id: str) -> None:
        """Queue the task chosen in the search results (Enter or click).

        Args:
            task_id: Task chosen.
        """
        self._run(ActionIdEnum.FOCUS_PICK, lambda: self._services.commands.add_tasks([task_id]))

    def on_quick_add_text_changed(self, text: str) -> None:
        """Remember the text typed in the quick-add field.

        Args:
            text: Text of the field.
        """
        self._fields[ActionIdEnum.FOCUS_QUICK_ADD] = text
        self._feedback.clear()

    def on_quick_add_submitted(self, text: str) -> None:
        """Enter in the quick-add field: create the task in the quick-add list and queue it.

        Args:
            text: Text of the field.
        """
        self._fields[ActionIdEnum.FOCUS_QUICK_ADD] = text
        choice = self._services.choice
        self._run(
            ActionIdEnum.FOCUS_QUICK_ADD,
            lambda: self._services.commands.quick_add(text, choice.preferred_id).validation,
        )

    def on_row_action(self, action_value: int, item_id: str) -> None:
        """Handle the check box, the x button and the context menu of a row.

        Args:
            action_value: ``ActionIdEnum`` value emitted by the panel.
            item_id: Item of the row.
        """
        action = ActionIdEnum.parse(action_value)
        operation = self._row_operations.get(action)
        if operation is None:
            _logger.warning("Focus row action %s (%d) is not handled", action.name, action_value)
            return
        self._feedback.report(self._gate.run(action, lambda: operation(item_id)))

    def on_data_changed(self, _event: object) -> None:
        """The queue, a task, a list or the whole data file changed.

        Args:
            _event: Event of the focus, TODO or storage use cases.
        """
        self._renderer.request(RenderSectionEnum.FOCUS_QUEUE)

    def on_tick(self) -> None:
        """Re-render when the local minute changes (overdue and today marks)."""
        minute = self._current_minute()
        if minute != self._minute:
            self._minute = minute
            self._renderer.request(RenderSectionEnum.FOCUS_QUEUE)

    def _run(self, action: ActionIdEnum, operation: Callable[[], ValidationResult]) -> None:
        """Run a field action; a success empties the field.

        Args:
            action: ``FOCUS_PICK`` or ``FOCUS_QUICK_ADD``.
            operation: The work.
        """
        result = self._feedback.report(self._gate.run(action, operation), SILENT_CODES)
        if result.is_success:
            self._fields[action] = ""
            self._cleared[action] += 1

    def _field(self, action: ActionIdEnum, placeholder: str) -> FocusFieldSnapshot:
        """Describe a field.

        Args:
            action: ``FOCUS_PICK`` or ``FOCUS_QUICK_ADD``.
            placeholder: Hint of the field.

        Returns:
            The field.
        """
        return FocusFieldSnapshot(
            text=self._fields[action],
            placeholder=placeholder,
            tooltip=self._texts.action_tooltip(action),
            cleared_count=self._cleared[action],
        )

    def _quick_add_placeholder(self) -> str:
        """Hint of the quick-add field, naming the list that receives the task.

        Returns:
            ``New task for focus (Inbox)...``.
        """
        target = self._services.choice.current()
        name = self._translator.tr(INBOX_NAME_KEY) if target is None else target.name
        return self._translator.tr("focus.quick_add.placeholder", list=name)

    def _choices(self) -> tuple[PickerChoiceSnapshot, ...]:
        """Tasks matching the search, the tasks due first.

        Returns:
            At most ``focus.picker_max_results`` entries; none while the field is empty.
        """
        search = TextSearch.parse(self._fields[ActionIdEnum.FOCUS_PICK])
        if search.is_empty:
            return ()
        if len(self._folded) > FOLD_CACHE_SIZE:
            self._folded.clear()
        candidates = self._services.queries.candidates()
        matching = sorted((task for task in candidates if search.matches(self._fold(task.text))), key=_due_order)
        names = {item.id: item.name for item in self._view.lists()}
        limit = self._services.defaults.picker_max_results
        return tuple(self._rows.choice(task, names.get(task.list_id, "")) for task in matching[:limit])

    def _fold(self, text: MultilineText) -> str:
        """Folded form of a text, computed once per text.

        Args:
            text: Text of a task.

        Returns:
            The text without case and accents.
        """
        folded = self._folded.get(text)
        if folded is None:
            folded = fold(text.as_text())
            self._folded[text] = folded
        return folded

    def _show_in_list(self, item_id: str) -> ValidationResult:
        """Show the task of an item in zone 1: its list, no filter, the task selected.

        Args:
            item_id: Item.

        Returns:
            Success, or ``ENTITY_NOT_FOUND``.
        """
        entry = next((entry for entry in self._services.queries.entries() if entry.item.id == item_id), None)
        if entry is None:
            return ValidationResult.failure(ErrorCodeEnum.ENTITY_NOT_FOUND)
        self._view.state.reveal(entry.task.list_id, entry.task.id)
        self._renderer.request(*REVEAL_SECTIONS)
        return ValidationResult.success()

    def _current_minute(self) -> tuple[int, int, int, int, int]:
        """Local minute, for the tick check.

        Returns:
            Year, month, day, hour and minute.
        """
        now = self._clock.now_local()
        return (now.year, now.month, now.day, now.hour, now.minute)
