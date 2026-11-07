"""Applies a UI language: settings, translator, startup hint, full re-render (``AGENTS.md`` section 9)."""

import logging
from types import MappingProxyType
from typing import Final

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.application.settings.language_hint import LanguageHint
from concentrator.application.settings.settings_commands import SettingsCommands
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.presentation.common.render_coordinator import RenderCoordinator

_logger = logging.getLogger(__name__)

_NEXT_LANGUAGE: Final = MappingProxyType(
    {LanguageEnum.ENGLISH: LanguageEnum.FRENCH, LanguageEnum.FRENCH: LanguageEnum.ENGLISH}
)


class LanguageSwitcher:
    """The one place that changes the UI language."""

    def __init__(
        self, translator: TranslatorPort, hint: LanguageHint, renderer: RenderCoordinator, settings: SettingsCommands
    ) -> None:
        """Create the switcher.

        Args:
            translator: Translator to switch.
            hint: ``shell/language_hint`` for the next startup dialogs.
            renderer: Re-renders every section.
            settings: Stores the language in the user settings.
        """
        self._translator = translator
        self._hint = hint
        self._renderer = renderer
        self._settings = settings

    def toggle(self) -> ValidationResult:
        """Switch between English and French and store the choice (status bar button).

        Returns:
            The settings or translator failure, or success.
        """
        return self.change(_NEXT_LANGUAGE.get(self._translator.language, LanguageEnum.ENGLISH))

    def change(self, language: LanguageEnum) -> ValidationResult:
        """Store a language in the user settings, then show it.

        Args:
            language: Chosen language.

        Returns:
            The settings or translator failure, or success.
        """
        stored = self._settings.change_language(language)
        if stored.is_failure:
            return stored
        return self.follow(language)

    def follow(self, language: LanguageEnum) -> ValidationResult:
        """Show a language already stored (data file opened or reloaded): translator, hint, re-render.

        Args:
            language: Language of the user settings.

        Returns:
            The translator result.
        """
        result = self._translator.set_language(language)
        if result.is_failure:
            _logger.warning("UI language %s refused: %s", language.name, [code.name for code in result.error_codes])
            return result
        self._hint.write(language)
        _logger.info("UI language: %s", language.iso_code)
        self._renderer.request_all()
        return result
