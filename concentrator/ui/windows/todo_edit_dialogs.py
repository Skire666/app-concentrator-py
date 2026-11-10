"""Task and list dialogs, run over the main window by ``ModalHost`` (ADR-036).

Escape and the close button do not close them: they send the Cancel action, and the presenter asks before
discarding changes.
"""

from typing import override

from PySide6.QtWidgets import QDialog, QVBoxLayout, QWidget

from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.ports.editor_dialog_port import EditorDialogPort
from concentrator.presentation.todo.list_edit_presenter import ListEditPresenter
from concentrator.presentation.todo.list_edit_snapshot import ListEditSnapshot
from concentrator.presentation.todo.task_edit_presenter import TaskEditPresenter
from concentrator.presentation.todo.task_edit_snapshot import TaskEditSnapshot
from concentrator.presentation.todo.todo_layout import TodoLayout
from concentrator.ui.panels.list_edit_form_panel import ListEditFormPanel
from concentrator.ui.panels.task_edit_form_panel import TaskEditFormPanel
from concentrator.ui.support.modal_host import DialogRunner


class TaskEditDialog(QDialog):
    """Hosts the task form panel; ``reject`` (Escape, close button) sends ``TASK_EDIT_CANCEL``."""

    def __init__(self, layout: TodoLayout, parent: QWidget | None) -> None:
        """Build the dialog (not shown).

        Args:
            layout: Spacing of the dialog.
            parent: Main window (Qt centers the dialog on it).
        """
        super().__init__(parent)
        self._panel = TaskEditFormPanel(layout.spacing_px, self)
        QVBoxLayout(self).addWidget(self._panel)

    @property
    def panel(self) -> TaskEditFormPanel:
        """The form panel."""
        return self._panel

    def render_snapshot(self, snapshot: TaskEditSnapshot) -> None:
        """Show the title and the fields.

        Args:
            snapshot: Dialog state.
        """
        self.setWindowTitle(snapshot.title)
        self._panel.render_snapshot(snapshot)

    @override
    def reject(self) -> None:
        self._panel.action_requested.emit(int(ActionIdEnum.TASK_EDIT_CANCEL))


class ListEditDialog(QDialog):
    """Hosts the list form panel; ``reject`` (Escape, close button) sends ``LIST_EDIT_CANCEL``."""

    def __init__(self, layout: TodoLayout, parent: QWidget | None) -> None:
        """Build the dialog (not shown).

        Args:
            layout: Spacing of the dialog.
            parent: Main window (Qt centers the dialog on it).
        """
        super().__init__(parent)
        self._panel = ListEditFormPanel(layout.spacing_px, self)
        QVBoxLayout(self).addWidget(self._panel)

    @property
    def panel(self) -> ListEditFormPanel:
        """The form panel."""
        return self._panel

    def render_snapshot(self, snapshot: ListEditSnapshot) -> None:
        """Show the title and the fields.

        Args:
            snapshot: Dialog state.
        """
        self.setWindowTitle(snapshot.title)
        self._panel.render_snapshot(snapshot)

    @override
    def reject(self) -> None:
        self._panel.action_requested.emit(int(ActionIdEnum.LIST_EDIT_CANCEL))


class TaskEditWindow(EditorDialogPort):
    """``EditorDialogPort`` on one ``TaskEditDialog``, wired to its presenter."""

    def __init__(
        self, presenter: TaskEditPresenter, renderer: RenderCoordinator, runner: DialogRunner, layout: TodoLayout
    ) -> None:
        """Build the dialog, connect its panel and register ``TASK_EDIT``.

        Args:
            presenter: Task dialog presenter.
            renderer: Render coordinator.
            runner: The main window's modal host.
            layout: Spacing of the dialog.
        """
        self._renderer = renderer
        self._runner = runner
        self._dialog = TaskEditDialog(layout, runner.parent)
        panel = self._dialog.panel
        panel.text_changed.connect(presenter.on_text_changed)
        panel.list_selected.connect(presenter.on_list_selected)
        panel.due_date_changed.connect(presenter.on_due_date_changed)
        panel.due_time_changed.connect(presenter.on_due_time_changed)
        panel.action_requested.connect(presenter.on_action_requested)
        renderer.register(RenderSectionEnum.TASK_EDIT, presenter.build_snapshot, self._dialog.render_snapshot)

    @property
    def dialog(self) -> TaskEditDialog:
        """The dialog (for tests)."""
        return self._dialog

    @override
    def show_editor(self) -> None:
        self._renderer.request(RenderSectionEnum.TASK_EDIT)
        self._renderer.flush()
        self._dialog.panel.text_input.setFocus()
        self._runner.run(self._dialog)

    @override
    def close_editor(self) -> None:
        self._dialog.done(QDialog.DialogCode.Accepted)


class ListEditWindow(EditorDialogPort):
    """``EditorDialogPort`` on one ``ListEditDialog``, wired to its presenter."""

    def __init__(
        self, presenter: ListEditPresenter, renderer: RenderCoordinator, runner: DialogRunner, layout: TodoLayout
    ) -> None:
        """Build the dialog, connect its panel and register ``LIST_EDIT``.

        Args:
            presenter: List dialog presenter.
            renderer: Render coordinator.
            runner: The main window's modal host.
            layout: Spacing of the dialog.
        """
        self._renderer = renderer
        self._runner = runner
        self._dialog = ListEditDialog(layout, runner.parent)
        panel = self._dialog.panel
        panel.name_changed.connect(presenter.on_name_changed)
        panel.description_changed.connect(presenter.on_description_changed)
        panel.priority_selected.connect(presenter.on_priority_selected)
        panel.action_requested.connect(presenter.on_action_requested)
        renderer.register(RenderSectionEnum.LIST_EDIT, presenter.build_snapshot, self._dialog.render_snapshot)

    @property
    def dialog(self) -> ListEditDialog:
        """The dialog (for tests)."""
        return self._dialog

    @override
    def show_editor(self) -> None:
        self._renderer.request(RenderSectionEnum.LIST_EDIT)
        self._renderer.flush()
        self._dialog.panel.name_input.setFocus()
        self._runner.run(self._dialog)

    @override
    def close_editor(self) -> None:
        self._dialog.done(QDialog.DialogCode.Accepted)
