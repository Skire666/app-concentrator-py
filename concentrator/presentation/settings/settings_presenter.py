"""Settings page (Menu C): the form of the values stored in the data file, with Save and Revert."""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final, override

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.application.settings.settings_commands import SettingsCommands
from concentrator.application.settings.settings_defaults import SettingsDefaults
from concentrator.application.settings.settings_queries import SettingsQueries
from concentrator.application.timer.chime_commands import ChimeCommands
from concentrator.application.timer.chime_queries import ChimeQueries
from concentrator.application.timer.sound_preview import SoundPreview
from concentrator.application.timer.timer_queries import TimerQueries
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.settings.general_settings import GeneralSettings
from concentrator.domain.timer.chime_settings import ChimeSettings
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.pending_edits import PendingEdits, PendingEditsQuestion, resolve_pending_edits
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.ports.dialog_port import DialogPort
from concentrator.presentation.settings.settings_files_presenter import SettingsFilesPresenter
from concentrator.presentation.settings.settings_form import SettingsForm
from concentrator.presentation.settings.settings_form_builder import LANGUAGES, LOG_LEVELS, SettingsFormBuilder
from concentrator.presentation.settings.settings_snapshot import SettingsSnapshot
from concentrator.presentation.shell.language_switcher import LanguageSwitcher
from concentrator.presentation.shell.shell_page_enum import ShellPageEnum
from concentrator.presentation.storage.storage_messages import StorageMessages
from concentrator.presentation.timer.chime_fields import ChimeFields
from concentrator.presentation.timer.chime_settings_form import ChimeSettingsForm
from concentrator.presentation.timer.sound_file_picker import pick_sound_file

_logger = logging.getLogger(__name__)

_NOT_ATTACHED: Final = "SettingsPresenter.attach() was not called"
LINE_BREAK: Final = "\n"
INTERACTIVE_ACTIONS: Final = frozenset({ActionIdEnum.SETTINGS_SAVE, ActionIdEnum.SETTINGS_CHIME_SOUND_CHOOSE_FILE})


@dataclass(frozen=True, slots=True, kw_only=True)
class SettingsServices:
    """Use cases the settings form reads and writes.

    Attributes:
        settings_queries: Stored user settings.
        settings_commands: Stores the General values.
        defaults: General values used while no settings can be read.
        chime_queries: Stored chime.
        chime_commands: Stores the chime.
        sounds: Built-in sounds and sound check.
        preview: Plays the chime sound being edited.
        switcher: Shows a newly stored language.
    """

    settings_queries: SettingsQueries
    settings_commands: SettingsCommands
    defaults: SettingsDefaults
    chime_queries: ChimeQueries
    chime_commands: ChimeCommands
    sounds: TimerQueries
    preview: SoundPreview
    switcher: LanguageSwitcher


class SettingsPresenter(PendingEdits):
    """Builds ``SETTINGS`` (with the file sections of ``SettingsFilesPresenter``) and owns the form.

    The form follows stored values changed elsewhere (status bar language, chime dialog, another data
    file) without losing the fields the user changed. Leaving the page or quitting with unsaved changes
    asks what to do.
    """

    def __init__(
        self,
        translator: TranslatorPort,
        gate: ActionGate,
        renderer: RenderCoordinator,
        services: SettingsServices,
        files: SettingsFilesPresenter,
    ) -> None:
        """Create the presenter; the dialog service comes with ``attach``.

        Args:
            translator: Current-language translator.
            gate: Runs every user action.
            renderer: Receives the render requests.
            services: Use cases of the form.
            files: Data file, Interface and About sections.
        """
        self._translator = translator
        self._gate = gate
        self._renderer = renderer
        self._services = services
        self._files = files
        self._fields = ChimeFields(
            translator,
            gate,
            services.sounds,
            actions=(ActionIdEnum.SETTINGS_CHIME_PREVIEW, ActionIdEnum.SETTINGS_CHIME_SOUND_CHOOSE_FILE),
        )
        self._builder = SettingsFormBuilder(translator, gate, self._fields)
        self._messages = StorageMessages(translator)
        self._dialogs: DialogPort | None = None
        self._form: SettingsForm | None = None
        self._actions: dict[ActionIdEnum, Callable[[], ValidationResult]] = {
            ActionIdEnum.SETTINGS_SAVE: self.save_edits,
            ActionIdEnum.SETTINGS_REVERT: self._revert,
            ActionIdEnum.SETTINGS_CHIME_PREVIEW: self._play_preview,
            ActionIdEnum.SETTINGS_CHIME_SOUND_CHOOSE_FILE: self._choose_file,
        }

    def attach(self, dialogs: DialogPort) -> None:
        """Set the dialog service of the main window (ADR-036), also for the file sections.

        Args:
            dialogs: Questions, errors and the sound file picker.
        """
        self._dialogs = dialogs
        self._files.attach(dialogs, self)

    def build_snapshot(self) -> SettingsSnapshot:
        """Describe the page.

        Returns:
            The snapshot.
        """
        return SettingsSnapshot(form=self._builder.build(self._current_form()), files=self._files.build_snapshot())

    def on_language_selected(self, index: int) -> None:
        """Handle the choice of a language.

        Args:
            index: Index among the options of the snapshot.
        """
        if 0 <= index < len(LANGUAGES):
            self._edit(lambda form: form.set_language(LANGUAGES[index]))

    def on_log_level_selected(self, index: int) -> None:
        """Handle the choice of a journal detail level.

        Args:
            index: Index among the options of the snapshot.
        """
        if 0 <= index < len(LOG_LEVELS):
            self._edit(lambda form: form.set_log_level(LOG_LEVELS[index]))

    def on_notify_toggled(self, checked: bool) -> None:
        """Handle the taskbar alert check box.

        Args:
            checked: New state.
        """
        self._edit(lambda form: form.set_notify_when_inactive(checked))

    def on_chime_enabled_toggled(self, checked: bool) -> None:
        """Handle the "Chime every hour" check box.

        Args:
            checked: New state.
        """
        self._edit(lambda form: form.set_chime_enabled(checked))

    def on_sound_selected(self, index: int) -> None:
        """Handle the choice of a chime sound in the list.

        Args:
            index: Index among the options of the snapshot.
        """
        if self._fields.select_sound(self._current_form().chime, index):
            self._renderer.request(RenderSectionEnum.SETTINGS)

    def on_volume_changed(self, percent: int) -> None:
        """Handle a move of the chime volume slider.

        Args:
            percent: Volume.
        """
        self._edit_chime(lambda chime: chime.set_volume(percent))

    def on_start_hour_changed(self, hour: int) -> None:
        """Handle the choice of the first chime.

        Args:
            hour: Index of the option, which is the hour.
        """
        self._edit_chime(lambda chime: chime.set_start_hour(hour))

    def on_end_hour_changed(self, hour: int) -> None:
        """Handle the choice of the last chime.

        Args:
            hour: Index of the option, which is the hour.
        """
        self._edit_chime(lambda chime: chime.set_end_hour(hour))

    def on_action_requested(self, action_value: int) -> None:
        """Handle Save, Revert, Preview and "Choose an MP3 file...".

        Args:
            action_value: ``ActionIdEnum`` value emitted by the panel.
        """
        action = ActionIdEnum.parse(action_value)
        operation = self._actions.get(action)
        if operation is None:
            _logger.warning("Settings action %s (%d) is not handled", action.name, action_value)
            return
        result = self._gate.run(action, operation, interactive=action in INTERACTIVE_ACTIONS)
        if result.is_failure:
            _logger.warning("Settings action %s: %s", action.name, [code.name for code in result.error_codes])
        self._renderer.request(RenderSectionEnum.SETTINGS)

    def on_stored_values_changed(self, _event: object) -> None:
        """Follow stored values changed elsewhere; the fields the user changed keep their value.

        Args:
            _event: ``UserSettingsChangedEvent``, ``HourlyChimeChangedEvent`` or ``UserDataReplacedEvent``.
        """
        if self._form is not None:
            self._form.rebase(*self._stored())
        self._renderer.request(RenderSectionEnum.SETTINGS)

    def on_page_changed(self, page: ShellPageEnum) -> None:
        """Stop the chime preview when the page is left.

        Args:
            page: Page now shown.
        """
        if page is not ShellPageEnum.SETTINGS:
            self._services.preview.stop()

    def may_leave(self) -> bool:
        """Ask Save / Discard / Cancel before another page is shown, when the form has unsaved changes.

        Returns:
            Whether the page may be left.
        """
        tr = self._translator.tr
        question = PendingEditsQuestion(
            title=tr("settings.leave.title"),
            message=tr("settings.leave.message"),
            answers=(tr("dialog.button.save"), tr("dialog.button.discard"), tr("dialog.button.cancel")),
        )
        result = resolve_pending_edits(self, self._attached_dialogs(), question)
        self._renderer.request(RenderSectionEnum.SETTINGS)
        return result.is_success

    @override
    def has_unsaved_edits(self) -> bool:
        """Tell whether the form differs from the stored values.

        Returns:
            Whether there are unsaved changes.
        """
        return self._form is not None and self._form.is_dirty

    @override
    def save_edits(self) -> ValidationResult:
        """Store the General values, then the chime, each in one write when it changed.

        A failure is shown in an error dialog and the form keeps its changes.

        Returns:
            Success, skipped when there is nothing valid to save, or the failure.
        """
        form = self._current_form()
        if not form.can_submit:
            return ValidationResult.skipped()
        language_before = self._translator.language
        general = form.general
        result = self._services.settings_commands.save_general(general.general)
        if not result.is_failure:
            settings = form.chime.draft
            result = result.merge(self._services.chime_commands.save(enabled=general.chime_enabled, settings=settings))
        if result.is_failure:
            self._show_failure(result)
            return result
        form.rebase(*self._stored())
        if general.language is not language_before:
            self._services.switcher.follow(general.language)
        return result

    @override
    def discard_edits(self) -> None:
        """Show the stored values again (Revert)."""
        self._current_form().reset()
        self._services.preview.stop()
        self._renderer.request(RenderSectionEnum.SETTINGS)

    def _revert(self) -> ValidationResult:
        """Discard the changes.

        Returns:
            Success.
        """
        self.discard_edits()
        return ValidationResult.success()

    def _play_preview(self) -> ValidationResult:
        """Play the chime sound of the draft once at the draft volume.

        Returns:
            The preview result.
        """
        draft = self._current_form().chime.draft
        return self._services.preview.play(draft.sound, draft.volume)

    def _choose_file(self) -> ValidationResult:
        """Pick an audio file and make it the chime sound of the draft.

        Returns:
            Success (also when the picker is cancelled).
        """
        chime = self._current_form().chime
        title = self._translator.tr("sound.file_dialog.chime_title")
        sound = pick_sound_file(self._attached_dialogs(), self._translator, chime.draft.sound, title)
        if sound is not None:
            self._edit_chime(lambda form: form.set_sound(sound))
        return ValidationResult.success()

    def _edit(self, change: Callable[[SettingsForm], None]) -> None:
        """Apply a change to the draft and re-render.

        Args:
            change: Form setter.
        """
        change(self._current_form())
        self._renderer.request(RenderSectionEnum.SETTINGS)

    def _edit_chime(self, change: Callable[[ChimeSettingsForm], None]) -> None:
        """Apply a change to the chime draft and re-render.

        Args:
            change: Chime form setter.
        """
        change(self._current_form().chime)
        self._renderer.request(RenderSectionEnum.SETTINGS)

    def _current_form(self) -> SettingsForm:
        """Return the form, created from the stored values the first time.

        Returns:
            The form.
        """
        if self._form is None:
            self._form = SettingsForm(*self._stored(), self._services.sounds.check_sound)
        return self._form

    def _stored(self) -> tuple[GeneralSettings, tuple[bool, ChimeSettings]]:
        """Read the stored values.

        Returns:
            The General values (the ini defaults in the current language when none can be read) and
            the chime switch and settings.
        """
        stored = self._services.settings_queries.current_settings().data
        language = self._translator.language
        general = self._services.defaults.general(language) if stored is None else stored.general
        chime = self._services.chime_queries
        return general, (chime.enabled(), chime.settings())

    def _show_failure(self, result: ValidationResult) -> None:
        """Explain why the settings were not saved.

        Args:
            result: The failure.
        """
        tr = self._translator.tr
        message = LINE_BREAK.join(self._messages.lines(result))
        self._attached_dialogs().error(tr("settings.error.title"), message, tr("dialog.button.ok"))

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
