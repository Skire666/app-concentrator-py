"""UI text catalogs."""

from typing import Protocol

from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.settings.language_enum import LanguageEnum


class TranslatorPort(Protocol):
    """Translates catalog keys into the current UI language."""

    @property
    def language(self) -> LanguageEnum:
        """Current UI language."""
        ...

    def set_language(self, language: LanguageEnum) -> ValidationResult:
        """Switch the UI language.

        Args:
            language: New language.

        Returns:
            Success, or a failure when the language is not available.
        """
        ...

    def has(self, key: str) -> bool:
        """Tell whether a key exists in the current or the fallback catalog (for optional texts).

        Args:
            key: Dotted catalog key.

        Returns:
            Whether ``tr(key)`` would return a catalog text rather than the key itself.
        """
        ...

    def tr(self, key: str, **params: object) -> str:
        """Translate a key.

        Args:
            key: Dotted catalog key such as ``timer.button.start``.
            **params: Values for the ``{name}`` placeholders.

        Returns:
            The text in the current language, falling back to English, then to the key itself.
        """
        ...

    def translations(self, key: str) -> tuple[str, ...]:
        """Return the text of a key in every loaded language (to recognize a name written in either).

        Args:
            key: Dotted catalog key.

        Returns:
            The texts, the current language first, without repeats; ``(key,)`` when no catalog has it.
        """
        ...

    def tr_plural(self, key: str, count: int, **params: object) -> str:
        """Translate a key whose text depends on a count (``<key>.one`` / ``<key>.other``).

        Args:
            key: Dotted catalog key without the plural suffix.
            count: Quantity choosing the form; also available as the ``{count}`` placeholder.
            **params: Values for the other placeholders.

        Returns:
            The text in the current language, with the same fallbacks as ``tr``.
        """
        ...
