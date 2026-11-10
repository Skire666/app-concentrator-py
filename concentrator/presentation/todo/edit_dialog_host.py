"""Shows, closes and cancels the task and list dialogs; a changed form asks before its changes are lost."""

from typing import Final

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.ports.dialog_port import DialogPort
from concentrator.presentation.ports.editor_dialog_port import EditorDialogPort

_NOT_ATTACHED: Final = "EditDialogHost.attach() was not called"


class EditDialogHost:
    """The dialog of one form and the discard question (``AGENTS.md`` section 8.4)."""

    def __init__(self, translator: TranslatorPort, section: RenderSectionEnum, renderer: RenderCoordinator) -> None:
        """Create the host; the dialog and the dialog service come with ``attach``.

        Args:
            translator: Texts of the discard question.
            section: Section of the dialog, rendered before it opens.
            renderer: Render coordinator.
        """
        self._translator = translator
        self._section = section
        self._renderer = renderer
        self._window: EditorDialogPort | None = None
        self._dialogs: DialogPort | None = None

    def attach(self, window: EditorDialogPort, dialogs: DialogPort) -> None:
        """Set the dialog and the dialog service.

        Args:
            window: The form dialog.
            dialogs: Discard question over the main window.
        """
        self._window = window
        self._dialogs = dialogs

    def show(self) -> ValidationResult:
        """Render the form, then run the dialog until it closes.

        Returns:
            Success once the dialog closed.
        """
        window, _dialogs = self._attached()
        self._renderer.request(self._section)
        window.show_editor()
        return ValidationResult.success()

    def close(self) -> ValidationResult:
        """Close the dialog (after a save).

        Returns:
            Success.
        """
        window, _dialogs = self._attached()
        window.close_editor()
        return ValidationResult.success()

    def cancel(self, *, is_dirty: bool) -> ValidationResult:
        """Close the dialog without saving; ask first when the form changed.

        Args:
            is_dirty: Whether the form changed.

        Returns:
            Success when the dialog closed, skipped when the user kept editing.
        """
        window, dialogs = self._attached()
        if is_dirty:
            tr = self._translator.tr
            discard = dialogs.confirm(
                tr("todo.discard.title"), tr("todo.discard.message"), tr("todo.discard.accept"), tr("todo.discard.keep")
            )
            if not discard:
                return ValidationResult.skipped()
        window.close_editor()
        return ValidationResult.success()

    def _attached(self) -> tuple[EditorDialogPort, DialogPort]:
        """The dialog and the dialog service.

        Returns:
            What ``attach`` received.

        Raises:
            RuntimeError: If ``attach`` was not called (a wiring error).
        """
        if self._window is None or self._dialogs is None:
            raise RuntimeError(_NOT_ATTACHED)
        return self._window, self._dialogs
