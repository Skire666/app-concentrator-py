"""TOML text <-> plain Python values. The only module that imports ``tomllib`` (ADR-035).

Reading uses the standard library ``tomllib`` (TOML 1.0). Writing uses the emitter below, because the
standard library has no TOML writer and the file must use literal strings: ``'...'`` by default,
``'''...'''`` when the value contains ``'``, ``"..."`` with escapes only when it contains ``'''`` or a
control character other than tab.
"""

import logging
import re
import tomllib
from collections.abc import Mapping, Sequence
from datetime import date, time
from typing import Final, cast

from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult

_logger = logging.getLogger(__name__)

INDENT: Final = "  "
LINE_END: Final = "\n"
_BARE_KEY: Final = re.compile(r"[A-Za-z0-9_-]+")
_NOT_LITERAL: Final = re.compile(r"[\x00-\x08\x0a-\x1f\x7f]|'''")
_TO_ESCAPE: Final = re.compile(r'[\\"\x00-\x08\x0a-\x1f\x7f]')
_ESCAPES: Final = {"\\": "\\\\", '"': '\\"', "\b": "\\b", "\n": "\\n", "\f": "\\f", "\r": "\\r"}
_QUOTE: Final = "'"
_TRIPLE_QUOTE: Final = "'''"


def _plain(value: object) -> object:
    """Turn the native TOML dates and times of a parsed document into ISO text (ADR-035).

    Args:
        value: Parsed value.

    Returns:
        The same value with JSON-compatible leaves.
    """
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in cast("dict[str, object]", value).items()}
    if isinstance(value, list):
        return [_plain(item) for item in cast("list[object]", value)]
    if isinstance(value, date | time):
        return value.isoformat()
    return value


def _escape(match: re.Match[str]) -> str:
    """Escape one character of a basic string.

    Args:
        match: The character.

    Returns:
        Its TOML escape sequence.
    """
    character = match[0]
    return _ESCAPES.get(character, f"\\u{ord(character):04X}")


def _string(text: str) -> str:
    """Quote a string (literal whenever TOML allows it).

    Args:
        text: Value.

    Returns:
        ``'...'``, ``'''...'''`` or ``"..."``.
    """
    if _NOT_LITERAL.search(text) is not None:
        return _basic(text)
    if _QUOTE in text:
        return _TRIPLE_QUOTE + text + _TRIPLE_QUOTE
    return _QUOTE + text + _QUOTE


def _basic(text: str) -> str:
    """Write a basic string ``"..."`` with escapes.

    Args:
        text: Value.

    Returns:
        The quoted text.
    """
    return '"' + _TO_ESCAPE.sub(_escape, text) + '"'


def _key(key: str) -> str:
    """Write a key: bare when it is a plain word, else ``'...'``, else ``"..."``.

    TOML keys cannot be multi-line strings, so a key with an apostrophe is a basic string.

    Args:
        key: Key.

    Returns:
        The TOML key.
    """
    if _BARE_KEY.fullmatch(key):
        return key
    if _QUOTE in key or _NOT_LITERAL.search(key) is not None:
        return _basic(key)
    return _QUOTE + key + _QUOTE


def _scalar(value: object) -> str:
    """Write a string, a boolean or a number.

    Args:
        value: Value.

    Returns:
        The TOML value.

    Raises:
        TypeError: For any other type (a programming error: the DTOs only hold these types).
    """
    if isinstance(value, str):
        return _string(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return repr(value)
    message = f"Cannot write a {type(value).__name__} value as TOML"
    raise TypeError(message)


def _array(value: object) -> Sequence[object] | None:
    """The elements of an array value.

    Args:
        value: Value.

    Returns:
        The elements of a list or tuple, ``None`` for any other value.
    """
    if isinstance(value, list | tuple):
        return cast("Sequence[object]", value)
    return None


def _inline(value: object) -> str:
    """Write a value on one line (inside an inline table or as an array element).

    Args:
        value: Value.

    Returns:
        The TOML value.
    """
    if isinstance(value, Mapping):
        entries = [f"{_key(key)} = {_inline(item)}" for key, item in _present(cast("Mapping[str, object]", value))]
        return "{ " + ", ".join(entries) + " }" if entries else "{}"
    elements = _array(value)
    if elements is not None:
        return "[" + ", ".join(_inline(item) for item in elements) + "]"
    return _scalar(value)


def _value(value: object) -> str:
    """Write the value of a table entry: non-empty arrays get one element per line.

    Args:
        value: Value.

    Returns:
        The TOML value.
    """
    elements = _array(value)
    if elements:
        items = "".join(f"{INDENT}{_inline(item)},{LINE_END}" for item in elements)
        return "[" + LINE_END + items + "]"
    return _inline(value)


def _present(table: Mapping[str, object]) -> list[tuple[str, object]]:
    """Entries of a table without the unset values (TOML has no ``null``).

    Args:
        table: Table.

    Returns:
        The ``(key, value)`` pairs to write, in order.
    """
    return [(key, value) for key, value in table.items() if value is not None]


def _is_table(value: object) -> bool:
    """Whether a root value is written as ``[section]`` or ``[[section]]``.

    Args:
        value: Root value.

    Returns:
        ``True`` for an object or a non-empty array of objects.
    """
    if isinstance(value, Mapping):
        return True
    elements = _array(value)
    return bool(elements) and all(isinstance(item, Mapping) for item in elements or ())


def _entries(table: Mapping[str, object]) -> list[str]:
    """Lines ``key = value`` of a table.

    Args:
        table: Table.

    Returns:
        The lines.
    """
    return [f"{_key(key)} = {_value(value)}" for key, value in _present(table)]


def _sections(key: str, value: object) -> list[str]:
    """Lines of one root ``[section]`` or of every ``[[section]]`` element, each after a blank line.

    Args:
        key: Root key.
        value: An object or a non-empty array of objects.

    Returns:
        The lines.
    """
    if isinstance(value, Mapping):
        return ["", f"[{_key(key)}]", *_entries(cast("Mapping[str, object]", value))]
    lines: list[str] = []
    for item in cast("Sequence[Mapping[str, object]]", value):
        lines.extend(["", f"[[{_key(key)}]]", *_entries(item)])
    return lines


class TomlCodec:
    """Parses and writes the data file format of ``AGENTS.md`` section 7.1."""

    @staticmethod
    def decode(text: str) -> DataResult[dict[str, object]]:
        """Parse TOML text; duplicate keys are syntax errors in TOML.

        Args:
            text: Whole file content, without BOM.

        Returns:
            The parsed document (native dates and times as ISO text), or ``STORAGE_SYNTAX_INVALID``
            with ``line`` and ``column``.
        """
        try:
            document: dict[str, object] = tomllib.loads(text)
        except tomllib.TOMLDecodeError as error:
            _logger.warning("TOML syntax error at line %d, column %d", error.lineno, error.colno)
            failure = ValidationResult.failure(
                ErrorCodeEnum.STORAGE_SYNTAX_INVALID, line=error.lineno, column=error.colno
            )
            return DataResult.fail(failure)
        return DataResult.ok({key: _plain(item) for key, item in document.items()})

    @staticmethod
    def encode(document: Mapping[str, object]) -> str:
        """Write a document: root scalar keys first, then the sections in order; ``None`` values omitted.

        Args:
            document: JSON-compatible document (dicts keep their key order).

        Returns:
            The TOML text, LF line endings, without trailing newline.
        """
        present = _present(document)
        lines = [f"{_key(key)} = {_value(value)}" for key, value in present if not _is_table(value)]
        for key, value in present:
            if _is_table(value):
                lines.extend(_sections(key, value))
        return LINE_END.join(lines).lstrip(LINE_END)
