"""The list chosen for the quick-add field of the focus queue (a view preference, not a layout key)."""

from typing import Final

from concentrator.application.focus.focus_queries import FocusQueries
from concentrator.application.ports.view_preferences_port import ViewPreferencesPort
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.todo.task_list import TaskList
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum

QUICK_ADD_LIST_KEY: Final = "focus/quick_add_list_id"
"""View preference holding the chosen list; "Reset layout" keeps it (it is not under ``layout/``)."""


class QuickAddListChoice:
    """Reads and stores the quick-add list; the Inbox is used when it is unset or gone (phase 7 spec)."""

    def __init__(self, preferences: ViewPreferencesPort, queries: FocusQueries, renderer: RenderCoordinator) -> None:
        """Create the choice.

        Args:
            preferences: ``ui-state.ini`` values.
            queries: Finds the list.
            renderer: Receives the render requests (the quick-add hint names the list).
        """
        self._preferences = preferences
        self._queries = queries
        self._renderer = renderer

    @property
    def preferred_id(self) -> str:
        """List chosen by the user, ``""`` for none."""
        return self._preferences.get_text(QUICK_ADD_LIST_KEY) or ""

    def current(self) -> TaskList | None:
        """Return the list that receives a quick-added task.

        Returns:
            The chosen list, else the Inbox, ``None`` when an Inbox will be created.
        """
        return self._queries.quick_add_list(self.preferred_id)

    def choose(self, list_id: str) -> ValidationResult:
        """Use a list for the quick add (``FOCUS_SET_QUICK_ADD_LIST``).

        Args:
            list_id: List of the tab.

        Returns:
            Success.
        """
        self._preferences.set_text(QUICK_ADD_LIST_KEY, list_id)
        self._renderer.request(RenderSectionEnum.TODO_TABS, RenderSectionEnum.FOCUS_QUEUE)
        return ValidationResult.success()
