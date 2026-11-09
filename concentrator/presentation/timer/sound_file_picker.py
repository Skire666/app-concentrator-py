"""Asks for an MP3 file to use as a sound (timer alarm, hourly chime)."""

from pathlib import PurePosixPath

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.domain.timer.sound_kind_enum import SoundKindEnum
from concentrator.domain.timer.sound_ref import SoundRef
from concentrator.presentation.ports.dialog_port import DialogPort


def pick_sound_file(dialogs: DialogPort, translator: TranslatorPort, current: SoundRef, title: str) -> SoundRef | None:
    """Show the file picker in the folder of the current file.

    Args:
        dialogs: Dialog service over the main window.
        translator: Current-language translator.
        current: Sound being edited.
        title: Translated window title.

    Returns:
        The chosen file, or ``None`` when the picker was cancelled.
    """
    directory = str(PurePosixPath(current.value).parent) if current.kind is SoundKindEnum.FILE else ""
    path = dialogs.choose_open_file(title, directory, translator.tr("sound.file_dialog.filter"))
    return None if path is None else SoundRef.file(path)
