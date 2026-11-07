"""``SoundCatalogPort`` on the ``assets/sounds`` folder and the file system."""

import logging
from pathlib import Path
from typing import Final, override

from concentrator.application.ports.sound_catalog_port import SoundCatalogPort
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.timer.sound_kind_enum import SoundKindEnum
from concentrator.domain.timer.sound_ref import SoundRef

_logger = logging.getLogger(__name__)

SOUND_SUFFIX: Final = ".mp3"
_NOT_FOUND: Final = ValidationResult.failure(ErrorCodeEnum.AUDIO_FILE_NOT_FOUND)


class BuiltinSoundCatalog(SoundCatalogPort):
    """Built-in sounds are the ``*.mp3`` files of the sounds folder, named by their stem.

    Files chosen by the user are only checked for existence, as given (``C:/``, ``D:/``, UNC).
    """

    def __init__(self, sounds_dir: Path) -> None:
        """Create the catalog.

        Args:
            sounds_dir: ``assets/sounds`` (bundled in the frozen build).
        """
        self._sounds_dir = sounds_dir

    @override
    def builtin_sounds(self) -> tuple[SoundRef, ...]:
        try:
            files = [path for path in self._sounds_dir.iterdir() if path.suffix.lower() == SOUND_SUFFIX]
        except OSError as error:
            _logger.warning("Cannot list the built-in sounds in %s: %s", self._sounds_dir, error)
            return ()
        return tuple(SoundRef.builtin(path.stem) for path in sorted(files, key=lambda path: path.stem))

    @override
    def resolve(self, sound: SoundRef) -> DataResult[str]:
        path = self._path_of(sound)
        if path is None or not path.is_file():
            return DataResult.fail(_NOT_FOUND)
        return DataResult.ok(path.as_posix())

    def _path_of(self, sound: SoundRef) -> Path | None:
        """Return where the file of a sound should be.

        Args:
            sound: Sound reference.

        Returns:
            The path, or ``None`` for an unset kind, an empty value or a built-in name with a folder.
        """
        if not sound.value:
            return None
        if sound.kind is SoundKindEnum.FILE:
            return Path(sound.value)
        if sound.kind is SoundKindEnum.BUILTIN and Path(sound.value).name == sound.value:
            return self._sounds_dir / f"{sound.value}{SOUND_SUFFIX}"
        return None
