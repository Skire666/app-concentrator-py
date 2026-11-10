"""The four chime fields (sound, volume, first and last hour), shared by the chime dialog and the settings page."""

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.application.timer.timer_queries import TimerQueries
from concentrator.domain.timer.hourly_chime_rules import END_HOUR_FIELD, START_HOUR_FIELD
from concentrator.domain.timer.timer_config_rules import SOUND_FIELD, VOLUME_FIELD
from concentrator.domain.timer.volume import MAX_VOLUME_PERCENT
from concentrator.presentation.common.action_button import action_button
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.ui_texts import UiTexts
from concentrator.presentation.timer.chime_hours import hour_options
from concentrator.presentation.timer.chime_settings_form import ChimeSettingsForm
from concentrator.presentation.timer.chime_settings_snapshot import ChimeFieldsSnapshot, HourRangeSnapshot
from concentrator.presentation.timer.sound_choices import SoundChoices
from concentrator.presentation.timer.timer_edit_snapshot import VolumeInputSnapshot


class ChimeFields:
    """Describes the fields of a chime form and applies the choice of a sound in the list."""

    def __init__(
        self,
        translator: TranslatorPort,
        gate: ActionGate,
        sounds: TimerQueries,
        *,
        actions: tuple[ActionIdEnum, ActionIdEnum],
    ) -> None:
        """Create the helper.

        Args:
            translator: Current-language translator.
            gate: Busy state of the field buttons.
            sounds: Built-in sounds.
            actions: Actions of the "Preview" and "Choose an MP3 file..." buttons.
        """
        self._translator = translator
        self._texts = UiTexts(translator)
        self._gate = gate
        self._choices = SoundChoices(translator, sounds.builtin_sounds)
        self._preview, self._choose_file = actions

    def reset_choices(self) -> None:
        """Forget the files met while the form was open (a new form starts)."""
        self._choices.reset()

    def select_sound(self, form: ChimeSettingsForm, index: int) -> bool:
        """Apply the choice of a sound in the list.

        Args:
            form: Form being edited.
            index: Index among the options of the last snapshot.

        Returns:
            Whether the index was valid.
        """
        choices = self._choices.choices(form.baseline.sound, form.draft.sound)
        if not 0 <= index < len(choices):
            return False
        form.set_sound(choices[index])
        return True

    def snapshot(self, form: ChimeSettingsForm) -> ChimeFieldsSnapshot:
        """Describe the fields of a form.

        Args:
            form: Form being edited.

        Returns:
            The fields snapshot.
        """
        return ChimeFieldsSnapshot(
            sound=self._choices.picker(
                label=self._translator.tr("chime.edit.sound"),
                baseline=form.baseline.sound,
                draft=form.draft.sound,
                choose_file=action_button(self._texts, self._gate, self._choose_file),
                error=self._texts.field_message(form.errors, SOUND_FIELD),
            ),
            volume=self._volume(form),
            hours=self._hours(form),
        )

    def _volume(self, form: ChimeSettingsForm) -> VolumeInputSnapshot:
        """Describe the volume field.

        Args:
            form: Form being edited.

        Returns:
            The field snapshot.
        """
        percent = form.draft.volume.percent
        return VolumeInputSnapshot(
            label=self._translator.tr("chime.edit.volume"),
            value=percent,
            maximum=MAX_VOLUME_PERCENT,
            value_text=self._translator.tr("timer.edit.volume_value", percent=percent),
            preview=action_button(self._texts, self._gate, self._preview),
            error=self._texts.field_message(form.errors, VOLUME_FIELD),
        )

    def _hours(self, form: ChimeSettingsForm) -> HourRangeSnapshot:
        """Describe the active hours.

        Args:
            form: Form being edited.

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
            start_error=self._texts.field_message(form.errors, START_HOUR_FIELD),
            end_error=self._texts.field_message(form.errors, END_HOUR_FIELD),
        )
