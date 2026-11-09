"""The sound list of an edit dialog (timer alarm, hourly chime)."""

from collections.abc import Callable
from pathlib import PurePosixPath

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.domain.timer.sound_kind_enum import SoundKindEnum
from concentrator.domain.timer.sound_ref import SoundRef
from concentrator.presentation.common.button_snapshot import ButtonSnapshot
from concentrator.presentation.timer.timer_edit_snapshot import SoundPickerSnapshot


class SoundChoices:
    """Built-in sounds, then the other sounds met while the dialog is open (stored or chosen files)."""

    def __init__(self, translator: TranslatorPort, builtin: Callable[[], tuple[SoundRef, ...]]) -> None:
        """Create the list.

        Args:
            translator: Current-language translator.
            builtin: Returns the built-in sounds, sorted by name.
        """
        self._translator = translator
        self._builtin = builtin
        self._custom: list[SoundRef] = []

    def reset(self) -> None:
        """Forget the other sounds (the dialog opens again)."""
        self._custom = []

    def choices(self, baseline: SoundRef, draft: SoundRef) -> tuple[SoundRef, ...]:
        """Return the sounds of the list; the stored and the edited sounds are always part of it.

        Args:
            baseline: Sound of the stored settings.
            draft: Sound being edited.

        Returns:
            The choices, without duplicates.
        """
        builtin = self._builtin()
        for sound in (baseline, draft):
            if sound not in builtin and sound not in self._custom:
                self._custom.append(sound)
        return (*builtin, *self._custom)

    def picker(
        self, *, label: str, baseline: SoundRef, draft: SoundRef, choose_file: ButtonSnapshot, error: str
    ) -> SoundPickerSnapshot:
        """Describe the sound field.

        Args:
            label: Field label.
            baseline: Sound of the stored settings.
            draft: Sound being edited (selected).
            choose_file: "Choose an MP3 file..." button.
            error: Inline message, ``""`` when valid.

        Returns:
            The field snapshot.
        """
        choices = self.choices(baseline, draft)
        labels = [self._label(sound) for sound in choices]
        return SoundPickerSnapshot(
            label=label,
            options=tuple(text for text, _tooltip in labels),
            tooltips=tuple(tooltip for _text, tooltip in labels),
            selected=choices.index(draft),
            choose_file=choose_file,
            error=error,
        )

    def _label(self, sound: SoundRef) -> tuple[str, str]:
        """Return the text and tooltip of a choice.

        Args:
            sound: Choice.

        Returns:
            The label (a built-in sound without catalog label shows its name) and the tooltip (the full
            path of a file).
        """
        if sound.kind is SoundKindEnum.FILE:
            return self._translator.tr("sound.file.label", name=PurePosixPath(sound.value).name), sound.value
        key = f"sound.builtin.{sound.value}"
        return (self._translator.tr(key) if self._translator.has(key) else sound.value), ""
