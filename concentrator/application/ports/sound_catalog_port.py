"""Built-in sounds and the files behind sound references."""

from typing import Protocol

from concentrator.domain.common.data_result import DataResult
from concentrator.domain.timer.sound_ref import SoundRef


class SoundCatalogPort(Protocol):
    """Lists the sounds shipped in ``assets/sounds`` and finds the file of any sound reference."""

    def builtin_sounds(self) -> tuple[SoundRef, ...]:
        """Return the built-in sounds, sorted by name.

        Returns:
            One reference per ``assets/sounds/*.mp3`` file.
        """
        ...

    def resolve(self, sound: SoundRef) -> DataResult[str]:
        """Find the file of a sound.

        Args:
            sound: Built-in sound or file reference.

        Returns:
            The absolute path with ``/`` separators, or ``AUDIO_FILE_NOT_FOUND`` (unknown built-in name,
            missing file, or an unset kind).
        """
        ...
