"""Snapshot of the timer edit dialog, built from its form (``TIMER_EDIT``)."""

from typing import Final

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.application.timer.timer_queries import TimerQueries
from concentrator.domain.timer.sound_ref import SoundRef
from concentrator.domain.timer.timer_config_rules import (
    AUTO_STOP_FIELD,
    DURATION_FIELD,
    LOOP_COUNT_FIELD,
    SOUND_FIELD,
    VOLUME_FIELD,
)
from concentrator.domain.timer.timer_limits import TimerLimits
from concentrator.domain.timer.timer_state_enum import TimerStateEnum
from concentrator.domain.timer.volume import MAX_VOLUME_PERCENT
from concentrator.presentation.common.action_button import action_button
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.button_snapshot import ButtonSnapshot
from concentrator.presentation.common.ui_texts import UiTexts
from concentrator.presentation.timer.duration_input import duration_input
from concentrator.presentation.timer.sound_choices import SoundChoices
from concentrator.presentation.timer.timer_edit_form import TimerEditForm
from concentrator.presentation.timer.timer_edit_snapshot import (
    AutoStopInputSnapshot,
    DurationInputSnapshot,
    LoopInputSnapshot,
    SoundPickerSnapshot,
    TimerEditSnapshot,
    VolumeInputSnapshot,
)

COUNTING_STATES: Final = frozenset({TimerStateEnum.RUNNING, TimerStateEnum.PAUSED})


class TimerEditView:
    """Translates the form into the dialog snapshot; remembers the custom sounds met while it is open."""

    def __init__(
        self, translator: TranslatorPort, gate: ActionGate, queries: TimerQueries, limits: TimerLimits
    ) -> None:
        """Create the view.

        Args:
            translator: Current-language translator.
            gate: Busy state of the dialog buttons.
            queries: Built-in sounds and timer state.
            limits: Bounds from ``concentrator.ini``.
        """
        self._translator = translator
        self._texts = UiTexts(translator)
        self._gate = gate
        self._queries = queries
        self._limits = limits
        self._sounds = SoundChoices(translator, queries.builtin_sounds)

    def reset(self) -> None:
        """Forget the custom sounds (the dialog opens again)."""
        self._sounds.reset()

    def build(self, form: TimerEditForm) -> TimerEditSnapshot:
        """Describe the dialog.

        Args:
            form: Form being edited.

        Returns:
            The snapshot.
        """
        tr = self._translator.tr
        counting = self._queries.current_view().state in COUNTING_STATES
        return TimerEditSnapshot(
            title=tr("timer.edit.title"),
            duration=self._duration_input(form),
            sound=self._sound_picker(form),
            volume=self._volume_input(form),
            loops=self._loop_input(form),
            auto_stop=self._auto_stop_input(form),
            note=tr("timer.edit.running_note") if counting else "",
            save=self._button(ActionIdEnum.TIMER_EDIT_SAVE, enabled=form.can_submit),
            cancel=self._button(ActionIdEnum.TIMER_EDIT_CANCEL),
        )

    def sound_choices(self, form: TimerEditForm) -> tuple[SoundRef, ...]:
        """Return the sounds of the list: built-in ones, then the others met in this dialog.

        Args:
            form: Current form.

        Returns:
            The choices, without duplicates.
        """
        return self._sounds.choices(form.baseline.sound, form.draft.sound)

    def _duration_input(self, form: TimerEditForm) -> DurationInputSnapshot:
        """Describe the duration field.

        Args:
            form: Current form.

        Returns:
            The field snapshot.
        """
        return duration_input(
            self._translator,
            label=self._translator.tr("timer.edit.duration"),
            duration=form.draft.duration,
            max_duration_seconds=self._limits.max_duration_seconds,
            error=self._error(form, DURATION_FIELD),
        )

    def _sound_picker(self, form: TimerEditForm) -> SoundPickerSnapshot:
        """Describe the sound field.

        Args:
            form: Current form.

        Returns:
            The field snapshot.
        """
        return self._sounds.picker(
            label=self._translator.tr("timer.edit.sound"),
            baseline=form.baseline.sound,
            draft=form.draft.sound,
            choose_file=self._button(ActionIdEnum.TIMER_SOUND_CHOOSE_FILE),
            error=self._error(form, SOUND_FIELD),
        )

    def _volume_input(self, form: TimerEditForm) -> VolumeInputSnapshot:
        """Describe the volume field.

        Args:
            form: Current form.

        Returns:
            The field snapshot.
        """
        percent = form.draft.volume.percent
        return VolumeInputSnapshot(
            label=self._translator.tr("timer.edit.volume"),
            value=percent,
            maximum=MAX_VOLUME_PERCENT,
            value_text=self._translator.tr("timer.edit.volume_value", percent=percent),
            preview=self._button(ActionIdEnum.TIMER_SOUND_PREVIEW),
            error=self._error(form, VOLUME_FIELD),
        )

    def _loop_input(self, form: TimerEditForm) -> LoopInputSnapshot:
        """Describe the play count field.

        Args:
            form: Current form.

        Returns:
            The field snapshot.
        """
        draft = form.draft
        return LoopInputSnapshot(
            label=self._translator.tr("timer.edit.plays"),
            count=draft.loop_count,
            maximum=self._limits.max_loop_count,
            count_enabled=not draft.loop_forever,
            forever_label=self._translator.tr("timer.edit.loop_forever"),
            forever=draft.loop_forever,
            error=self._error(form, LOOP_COUNT_FIELD),
        )

    def _auto_stop_input(self, form: TimerEditForm) -> AutoStopInputSnapshot:
        """Describe the automatic stop field.

        Args:
            form: Current form.

        Returns:
            The field snapshot.
        """
        tr = self._translator.tr
        draft = form.draft
        return AutoStopInputSnapshot(
            label=tr("timer.edit.auto_stop"),
            seconds=draft.auto_stop_seconds,
            maximum=self._limits.max_auto_stop_seconds,
            unit=tr("timer.edit.unit.auto_stop"),
            restart_label=tr("timer.edit.auto_restart"),
            restart=draft.auto_restart,
            restart_enabled=draft.auto_stop_seconds > 0,
            error=self._error(form, AUTO_STOP_FIELD),
        )

    def _error(self, form: TimerEditForm, field: str) -> str:
        """Return the inline message of a field (failures and warnings).

        Args:
            form: Current form.
            field: Field path of the rules, ``sound`` also covering ``sound.kind``.

        Returns:
            The first message, ``""`` when the field is valid.
        """
        return self._texts.field_message(form.errors, field)

    def _button(self, action: ActionIdEnum, *, enabled: bool = True) -> ButtonSnapshot:
        """Describe a dialog button.

        Args:
            action: Its action.
            enabled: Whether the form allows it.

        Returns:
            The button snapshot.
        """
        return action_button(self._texts, self._gate, action, enabled=enabled)
