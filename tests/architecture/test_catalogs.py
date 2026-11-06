"""Catalog parity and completeness (AGENTS.md section 9).

Keys used in code are checked in two ways: every plain string literal of the presentation and ui
layers (the only ones that translate) that looks like a key of a catalog family (``app.``, ``shell.``,
``error.`` ...) must exist, and keys built from enums (``error.<code>``, ``action.<action>``) are
checked member by member. Other layers use dotted ini field paths such as ``app.name``.
"""

import ast
import json
import re
import string
from pathlib import Path
from typing import Final, cast

import pytest

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.ui_texts import action_label_key, error_message_key
from tests.architecture.source_tree import REPO_ROOT, parse, relative, source_files

CATALOG_DIR: Final = REPO_ROOT / "assets" / "i18n"
CATALOG_NAMES: Final = ("en.json", "fr.json")
TRANSLATING_LAYERS: Final = ("presentation", "ui")


def _load(name: str) -> dict[str, str]:
    return cast("dict[str, str]", json.loads((CATALOG_DIR / name).read_text(encoding="utf-8")))


def _placeholders(text: str) -> set[str]:
    return {field for _literal, field, _spec, _conversion in string.Formatter().parse(text) if field}


def _formatted_parts(tree: ast.Module) -> set[int]:
    """Ids of the constants that are fragments of f-strings (dynamic keys, checked elsewhere)."""
    return {id(value) for node in ast.walk(tree) if isinstance(node, ast.JoinedStr) for value in node.values}


def _key_literals(path: Path, key_pattern: re.Pattern[str]) -> list[tuple[str, int]]:
    """Return (literal, line) for every plain string literal that looks like a catalog key."""
    tree = parse(path)
    fragments = _formatted_parts(tree)
    return [
        (node.value, node.lineno)
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in fragments
        and key_pattern.fullmatch(node.value)
    ]


ENGLISH: Final = _load("en.json")
FRENCH: Final = _load("fr.json")


def test_catalogs_have_identical_key_sets() -> None:
    assert sorted(set(ENGLISH) ^ set(FRENCH)) == []


@pytest.mark.parametrize("key", sorted(ENGLISH))
def test_catalogs_have_identical_placeholders(key: str) -> None:
    assert _placeholders(ENGLISH[key]) == _placeholders(FRENCH.get(key, ENGLISH[key]))


@pytest.mark.parametrize("name", CATALOG_NAMES)
def test_catalog_texts_are_not_empty(name: str) -> None:
    assert [key for key, text in _load(name).items() if not text.strip()] == []


@pytest.mark.parametrize("code", list(ErrorCodeEnum), ids=lambda code: code.name)
def test_every_error_code_has_a_message(code: ErrorCodeEnum) -> None:
    assert error_message_key(code) in ENGLISH


@pytest.mark.parametrize("action", [action for action in ActionIdEnum if action.is_set], ids=lambda a: a.name)
def test_every_action_has_a_label(action: ActionIdEnum) -> None:
    assert action_label_key(action) in ENGLISH


def test_every_key_literal_in_code_exists() -> None:
    families = "|".join(sorted({re.escape(key.split(".", 1)[0]) for key in ENGLISH}))
    key_pattern = re.compile(rf"(?:{families})\.[a-z0-9_]+(?:\.[a-z0-9_]+)*")
    missing = [
        f"{relative(path)}:{line} {literal}"
        for path in source_files()
        if path.relative_to(REPO_ROOT / "concentrator").parts[0] in TRANSLATING_LAYERS
        for literal, line in _key_literals(path, key_pattern)
        if literal not in ENGLISH
    ]

    assert missing == []


def test_key_literal_scan_sees_the_shell_texts() -> None:
    families = "|".join(sorted({re.escape(key.split(".", 1)[0]) for key in ENGLISH}))
    key_pattern = re.compile(rf"(?:{families})\.[a-z0-9_]+(?:\.[a-z0-9_]+)*")
    presenter = REPO_ROOT / "concentrator" / "presentation" / "shell" / "shell_presenter.py"

    literals = {literal for literal, _line in _key_literals(presenter, key_pattern)}

    assert {"app.title", "shell.language.button.fr", "placeholder.journal"} <= literals
