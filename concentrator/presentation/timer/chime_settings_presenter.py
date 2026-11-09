"""Hourly chime dialog: sound, volume, preview and active hours."""

import logging
from collections.abc import Callable
from typing import Final

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.application.timer.chime_commands import ChimeCommands
from concentrator.application.timer.chime_queries import ChimeQueries
from concentrator.application.timer.sound_preview import SoundPreview
from concentrator.application.timer.timer_queries import TimerQueries
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.timer.hourly_chime_rules import END_HOUR_FIELD, START_HOUR_FIELD
from concentrator.domain.timer.timer_config_rules import SOUND_FIELD, VOLUME_FIELD
from concentrator.domain.timer.volume import MAX_VOLUME_PERCENT
from concentrator.presentation.common.action_button import action_button
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.common.ui_texts import UiTexts
from concentrator.presentation.ports.dialog_port import DialogPort
from concentrator.presentation.ports.editor_dialog_port import EditorDialogPort
from concentrator.presentation.timer.chime_hours import hour_options
from concentrator.presentation.timer.chime_settings_form import ChimeSettingsForm
from concentrator.presentation.timer.chime_settings_snapshot import ChimeSettingsSnapshot, HourRangeSnapshot
from concentrator.presentation.timer.sound_choices import SoundChoices
from concentrator.presentation.timer.sound_file_picker import pick_sound_file
from concentrator.presentation.timer.timer_edit_snapshot import VolumeInputSnapshot

_logger = logging.getLogger(__name__)

_NOT_ATTACHED: Final = "ChimeSettingsPresenter.attach() was not called"
CHOOSE_FILE_IS_INTERACTIVE: Final = frozenset({ActionIdEnum.CHIME_SOUND_CHOOSE_FILE})


class ChimeSettingsPresenter:
    """Owns the chime form while the dialog is open; builds ``CHIME_EDIT`` and handles its controls.

    Cancel, Escape and the close button close the dialog without asking (owner decision, ADR-038).
    """

    def __init__(
        self,
        translator: TranslatorPort,
        gate: ActionGate,
        renderer: RenderCoordinator,
        *,
        queries: ChimeQueries,
        commands: ChimeCommands,
        sounds: TimerQueries,
        preview: SoundPreview,
    ) -> None:
        """Create the presenter; the dialog and the dialog service come with ``attach``.

        Args:
            translator: Current-language translator.
            gate: Runs every user action.
            renderer: Receives the render requests.
            queries: Stored chime settings.
            commands: Stores the edited settings.
            sounds: Built-in sounds and sound check.
            preview: Plays the sound being edited.
        """
        self._translator = translator
        self._texts = UiTexts(translator)
        self._gate = gate
        self._renderer = renderer
        self._queries = queries
        self._commands = commands
        self._sounds = sounds
        self._preview = preview
        self._choices = SoundChoices(translator, sounds.builtin_sounds)
        self._window: EditorDialogPort | None = None
        self._dialogs: DialogPort | None = None
        self._form: ChimeSettingsForm | None = None
        self._actions: dict[ActionIdEnum, Callable[[], ValidationResult]] = {
            ActionIdEnum.CHIME_EDIT_SAVE: self._save,
            ActionIdEnum.CHIME_EDIT_CANCEL: self._cancel,
            ActionIdEnum.CHIME_PREVIEW: self._play_preview,
            ActionIdEnum.CHIME_SOUND_CHOOSE_FILE: self._choose_file,
        }

    def attach(self, window: EditorDialogPort, dialogs: DialogPort) -> None:
        """Set the dialog and the dialog service (built with the main window).

        Args:
            window: The chime dialog.
            dialogs: File picker over the main window (ADR-036).
        """
        self._window = window
        self._dialogs = dialogs

    def open(self) -> ValidationResult:
        """Edit the stored chime settings in the modal dialog (``CHIME_EDIT``).

        Returns:
            Success once the dialog closed.
        """
        self._form = ChimeSettingsForm(self._queries.settings(), self._sounds.check_sound)
        self._choices.reset()
        self._attached(self._window).show_editor()
        self._preview.stop()
        return ValidationResult.success()

    def build_snapshot(self) -> ChimeSettingsSnapshot:
        """Describe the dialog.

        Returns:
            The snapshot of the draft (of the stored settings before the first opening).
        """
        tr = self._translator.tr
        form = self._current_form()
        return ChimeSettingsSnapshot(
            title=tr("chime.edit.title"),
            sound=self._choices.picker(
                label=tr("chime.edit.sound"),
                baseline=form.baseline.sound,
                draft=form.draft.sound,
                choose_file=action_button(self._texts, self._gate, ActionIdEnum.CHIME_SOUND_CHOOSE_FILE),
                error=self._error(form, SOUND_FIELD),
            ),
            volume=self._volume_input(form),
            hours=self._hours(form),
            hint=tr("chime.edit.hint"),
            save=action_button(self._texts, self._gate, ActionIdEnum.CHIME_EDIT_SAVE, enabled=form.can_submit),
            cancel=action_button(self._texts, self._gate, ActionIdEnum.CHIME_EDIT_CANCEL),
        )

    def on_sound_selected(self, index: int) -> None:
        """Handle the choice of a sound in the list.

        Args:
            index: Index among the options of the snapshot.
        """
        form = self._current_form()
        choices = self._choices.choices(form.baseline.sound, form.draft.sound)
        if 0 <= index < len(choices):
            self._edit(lambda edited: edited.set_sound(choices[index]))

    def on_volume_changed(self, percent: int) -> None:
        """Handle a move of the volume slider.

        Args:
            percent: Volume.
        """
        self._edit(lambda form: form.set_volume(percent))

    def on_start_hour_changed(self, hour: int) -> None:
        """Handle the choice of the first hour.

        Args:
            hour: Index of the option, which is the hour.
        """
        self._edit(lambda form: form.set_start_hour(hour))

    def on_end_hour_changed(self, hour: int) -> None:
        """Handle the choice of the last hour.

        Args:
            hour: Index of the option, which is the hour.
        """
        self._edit(lambda form: form.set_end_hour(hour))

    def on_action_requested(self, action_value: int) -> None:
        """Handle a button of the dialog.

        Args:
            action_value: ``ActionIdEnum`` value emitted by the panel.
        """
        action = ActionIdEnum.parse(action_value)
        operation = self._actions.get(action)
        if operation is None:
            _logger.warning("Chime dialog action %s (%d) is not handled", action.name, action_value)
            return
        result = self._gate.run(action, operation, interactive=action in CHOOSE_FILE_IS_INTERACTIVE)
        if result.is_failure:
            _logger.warning("Chime dialog action %s: %s", action.name, [code.name for code in result.error_codes])
        self._renderer.request(RenderSectionEnum.CHIME_EDIT)

    def _edit(self, change: Callable[[ChimeSettingsForm], None]) -> None:
        """Apply a change to the draft and re-render.

        Args:
            change: Form setter.
        """
        change(self._current_form())
        self._renderer.request(RenderSectionEnum.CHIME_EDIT)

    def _save(self) -> ValidationResult:
        """Store the draft and close the dialog.

        Returns:
            Success, skipped when there is nothing valid to save, or the failure.
        """
        form = self._current_form()
        if not form.can_submit:
            return ValidationResult.skipped()
        result = self._commands.update_settings(form.draft)
        if result.is_failure:
            return result
        self._preview.stop()
        self._attached(self._window).close_editor()
        return result

    def _cancel(self) -> ValidationResult:
        """Close the dialog without saving and without asking.

        Returns:
            Success.
        """
        self._preview.stop()
        self._attached(self._window).close_editor()
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
        title = self._translator.tr("sound.file_dialog.chime_title")
        sound = pick_sound_file(
            self._attached(self._dialogs), self._translator, self._current_form().draft.sound, title
        )
        if sound is not None:
            self._edit(lambda form: form.set_sound(sound))
        return ValidationResult.success()

    def _volume_input(self, form: ChimeSettingsForm) -> VolumeInputSnapshot:
        """Describe the volume field.

        Args:
            form: Current form.

        Returns:
            The field snapshot.
        """
        percent = form.draft.volume.percent
        return VolumeInputSnapshot(
            label=self._translator.tr("chime.edit.volume"),
            value=percent,
            maximum=MAX_VOLUME_PERCENT,
            value_text=self._translator.tr("timer.edit.volume_value", percent=percent),
            preview=action_button(self._texts, self._gate, ActionIdEnum.CHIME_PREVIEW),
            error=self._error(form, VOLUME_FIELD),
        )

    def _hours(self, form: ChimeSettingsForm) -> HourRangeSnapshot:
        """Describe the active hours.

        Args:
            form: Current form.

        Returns:
            The field snapshot.
        """
        tr = self._translator.tr
        return HourRangeSnapshot(
            start_label=tr("chime.edit.start_hour"),
            end_label=tr("chime.edit.end_hour"),
            options=hour_options(self._translator),
            start=form.draft.start_hour,
            end=form.draft.end_hour,
            start_error=self._error(form, START_HOUR_FIELD),
            end_error=self._error(form, END_HOUR_FIELD),
        )

    def _error(self, form: ChimeSettingsForm, field: str) -> str:
        """Return the inline message of a field (failures and warnings).

        Args:
            form: Current form.
            field: Field path of the rules, ``sound`` also covering ``sound.kind``.

        Returns:
            The first message, ``""`` when the field is valid.
        """
        issues = [issue for issue in form.errors.issues if issue.field.split(".")[0] == field]
        return self._texts.issue_message(issues[0]) if issues else ""

    def _current_form(self) -> ChimeSettingsForm:
        """Return the form being edited, created from the stored settings if none is open.

        Returns:
            The form.
        """
        if self._form is None:
            self._form = ChimeSettingsForm(self._queries.settings(), self._sounds.check_sound)
        return self._form

    @staticmethod
    def _attached[T](port: T | None) -> T:
        """A port given to ``attach``.

        Args:
            port: The dialog or the dialog service.

        Returns:
            The port.

        Raises:
            RuntimeError: If ``attach`` was not called (a wiring error).
        """
        if port is None:
            raise RuntimeError(_NOT_ATTACHED)
        return port
