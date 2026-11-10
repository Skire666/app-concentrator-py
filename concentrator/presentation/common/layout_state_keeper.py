"""Persistence of Qt layout state (geometry, splitters, header states) as opaque strings.

Qt blobs cross the presentation layer as base64 strings: the ui encodes and decodes them, this class
stores them through ``ViewPreferencesPort`` (ADR-022).
"""

from typing import Final

from concentrator.application.ports.view_preferences_port import ViewPreferencesPort
from concentrator.presentation.common.layout_keys import LAYOUT_GROUP, LAYOUT_PREFIX

_KEY_OUTSIDE_LAYOUT: Final = f"layout keys must start with {LAYOUT_PREFIX!r}"


def _checked(key: str) -> str:
    """Reject a key outside the ``layout/`` namespace (programming error).

    Args:
        key: Layout key.

    Returns:
        The key.

    Raises:
        ValueError: If the key does not start with ``layout/``.
    """
    if not key.startswith(LAYOUT_PREFIX):
        raise ValueError(_KEY_OUTSIDE_LAYOUT)
    return key


class LayoutStateKeeper:
    """Loads and saves layout blobs under ``layout/*`` keys."""

    def __init__(self, preferences: ViewPreferencesPort) -> None:
        """Create a keeper.

        Args:
            preferences: Store of ``ui-state.ini``.
        """
        self._preferences = preferences

    def load(self, key: str) -> str | None:
        """Read a layout blob.

        Args:
            key: Constant from ``layout_keys``.

        Returns:
            The base64 blob, or ``None`` when nothing was saved yet (the ui then uses the ini defaults).
        """
        return self._preferences.get_text(_checked(key))

    def reset(self) -> None:
        """Remove every ``layout/*`` key ("Reset layout"); the data file path and other keys are kept."""
        self._preferences.remove_group(LAYOUT_GROUP)

    def save(self, key: str, value: str) -> None:
        """Store a layout blob.

        Args:
            key: Constant from ``layout_keys``.
            value: Base64 blob exported by the ui.
        """
        self._preferences.set_text(_checked(key), value)
