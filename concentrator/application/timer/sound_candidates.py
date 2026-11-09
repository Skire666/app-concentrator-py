"""Files to try for a sound that must play: the chosen one, then its default (alarm and hourly chime)."""

import logging

from concentrator.application.ports.sound_catalog_port import SoundCatalogPort
from concentrator.domain.timer.sound_ref import SoundRef

_logger = logging.getLogger(__name__)


def sound_candidates(catalog: SoundCatalogPort, sound: SoundRef, fallback: SoundRef, purpose: str) -> tuple[str, ...]:
    """Return the existing files of a chosen sound and of its default sound.

    A sound that cannot be found is logged at WARNING with its kind only (never the user's path); the
    player falls back to the system beep when no file is left.

    Args:
        catalog: Finds the sound files.
        sound: Chosen sound.
        fallback: Built-in default (``timer.default_sound`` or ``chime.default_sound``).
        purpose: ``Alarm`` or ``Chime``, for the log.

    Returns:
        Existing files, chosen first, without duplicates; empty when none exists.
    """
    paths: list[str] = []
    for candidate in (sound, fallback):
        resolved = catalog.resolve(candidate)
        if resolved.data is None:
            _logger.warning("%s sound (%s) not found; falling back", purpose, candidate.kind.name)
        elif resolved.data not in paths:
            paths.append(resolved.data)
    return tuple(paths)
