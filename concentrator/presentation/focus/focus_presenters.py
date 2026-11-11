"""The presenters of the focus queue, handed to the Focus page as one value."""

from dataclasses import dataclass

from concentrator.presentation.focus.focus_queue_presenter import FocusQueuePresenter
from concentrator.presentation.focus.focus_task_actions import FocusTaskActions


@dataclass(frozen=True, slots=True, kw_only=True)
class FocusPresenters:
    """Everything the focus queue of zone 2 and the star of zone 1 talk to.

    Attributes:
        queue: Focus queue panel.
        actions: Star of the task table, "Add to focus" and "Remove from focus".
    """

    queue: FocusQueuePresenter
    actions: FocusTaskActions
