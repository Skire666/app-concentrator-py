"""Plays a sound once from the edit dialog ("Preview")."""

from typing import Final

from concentrator.application.ports.sound_catalog_port import SoundCatalogPort
from concentrator.application.ports.sound_player_port import SoundPlayback, SoundPlayerPort
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.timer.sound_ref import SoundRef
from concentrator.domain.timer.volume import Volume

PREVIEW_LOOPS: Final = 1


class SoundPreview:
    """Uses its own player instance, so a preview never cuts a ringing alarm."""

    def __init__(self, player: SoundPlayerPort, catalog: SoundCatalogPort) -> None:
        """Create the preview.

        Args:
            player: Preview player instance.
            catalog: Finds the sound files.
        """
        self._player = player
        self._catalog = catalog

    def play(self, sound: SoundRef, volume: Volume) -> ValidationResult:
        """Play a sound once at a volume (the previous preview stops).

        Args:
            sound: Sound being edited.
            volume: Volume being edited.

        Returns:
            Success, ``AUDIO_FILE_NOT_FOUND`` or the player failure.
        """
        resolved = self._catalog.resolve(sound)
        if resolved.data is None:
            return resolved.validation
        return self._player.play(SoundPlayback(paths=(resolved.data,), volume=volume, loops=PREVIEW_LOOPS))

    def stop(self) -> None:
        """Stop the preview (the edit dialog closes)."""
        self._player.stop()
