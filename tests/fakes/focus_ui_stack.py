"""Focus queue presenters on top of the TODO presenters, with every rendered snapshot recorded."""

from collections.abc import Sequence
from typing import Final, override

from concentrator.application.focus.focus_defaults import FocusDefaults
from concentrator.application.focus.focus_events import FocusQueueChangedEvent
from concentrator.domain.focus.focus_items_collection import FocusItemsCollection
from concentrator.domain.focus.focus_limits import FocusLimits
from concentrator.domain.todo.task import Task
from concentrator.domain.todo.task_list import TaskList
from concentrator.presentation.common.date_time_formatter import DateTimeFormatter
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.focus.focus_queue_presenter import FocusQueuePresenter, FocusServices
from concentrator.presentation.focus.focus_queue_snapshot import FocusQueueSnapshot
from concentrator.presentation.focus.focus_row_formatter import FocusRowFormatter
from concentrator.presentation.focus.focus_task_actions import FocusTaskActions
from concentrator.presentation.focus.quick_add_list_choice import QuickAddListChoice
from concentrator.presentation.todo.task_row_formatter import TaskRowFormatter
from concentrator.presentation.todo.todo_tabs_presenter import QuickAddListTarget
from tests.fakes.focus_factory import FOCUS_LIMITS
from tests.fakes.focus_stack import FocusParts
from tests.fakes.todo_stack import LINKS, TODO_EVENT_TYPES
from tests.fakes.todo_ui_stack import TodoUiStack

PICKER_MAX_RESULTS: Final = 3


class FocusUiStack(TodoUiStack):
    """Zone 1 and zone 2 presenters over one store; ``rendered_focus`` records the queue snapshots."""

    def __init__(
        self,
        lists: Sequence[TaskList] = (),
        tasks: Sequence[Task] = (),
        *,
        queue: FocusItemsCollection | None = None,
        limits: FocusLimits = FOCUS_LIMITS,
        stored: dict[str, str] | None = None,
    ) -> None:
        self._queue = queue
        self._limits = limits
        super().__init__(lists, tasks, stored=stored)
        self.bus.subscribe(FocusQueueChangedEvent, self.refresher.on_todo_changed)
        defaults = FocusDefaults(limits=limits, picker_max_results=PICKER_MAX_RESULTS)
        services = FocusServices(
            queries=self.focus.queries, commands=self.focus.commands, choice=self.choice, defaults=defaults
        )
        rows = FocusRowFormatter(
            self.translator,
            self.gate,
            TaskRowFormatter(self.translator, DateTimeFormatter(self.translator, self.clock), LINKS),
        )
        self.queue = FocusQueuePresenter(
            self.translator, self.gate, self.renderer, services=services, view=self.view, clock=self.clock, rows=rows
        )
        self.focus_actions = FocusTaskActions(
            self.gate,
            self.renderer,
            view=self.view,
            queries=self.focus.queries,
            commands=self.focus.commands,
            feedback=self.queue.feedback,
        )
        self.focus_actions.register(self.actions)
        for event_type in (*TODO_EVENT_TYPES, FocusQueueChangedEvent):
            self.bus.subscribe(event_type, self.queue.on_data_changed)
        self.rendered_focus: list[FocusQueueSnapshot] = []
        self.renderer.register(RenderSectionEnum.FOCUS_QUEUE, self.queue.build_snapshot, self.rendered_focus.append)

    @override
    def _before_presenters(self) -> None:
        self.focus = FocusParts(self, self._queue, self._limits)

    @override
    def _queued_task_ids(self) -> frozenset[str]:
        return self.focus.queries.queued_task_ids()

    @override
    def _quick_add_target(self) -> QuickAddListTarget | None:
        self.choice = QuickAddListChoice(self.preferences, self.focus.queries, self.renderer)
        return self.choice
