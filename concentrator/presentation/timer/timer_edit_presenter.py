"""Timer edit dialog: duration, sound, volume, play count, automatic stop (phase 2 spec)."""

import logging
from collections.abc import Callable
from pathlib import PurePosixPath
from typing import Final

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.application.timer.sound_preview import SoundPreview
from concentrator.application.timer.timer_commands import TimerCommands
from concentrator.application.timer.timer_queries import TimerQueries
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.timer.sound_kind_enum import SoundKindEnum
from concentrator.domain.timer.sound_ref import SoundRef
from concentrator.domain.timer.timer_limits import TimerLimits
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.ports.dialog_port import DialogPort
from concentrator.presentation.ports.timer_edit_dialog_port import TimerEditDialogPort
from concentrator.presentation.timer.timer_edit_form import TimerEditForm
from concentrator.presentation.timer.timer_edit_snapshot import TimerEditSnapshot
from concentrator.presentation.timer.timer_edit_view import TimerEditView

_logger = logging.getLogger(__name__)

_NOT_ATTACHED: Final = "TimerEditPresenter.attach() was not called"


class TimerEditPresenter:
    """Owns the edit form while the dialog is open; builds ``TIMER_EDIT`` and handles its controls."""

    def __init__(
        self,
        translator: TranslatorPort,
        gate: ActionGate,
        renderer: RenderCoordinator,
        queries: TimerQueries,
        commands: TimerCommands,
        preview: SoundPreview,
        limits: TimerLimits,
    ) -> None:
        """Create the presenter; the dialog and the dialog service come with ``attach``.

        Args:
            translator: Current-language translator.
            gate: Runs every user action.
            renderer: Receives the render requests.
            queries: Stored configuration, built-in sounds, sound check, timer state.
            commands: Stores the edited configuration.
            preview: Plays the sound being edited.
            limits: Bounds from ``concentrator.ini``.
        """
        self._translator = translator
        self._gate = gate
        self._renderer = renderer
        self._queries = queries
        self._commands = commands
        self._preview = preview
        self._limits = limits
        self._window: TimerEditDialogPort | None = None
        self._dialogs: DialogPort | None = None
        self._form: TimerEditForm | None = None
        self._view = TimerEditView(translator, gate, queries, limits)
        self._actions: dict[ActionIdEnum, tuple[Callable[[], ValidationResult], bool]] = {
            ActionIdEnum.TIMER_EDIT_SAVE: (self._save, False),
            ActionIdEnum.TIMER_EDIT_CANCEL: (self._cancel, False),
            ActionIdEnum.TIMER_SOUND_PREVIEW: (self._play_preview, False),
            ActionIdEnum.TIMER_SOUND_CHOOSE_FILE: (self._choose_file, True),
        }

    def attach(self, window: TimerEditDialogPort, dialogs: DialogPort) -> None:
        """Set the dialog and the dialog service (built with the main window).

        Args:
            window: The edit dialog.
            dialogs: Confirmations and file picker over the main window (ADR-036).
        """
        self._window = window
        self._dialogs = dialogs

    def open(self) -> ValidationResult:
        """Edit the stored configuration in the modal dialog (``TIMER_EDIT``).

        Returns:
            Success once the dialog closed.
        """
        self._form = TimerEditForm(self._queries.settings(), self._limits, self._queries.check_sound)
        self._view.reset()
        self._attached_window().show_editor()
        self._preview.stop()
        return ValidationResult.success()

    def build_snapshot(self) -> TimerEditSnapshot:
        """Describe the dialog.

        Returns:
            The snapshot of the draft (of the stored configuration before the first opening).
        """
        return self._view.build(self._current_form())

    def on_duration_changed(self, hours: int, minutes: int, seconds: int) -> None:
        """Handle a change of the duration fields.

        Args:
            hours: Hours.
            minutes: Minutes.
            seconds: Seconds.
        """
        self._edit(lambda form: form.set_duration(hours, minutes, seconds))

    def on_sound_selected(self, index: int) -> None:
        """Handle the choice of a sound in the list.

        Args:
            index: Index among the options of the snapshot.
        """
        choices = self._view.sound_choices(self._current_form())
        if 0 <= index < len(choices):
            self._edit(lambda form: form.set_sound(choices[index]))

    def on_volume_changed(self, percent: int) -> None:
        """Handle a move of the volume slider.

        Args:
            percent: Volume.
        """
        self._edit(lambda form: form.set_volume(percent))

    def on_loop_count_changed(self, count: int) -> None:
        """Handle a change of the play count.

        Args:
            count: Number of plays.
        """
        self._edit(lambda form: form.set_loop_count(count))

    def on_loop_forever_changed(self, forever: bool) -> None:
        """Handle the "Repeat until stopped" check box.

        Args:
            forever: Whether it is checked.
        """
        self._edit(lambda form: form.set_loop_forever(forever))

    def on_auto_stop_changed(self, seconds: int) -> None:
        """Handle a change of the automatic stop.

        Args:
            seconds: Delay, ``0`` for never.
        """
        self._edit(lambda form: form.set_auto_stop(seconds))

    def on_auto_restart_changed(self, restart: bool) -> None:
        """Handle the "Restart automatically" check box.

        Args:
            restart: Whether it is checked.
        """
        self._edit(lambda form: form.set_auto_restart(restart))

    def on_action_requested(self, action_value: int) -> None:
        """Handle a button of the dialog.

        Args:
            action_value: ``ActionIdEnum`` value emitted by the panel.
        """
        action = ActionIdEnum.parse(action_value)
        handler = self._actions.get(action)
        if handler is None:
            _logger.warning("Timer edit action %s (%d) is not handled", action.name, action_value)
            return
        operation, interactive = handler
        result = self._gate.run(action, operation, interactive=interactive)
        if result.is_failure:
            _logger.warning("Timer edit action %s: %s", action.name, [code.name for code in result.error_codes])
        self._renderer.request(RenderSectionEnum.TIMER_EDIT)

    def _edit(self, change: Callable[[TimerEditForm], None]) -> None:
        """Apply a change to the draft and re-render.

        Args:
            change: Form setter.
        """
        change(self._current_form())
        self._renderer.request(RenderSectionEnum.TIMER_EDIT)

    def _save(self) -> ValidationResult:
        """Store the draft and close the dialog.

        Returns:
            Success, skipped when there is nothing valid to save, or the failure.
        """
        form = self._current_form()
        if not form.can_submit:
            return ValidationResult.skipped()
        result = self._commands.update_config(form.draft)
        if result.is_failure:
            return result
        form.commit()
        self._preview.stop()
        self._attached_window().close_editor()
        return result

    def _cancel(self) -> ValidationResult:
        """Close the dialog without saving and without asking (owner decision, ADR-038).

        Returns:
            Success.
        """
        self._preview.stop()
        self._attached_window().close_editor()
        return ValidationResult.success()

    def _play_preview(self) -> ValidationResult:
        """Play the sound of the draft once at the draft volume.

        Returns:
            The preview result.
        """
        draft = self._current_form().draft
        return self._preview.play(draft.sound, draft.volume)

    def _choose_file(self) -> ValidationResult:
        """Pick an audio file and make it the draft's sound.

        Returns:
            Success (also when the picker is cancelled).
        """
        tr = self._translator.tr
        draft_sound = self._current_form().draft.sound
        directory = str(PurePosixPath(draft_sound.value).parent) if draft_sound.kind is SoundKindEnum.FILE else ""
        path = self._attached_dialogs().choose_open_file(
            tr("sound.file_dialog.title"), directory, tr("sound.file_dialog.filter")
        )
        if path is not None:
            sound = SoundRef.file(path)
            self._edit(lambda form: form.set_sound(sound))
        return ValidationResult.success()

    def _current_form(self) -> TimerEditForm:
        """Return the form being edited, created from the stored configuration if none is open.

        Returns:
            The form.
        """
        if self._form is None:
            self._form = TimerEditForm(self._queries.settings(), self._limits, self._queries.check_sound)
        return self._form

    def _attached_window(self) -> TimerEditDialogPort:
        """The dialog.

        Returns:
            The dialog given to ``attach``.

        Raises:
            RuntimeError: If ``attach`` was not called (a wiring error).
        """
        if self._window is None:
            raise RuntimeError(_NOT_ATTACHED)
        return self._window

    def _attached_dialogs(self) -> DialogPort:
        """The dialog service.

        Returns:
            The service given to ``attach``.

        Raises:
            RuntimeError: If ``attach`` was not called (a wiring error).
        """
        if self._dialogs is None:
            raise RuntimeError(_NOT_ATTACHED)
        return self._dialogs
