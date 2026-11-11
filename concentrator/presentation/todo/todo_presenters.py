"""The presenters of the TODO manager, handed to the Focus page as one value."""

from dataclasses import dataclass

from concentrator.presentation.todo.link_presenter import LinkPresenter
from concentrator.presentation.todo.list_edit_presenter import ListEditPresenter
from concentrator.presentation.todo.quick_add_presenter import QuickAddPresenter
from concentrator.presentation.todo.task_actions import TaskActions
from concentrator.presentation.todo.task_details_presenter import TaskDetailsPresenter
from concentrator.presentation.todo.task_edit_presenter import TaskEditPresenter
from concentrator.presentation.todo.task_filter_presenter import TaskFilterPresenter
from concentrator.presentation.todo.task_history_presenter import TaskHistoryPresenter
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
        filters: Filter bar (due date, recurring only, search, scope).
        quick_add: Quick add field.
        table: Task table.
        details: Details pane.
        history: History tab of the details pane.
        links: Clicks on the links of the tasks.
        task_editor: Task dialog.
        list_editor: List dialog.
        actions: Task actions (keyboard shortcuts).
        refresher: Follows the data and "Reset layout".
    """

    tabs: TodoTabsPresenter
    toolbar: TodoToolbarPresenter
    filters: TaskFilterPresenter
    quick_add: QuickAddPresenter
    table: TaskTablePresenter
    details: TaskDetailsPresenter
    history: TaskHistoryPresenter
    links: LinkPresenter
    task_editor: TaskEditPresenter
    list_editor: ListEditPresenter
    actions: TaskActions
    refresher: TodoRefresher
