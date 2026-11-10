"""The presenters of the TODO manager, handed to the Focus page as one value."""

from dataclasses import dataclass

from concentrator.presentation.common.layout_state_keeper import LayoutStateKeeper
from concentrator.presentation.todo.list_edit_presenter import ListEditPresenter
from concentrator.presentation.todo.quick_add_presenter import QuickAddPresenter
from concentrator.presentation.todo.task_actions import TaskActions
from concentrator.presentation.todo.task_details_presenter import TaskDetailsPresenter
from concentrator.presentation.todo.task_edit_presenter import TaskEditPresenter
from concentrator.presentation.todo.task_table_presenter import TaskTablePresenter
from concentrator.presentation.todo.todo_refresher import TodoRefresher
from concentrator.presentation.todo.todo_tabs_presenter import TodoTabsPresenter
from concentrator.presentation.todo.todo_toolbar_presenter import TodoToolbarPresenter


@dataclass(frozen=True, slots=True, kw_only=True)
class TodoPresenters:
    """Everything zone 1 and its dialogs talk to.

    Attributes:
        tabs: List tabs and list actions.
        toolbar: Task toolbar and toggles.
        quick_add: Quick add field.
        table: Task table.
        details: Details pane.
        task_editor: Task dialog.
        list_editor: List dialog.
        actions: Task actions (keyboard shortcuts).
        refresher: Follows the data and "Reset layout".
        layout: ``layout/*`` keys (table header and splitter of zone 1).
    """

    tabs: TodoTabsPresenter
    toolbar: TodoToolbarPresenter
    quick_add: QuickAddPresenter
    table: TaskTablePresenter
    details: TaskDetailsPresenter
    task_editor: TaskEditPresenter
    list_editor: ListEditPresenter
    actions: TaskActions
    refresher: TodoRefresher
    layout: LayoutStateKeeper
