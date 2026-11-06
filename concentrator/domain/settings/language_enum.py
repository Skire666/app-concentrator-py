"""UI language."""

from types import MappingProxyType
from typing import Final

from concentrator.domain.common.base_int_enum import BaseIntEnum


class LanguageEnum(BaseIntEnum):
    """Languages of the UI catalogs, each with its ISO 639-1 code."""

    UNKNOWN = -1
    UNSET = 0
    ENGLISH = 1
    FRENCH = 2

    @property
    def iso_code(self) -> str:
        """ISO 639-1 code (``en``, ``fr``), ``""`` for ``UNKNOWN`` and ``UNSET``."""
        return _ISO_CODES.get(self, "")

    @staticmethod
    def from_iso_code(code: str) -> LanguageEnum:
        """Find the language of an ISO 639-1 code.

        Args:
            code: Code such as ``en`` or ``FR`` (case and surrounding spaces are ignored).

        Returns:
            The language, or ``UNKNOWN`` when the code is not supported.
        """
        normalized = code.strip().lower()
        for language, iso_code in _ISO_CODES.items():
            if iso_code == normalized:
                return language
        return LanguageEnum.UNKNOWN


_ISO_CODES: Final = MappingProxyType({LanguageEnum.ENGLISH: "en", LanguageEnum.FRENCH: "fr"})
