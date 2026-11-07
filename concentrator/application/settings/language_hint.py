"""Language of the startup dialogs, remembered in ``ui-state.ini`` (ADR-027).

The data file stays the source of truth once loaded; the hint only serves the dialogs shown before
it is (first run, recovery).
"""

from typing import Final

from concentrator.application.ports.view_preferences_port import ViewPreferencesPort
from concentrator.domain.settings.language_enum import LanguageEnum

LANGUAGE_HINT_KEY: Final = "shell/language_hint"


class LanguageHint:
    """Reads and writes ``shell/language_hint`` (an ISO 639-1 code)."""

    def __init__(self, preferences: ViewPreferencesPort) -> None:
        """Create the hint.

        Args:
            preferences: ``ui-state.ini`` adapter.
        """
        self._preferences = preferences

    def read(self) -> LanguageEnum:
        """Return the remembered language.

        Returns:
            The language, ``UNSET`` when none is remembered, ``UNKNOWN`` for an unsupported code.
        """
        value = self._preferences.get_text(LANGUAGE_HINT_KEY)
        return LanguageEnum.UNSET if value is None else LanguageEnum.from_iso_code(value)

    def write(self, language: LanguageEnum) -> None:
        """Remember a language (``UNKNOWN`` and ``UNSET`` are ignored).

        Args:
            language: Current UI language.
        """
        if language.is_set:
            self._preferences.set_text(LANGUAGE_HINT_KEY, language.iso_code)
