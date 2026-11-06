"""Storage of UI-only state (``ui-state.ini``)."""

from typing import Protocol


class ViewPreferencesPort(Protocol):
    """String key-value store for UI state: layout blobs, sorts, filters, remembered paths.

    Keys are slash-separated (``layout/main_window/geometry``). Values are opaque strings.
    """

    def get_text(self, key: str) -> str | None:
        """Read a value.

        Args:
            key: Preference key.

        Returns:
            The stored value, or ``None`` when the key was never written.
        """
        ...

    def set_text(self, key: str, value: str) -> None:
        """Write a value.

        Args:
            key: Preference key.
            value: Value to store.
        """
        ...

    def remove(self, key: str) -> None:
        """Delete a value; does nothing when the key is absent.

        Args:
            key: Preference key.
        """
        ...
