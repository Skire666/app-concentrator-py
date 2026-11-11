"""Task actions enabled from the selection, for the toolbar and the context menu of the table."""

from collections.abc import Callable, Sequence
from dataclasses import replace
from typing import Final

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.severity_enum import SeverityEnum
from concentrator.domain.common.validation_issue import ValidationIssue
from concentrator.domain.todo.link_detector import LinkDetector
from concentrator.domain.todo.task import Task
from concentrator.domain.todo.task_lists_collection import TaskListsCollection
from concentrator.domain.todo.task_state_enum import TaskStateEnum
from concentrator.presentation.common.action_button import action_button
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.button_snapshot import ButtonSnapshot
from concentrator.presentation.common.ui_texts import UiTexts
from concentrator.presentation.todo.task_menu_snapshot import LinkMenuItemSnapshot, MoveTargetSnapshot, TaskMenuSnapshot

TASK_MENU_ACTIONS: Final = (
    ActionIdEnum.TASK_NEW,
    ActionIdEnum.TASK_EDIT,
    ActionIdEnum.TASK_COMPLETE,
    ActionIdEnum.TASK_REOPEN,
    ActionIdEnum.TASK_ARCHIVE,
    ActionIdEnum.TASK_UNARCHIVE,
    ActionIdEnum.TASK_DUPLICATE,
    ActionIdEnum.TASK_MOVE,
    ActionIdEnum.TASK_SET_DUE_DATE,
    ActionIdEnum.TASK_CLEAR_DUE_DATE,
    ActionIdEnum.FOCUS_ADD_SELECTED,
    ActionIdEnum.FOCUS_REMOVE_SELECTED,
    ActionIdEnum.TASK_DELETE,
)
"""Buttons of the toolbar and items of the context menu, in order."""
FOCUS_ACTIONS: Final = frozenset({ActionIdEnum.FOCUS_ADD_SELECTED, ActionIdEnum.FOCUS_REMOVE_SELECTED})

ACTION_STATES: Final = {
    ActionIdEnum.TASK_COMPLETE: frozenset({TaskStateEnum.OPEN}),
    ActionIdEnum.TASK_REOPEN: frozenset({TaskStateEnum.DONE}),
    ActionIdEnum.TASK_ARCHIVE: frozenset({TaskStateEnum.OPEN, TaskStateEnum.DONE}),
    ActionIdEnum.TASK_UNARCHIVE: frozenset({TaskStateEnum.ARCHIVED}),
}
"""States a selected task must have for a state action to apply to it."""

SINGLE_TASK_ACTIONS: Final = frozenset({ActionIdEnum.TASK_EDIT, ActionIdEnum.TASK_DUPLICATE})
ANY_TASK_ACTIONS: Final = frozenset({ActionIdEnum.TASK_DELETE, ActionIdEnum.TASK_SET_DUE_DATE})
NEEDS_DUE_DATE: Final = ValidationIssue(code=ErrorCodeEnum.RECURRENCE_REQUIRES_DUE_DATE, severity=SeverityEnum.ERROR)
"""Why "Clear due date" is off for a selection holding a repeating task (its tooltip)."""


def no_task_queued() -> frozenset[str]:
    """Queued tasks when no focus queue is wired (tests of the TODO manager alone).

    Returns:
        No id.
    """
    return frozenset()


def focus_applicable(tasks: Sequence[Task], action: ActionIdEnum, queued: frozenset[str]) -> tuple[Task, ...]:
    """Keep the selected tasks "Add to focus" or "Remove from focus" applies to.

    Args:
        tasks: Selected tasks.
        action: ``FOCUS_ADD_SELECTED`` or ``FOCUS_REMOVE_SELECTED``.
        queued: Ids of the queued tasks.

    Returns:
        The open tasks not queued yet (add), or the queued tasks (remove).
    """
    if action is ActionIdEnum.FOCUS_REMOVE_SELECTED:
        return tuple(task for task in tasks if task.id in queued)
    return tuple(task for task in tasks if task.state is TaskStateEnum.OPEN and task.id not in queued)


def applicable(tasks: Sequence[Task], action: ActionIdEnum) -> tuple[Task, ...]:
    """Keep the selected tasks a state action applies to (Reopen in a mixed selection reopens the done ones).

    Args:
        tasks: Selected tasks.
        action: ``TASK_COMPLETE``, ``TASK_REOPEN``, ``TASK_ARCHIVE`` or ``TASK_UNARCHIVE``.

    Returns:
        The tasks in a state the action accepts.
    """
    states = ACTION_STATES.get(action, frozenset())
    return tuple(task for task in tasks if task.state in states)


class TaskMenuBuilder:
    """Builds ``TaskMenuSnapshot`` from the selection, the lists and the busy actions."""

    def __init__(
        self,
        texts: UiTexts,
        gate: ActionGate,
        *,
        links: LinkDetector,
        max_links: int,
        queued: Callable[[], frozenset[str]] = no_task_queued,
    ) -> None:
        """Create the builder.

        Args:
            texts: Action labels.
            gate: Busy actions.
            links: Finds the links of a task ("Open link").
            max_links: Most links listed (``links.max_links_in_menu``).
            queued: Ids of the tasks in the focus queue ("Add to focus", "Remove from focus").
        """
        self._texts = texts
        self._gate = gate
        self._links = links
        self._max_links = max_links
        self._queued = queued

    def queued_task_ids(self) -> frozenset[str]:
        """Return the tasks in the focus queue (the stars of the table).

        Returns:
            Their ids.
        """
        return self._queued()

    def build(self, selected: Sequence[Task], lists: TaskListsCollection, current_list_id: str) -> TaskMenuSnapshot:
        """Describe the task actions.

        Args:
            selected: Selected tasks.
            lists: Lists in tab order.
            current_list_id: List shown (``TASK_NEW`` needs one).

        Returns:
            The buttons and the "Move to list" targets.
        """
        others = tuple(item for item in lists if item.id != current_list_id)
        queued = self._queued()
        buttons = tuple(
            self._focus_button(action, selected, queued)
            if action in FOCUS_ACTIONS
            else self._button(action, selected, has_list=lists.contains(current_list_id), others=bool(others))
            for action in TASK_MENU_ACTIONS
        )
        move_enabled = bool(selected) and not self._gate.is_busy(ActionIdEnum.TASK_MOVE)
        targets = tuple(MoveTargetSnapshot(list_id=item.id, text=item.name, enabled=move_enabled) for item in others)
        links = self._link_items(selected)
        open_link = action_button(self._texts, self._gate, ActionIdEnum.LINK_OPEN, enabled=bool(links))
        return TaskMenuSnapshot(buttons=buttons, move_targets=targets, open_link=open_link, links=links)

    def _link_items(self, selected: Sequence[Task]) -> tuple[LinkMenuItemSnapshot, ...]:
        """Links of the only selected task.

        Args:
            selected: Selected tasks.

        Returns:
            Up to ``max_links`` entries, ``()`` unless exactly one task is selected.
        """
        if len(selected) != 1:
            return ()
        found = self._links.find(selected[0].text)[: self._max_links]
        return tuple(LinkMenuItemSnapshot(index=index, text=link.target.value) for index, link in enumerate(found))

    def _focus_button(self, action: ActionIdEnum, selected: Sequence[Task], queued: frozenset[str]) -> ButtonSnapshot:
        """Describe "Add to focus" or "Remove from focus".

        Args:
            action: ``FOCUS_ADD_SELECTED`` or ``FOCUS_REMOVE_SELECTED``.
            selected: Selected tasks.
            queued: Ids of the queued tasks.

        Returns:
            The button, enabled when a selected task can be added or removed.
        """
        return action_button(self._texts, self._gate, action, enabled=bool(focus_applicable(selected, action, queued)))

    def _button(
        self, action: ActionIdEnum, selected: Sequence[Task], *, has_list: bool, others: bool
    ) -> ButtonSnapshot:
        """Describe one task action.

        Args:
            action: Task action.
            selected: Selected tasks.
            has_list: Whether a list is shown.
            others: Whether another list exists.

        Returns:
            The button; "Clear due date" explains in its tooltip why a repeating task blocks it.
        """
        enabled = self._enabled(action, selected, has_list=has_list, others=others)
        button = action_button(self._texts, self._gate, action, enabled=enabled)
        if action is ActionIdEnum.TASK_CLEAR_DUE_DATE and any(task.recurrence for task in selected):
            return replace(button, tooltip=self._texts.issue_message(NEEDS_DUE_DATE))
        return button

    @staticmethod
    def _enabled(action: ActionIdEnum, selected: Sequence[Task], *, has_list: bool, others: bool) -> bool:
        """Tell whether an action applies to the selection.

        Args:
            action: Task action.
            selected: Selected tasks.
            has_list: Whether a list is shown.
            others: Whether another list exists (Move to list).

        Returns:
            Whether the action is enabled.
        """
        if action is ActionIdEnum.TASK_NEW:
            return has_list
        if action in SINGLE_TASK_ACTIONS:
            return len(selected) == 1
        if action is ActionIdEnum.TASK_MOVE:
            return bool(selected) and others
        if action in ANY_TASK_ACTIONS:
            return bool(selected)
        if action is ActionIdEnum.TASK_CLEAR_DUE_DATE:
            dated = any(task.due_date is not None for task in selected)
            return dated and not any(task.recurrence is not None for task in selected)
        return bool(applicable(selected, action))
