"""Flat JSON catalogs (``assets/i18n/<iso>.json``) and the translator built on them."""

import json
import logging
from collections import UserDict
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Final, cast, override

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.settings.language_enum import LanguageEnum

_logger = logging.getLogger(__name__)

type Catalog = Mapping[str, str]
type CatalogSet = Mapping[LanguageEnum, Catalog]

CATALOG_SUFFIX: Final = ".json"
PLURAL_ONE: Final = "one"
PLURAL_OTHER: Final = "other"
COUNT_PARAM: Final = "count"

_PLURAL_RULES: Final[Mapping[LanguageEnum, Callable[[int], bool]]] = MappingProxyType(
    {LanguageEnum.ENGLISH: lambda count: count == 1, LanguageEnum.FRENCH: lambda count: count <= 1}
)


class _KeepMissing(UserDict[str, str]):
    """Format mapping leaving unknown ``{placeholders}`` visible instead of raising."""

    def __missing__(self, key: str) -> str:
        """Return the placeholder itself (``UserDict`` calls this hook for absent keys).

        Args:
            key: Placeholder name.

        Returns:
            ``{key}``.
        """
        return "{" + key + "}"


def _read_json(path: Path) -> DataResult[object]:
    """Read and decode a JSON file.

    Args:
        path: File to read.

    Returns:
        The decoded content, or ``CATALOG_FILE_NOT_FOUND`` / ``CATALOG_SYNTAX_INVALID``.
    """
    try:
        content: object = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        _logger.warning("Catalog not found: %s", path)
        return DataResult.fail(ValidationResult.failure(ErrorCodeEnum.CATALOG_FILE_NOT_FOUND, path=path.name))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        _logger.warning("Catalog unreadable %s: %s", path, error)
        return DataResult.fail(ValidationResult.failure(ErrorCodeEnum.CATALOG_SYNTAX_INVALID, path=path.name))
    return DataResult.ok(content)


def _to_catalog(content: object, path: Path) -> DataResult[Catalog]:
    """Check that decoded JSON is a flat object of texts.

    Args:
        content: Decoded JSON.
        path: Source file, for the log and the issue.

    Returns:
        The catalog, or ``CATALOG_SYNTAX_INVALID`` (``field`` = first key whose value is not text).
    """
    if not isinstance(content, dict):
        _logger.warning("Catalog %s is not a JSON object", path)
        return DataResult.fail(ValidationResult.failure(ErrorCodeEnum.CATALOG_SYNTAX_INVALID, path=path.name))
    entries = cast("dict[object, object]", content)
    invalid = [str(key) for key, value in entries.items() if not isinstance(value, str)]
    if invalid:
        _logger.warning("Catalog %s has non-text values for %s", path, invalid)
        failure = ValidationResult.failure(ErrorCodeEnum.CATALOG_SYNTAX_INVALID, field=invalid[0], path=path.name)
        return DataResult.fail(failure)
    return DataResult.ok(MappingProxyType({str(key): str(value) for key, value in entries.items()}))


def load_catalog(path: Path) -> DataResult[Catalog]:
    """Read one catalog: a flat JSON object of string keys and string values.

    Args:
        path: Catalog file.

    Returns:
        The catalog, or ``CATALOG_FILE_NOT_FOUND`` / ``CATALOG_SYNTAX_INVALID``.
    """
    content = _read_json(path)
    if not content.is_success:
        return DataResult.fail(content.validation)
    return _to_catalog(content.data, path)


def load_catalogs(
    directory: Path, languages: Iterable[LanguageEnum], reference: LanguageEnum
) -> DataResult[CatalogSet]:
    """Read the catalog of every language and compare its keys with the reference catalog.

    Args:
        directory: Folder of the catalogs.
        languages: Languages to load (``<iso_code>.json`` each).
        reference: Language whose keys every other catalog should have (the fallback language).

    Returns:
        Every catalog, with a ``CATALOG_KEY_MISSING`` warning per missing key; a failure when a file
        cannot be loaded.
    """
    results = {language: load_catalog(directory / f"{language.iso_code}{CATALOG_SUFFIX}") for language in languages}
    failures = [result.validation for result in results.values() if result.data is None]
    if failures:
        return DataResult.fail(failures[0].merge(*failures[1:]))
    catalogs = {language: result.value_or({}) for language, result in results.items()}
    reference_keys = set(catalogs.get(reference, {}))
    warnings = [
        ValidationResult.warning(ErrorCodeEnum.CATALOG_KEY_MISSING, field=key, language=language.iso_code)
        for language, catalog in catalogs.items()
        for key in sorted(reference_keys - set(catalog))
    ]
    for warning in warnings:
        _logger.warning("Catalog key %s missing in %s", warning.issues[0].field, warning.issues[0].params)
    return DataResult.ok(MappingProxyType(catalogs), ValidationResult.success().merge(*warnings))


class JsonCatalogTranslator(TranslatorPort):
    """Looks keys up in the current language, then in the fallback language, then returns the key.

    A missing key is logged once per language at WARNING level.
    """

    def __init__(self, catalogs: CatalogSet, *, language: LanguageEnum, fallback_language: LanguageEnum) -> None:
        """Create a translator.

        Args:
            catalogs: Loaded catalogs; may be empty (every text is then its key).
            language: Initial UI language.
            fallback_language: Language used for keys missing from the current catalog.
        """
        self._catalogs = catalogs
        self._language = language
        self._fallback_language = fallback_language
        self._warned: set[tuple[LanguageEnum, str]] = set()

    @property
    @override
    def language(self) -> LanguageEnum:
        return self._language

    @override
    def set_language(self, language: LanguageEnum) -> ValidationResult:
        if language is LanguageEnum.UNSET:
            return ValidationResult.failure(ErrorCodeEnum.ENUM_VALUE_UNSET, field="language")
        if not language.is_set:
            return ValidationResult.failure(ErrorCodeEnum.ENUM_VALUE_UNKNOWN, field="language")
        self._language = language
        return ValidationResult.success()

    @override
    def has(self, key: str) -> bool:
        return any(key in self._catalogs.get(language, {}) for language in (self._language, self._fallback_language))

    @override
    def tr(self, key: str, **params: object) -> str:
        text = self._lookup(key)
        if not params:
            return text
        try:
            return text.format_map(_KeepMissing({name: str(value) for name, value in params.items()}))
        except (ValueError, IndexError, AttributeError) as error:
            self._warn_once(key, f"cannot format: {error}")
            return text

    @override
    def tr_plural(self, key: str, count: int, **params: object) -> str:
        is_one = _PLURAL_RULES.get(self._language, _PLURAL_RULES[LanguageEnum.ENGLISH])(count)
        form = PLURAL_ONE if is_one else PLURAL_OTHER
        return self.tr(f"{key}.{form}", **{COUNT_PARAM: count, **params})

    def _lookup(self, key: str) -> str:
        """Find the text of a key through the fallback chain.

        Args:
            key: Catalog key.

        Returns:
            The text, or the key itself.
        """
        text = self._catalogs.get(self._language, {}).get(key)
        if text is not None:
            return text
        self._warn_once(key, "missing")
        return self._catalogs.get(self._fallback_language, {}).get(key, key)

    def _warn_once(self, key: str, problem: str) -> None:
        """Log a catalog problem the first time it is met for the current language.

        Args:
            key: Catalog key.
            problem: Short description.
        """
        if (self._language, key) in self._warned:
            return
        self._warned.add((self._language, key))
        _logger.warning(
            "Catalog key %r %s in language %s", key, problem, self._language.iso_code or self._language.name
        )
