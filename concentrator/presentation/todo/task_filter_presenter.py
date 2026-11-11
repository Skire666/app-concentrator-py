"""Filter bar of the task table (``TODO_FILTERS``): due date filter, recurring only, search, scope, counter."""

import logging
from collections.abc import Callable, Iterable
from types import MappingProxyType
from typing import Final

from concentrator.application.ports.scheduler_port import ScheduledCallPort, SchedulerPort
from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.application.todo.due_filter_enum import DueFilterEnum
from concentrator.application.todo.task_scope_enum import TaskScopeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.presentation.common.action_button import action_button
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.common.ui_texts import UiTexts
from concentrator.presentation.journal.journal_snapshot import SearchBoxSnapshot
from concentrator.presentation.settings.settings_snapshot import ChoiceFieldSnapshot
from concentrator.presentation.todo.task_filter_snapshot import TaskFilterSnapshot
from concentrator.presentation.todo.todo_tabs_presenter import TODO_SECTIONS
from concentrator.presentation.todo.todo_view import TodoView

_logger = logging.getLogger(__name__)

DUE_FILTER_KEYS: Final = MappingProxyType(
    {
        DueFilterEnum.ALL: "todo.filter.due.all",
        DueFilterEnum.OVERDUE: "todo.filter.due.overdue",
        DueFilterEnum.TODAY: "todo.filter.due.today",
        DueFilterEnum.THIS_WEEK: "todo.filter.due.this_week",
        DueFilterEnum.NEXT_7_DAYS: "todo.filter.due.next_7_days",
        DueFilterEnum.WITH_DATE: "todo.filter.due.with_date",
        DueFilterEnum.NO_DATE: "todo.filter.due.no_date",
    }
)
"""Due date filters offered, in order, with their label."""

SCOPE_KEYS: Final = MappingProxyType(
    {TaskScopeEnum.THIS_LIST: "todo.filter.scope.this_list", TaskScopeEnum.ALL_LISTS: "todo.filter.scope.all_lists"}
)
"""Scopes offered, in order, with their label."""

FILTER_SECTIONS: Final = (RenderSectionEnum.TODO_FILTERS, *TODO_SECTIONS)
"""Sections a change of the filters changes."""


class TaskFilterPresenter:
    """Changes the filters of ``TodoViewState``; the search applies ``todo.search_debounce_ms`` after the last key."""

    def __init__(
        self,
        translator: TranslatorPort,
        gate: ActionGate,
        renderer: RenderCoordinator,
        *,
        view: TodoView,
        scheduler: SchedulerPort,
        search_debounce_ms: int,
    ) -> None:
        """Create the presenter.

        Args:
            translator: Current-language translator.
            gate: Runs every user action.
            renderer: Receives the render requests.
            view: Filters of the table and the tasks shown.
            scheduler: Search debounce.
            search_debounce_ms: ``todo.search_debounce_ms``.
        """
        self._translator = translator
        self._texts = UiTexts(translator)
        self._gate = gate
        self._renderer = renderer
        self._view = view
        self._scheduler = scheduler
        self._debounce_ms = search_debounce_ms
        self._typed: str | None = None
        self._search_call: ScheduledCallPort | None = None

    def build_snapshot(self) -> TaskFilterSnapshot:
        """Describe the filter bar now.

        Returns:
            The snapshot.
        """
        tr = self._translator.tr
        state = self._view.state
        dues = tuple(DUE_FILTER_KEYS)
        scopes = tuple(SCOPE_KEYS)
        shown = len(self._view.visible())
        return TaskFilterSnapshot(
            due=self._choice(
                ActionIdEnum.TODO_FILTER_DUE, DUE_FILTER_KEYS.values(), _index(dues, state.task_filter.due)
            ),
            recurring_only=action_button(
                self._texts,
                self._gate,
                ActionIdEnum.TODO_TOGGLE_RECURRING_ONLY,
                checked=state.task_filter.recurring_only,
            ),
            search=SearchBoxSnapshot(
                text=state.search.query if self._typed is None else self._typed,
                placeholder=tr("todo.filter.search_placeholder"),
                tooltip=tr("todo.filter.search_tooltip"),
            ),
            scope=self._choice(ActionIdEnum.TODO_SEARCH_SCOPE, SCOPE_KEYS.values(), _index(scopes, state.scope)),
            counter=self._translator.tr_plural("todo.filter.counter", self._view.scope_total(), shown=shown),
        )

    def on_due_selected(self, index: int) -> None:
        """Handle a choice of the due date filter.

        Args:
            index: Index of the option.
        """
        dues = tuple(DUE_FILTER_KEYS)
        if 0 <= index < len(dues):
            due = dues[index]
            self._run(ActionIdEnum.TODO_FILTER_DUE, lambda: self._view.state.filter_due(due))
        self._renderer.request(*FILTER_SECTIONS)

    def on_scope_selected(self, index: int) -> None:
        """Handle a choice of the scope.

        Args:
            index: Index of the option.
        """
        scopes = tuple(SCOPE_KEYS)
        if 0 <= index < len(scopes):
            scope = scopes[index]
            self._run(ActionIdEnum.TODO_SEARCH_SCOPE, lambda: self._view.state.set_scope(scope))
        self._renderer.request(*FILTER_SECTIONS)

    def on_action_requested(self, action_value: int) -> None:
        """Handle the "Recurring only" toggle.

        Args:
            action_value: ``ActionIdEnum`` value emitted by the panel.
        """
        action = ActionIdEnum.parse(action_value)
        if action is not ActionIdEnum.TODO_TOGGLE_RECURRING_ONLY:
            _logger.warning("Filter action %s (%d) is not handled", action.name, action_value)
            return
        self._run(action, self._view.state.toggle_recurring_only)
        self._renderer.request(*FILTER_SECTIONS)

    def on_search_changed(self, text: str) -> None:
        """Apply a search ``todo.search_debounce_ms`` after the last key press.

        Args:
            text: Text of the search field.
        """
        self._typed = text
        if self._search_call is not None:
            self._search_call.cancel()
        self._search_call = self._scheduler.call_later(self._debounce_ms, self._apply_search)

    def _apply_search(self) -> None:
        """Apply the typed search, or try again later while the previous search is cooling down."""
        self._search_call = None
        if self._gate.is_busy(ActionIdEnum.TODO_SEARCH):
            self._search_call = self._scheduler.call_later(self._debounce_ms, self._apply_search)
            return
        text = self._typed or ""
        self._typed = None
        self._run(ActionIdEnum.TODO_SEARCH, lambda: self._view.state.set_search(text))
        self._renderer.request(*FILTER_SECTIONS)

    def _run(self, action: ActionIdEnum, change: Callable[[], object]) -> None:
        """Run a change of the view through the gate.

        Args:
            action: Action of the control.
            change: Change of the view state (cannot fail).
        """

        def operation() -> ValidationResult:
            change()
            return ValidationResult.success()

        self._gate.run(action, operation)

    def _choice(self, action: ActionIdEnum, keys: Iterable[str], selected: int) -> ChoiceFieldSnapshot:
        """Describe a list labelled by its action.

        Args:
            action: Action of the list (label and tooltip).
            keys: Catalog keys of the options, in order.
            selected: Index of the current option.

        Returns:
            The field.
        """
        options = tuple(self._translator.tr(key) for key in keys)
        return ChoiceFieldSnapshot(
            label=self._texts.action_label(action),
            tooltip=self._texts.action_tooltip(action),
            options=options,
            selected=selected,
            error="",
        )


def _index[T](values: tuple[T, ...], value: T) -> int:
    """Position of a value.

    Args:
        values: Options.
        value: Current value.

    Returns:
        Its index, ``0`` when it is not offered.
    """
    return values.index(value) if value in values else 0
