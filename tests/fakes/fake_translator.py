"""Translator returning recognizable texts: ``<iso>:<key>`` plus the parameters."""

from typing import override

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.settings.language_enum import LanguageEnum


class FakeTranslator(TranslatorPort):
    """Every key exists except those listed in ``missing``."""

    def __init__(self, language: LanguageEnum = LanguageEnum.ENGLISH, missing: frozenset[str] = frozenset()) -> None:
        self._language = language
        self.missing = missing
        self.refused: frozenset[LanguageEnum] = frozenset()

    @property
    @override
    def language(self) -> LanguageEnum:
        return self._language

    @override
    def set_language(self, language: LanguageEnum) -> ValidationResult:
        if not language.is_set or language in self.refused:
            return ValidationResult.failure(ErrorCodeEnum.ENUM_VALUE_UNKNOWN, field="language")
        self._language = language
        return ValidationResult.success()

    @override
    def has(self, key: str) -> bool:
        return key not in self.missing

    @override
    def tr(self, key: str, **params: object) -> str:
        text = f"{self._language.iso_code}:{key}"
        if params:
            text += "(" + ",".join(f"{name}={value}" for name, value in params.items()) + ")"
        return text

    @override
    def translations(self, key: str) -> tuple[str, ...]:
        others = (
            language for language in (LanguageEnum.ENGLISH, LanguageEnum.FRENCH) if language is not self._language
        )
        return tuple(f"{language.iso_code}:{key}" for language in (self._language, *others))

    @override
    def tr_plural(self, key: str, count: int, **params: object) -> str:
        form = "one" if count == 1 else "other"
        return self.tr(f"{key}.{form}", count=count, **params)
