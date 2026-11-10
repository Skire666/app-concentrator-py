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
PLURAL_FORMS: Final = ("one", "other")


def _exists(literal: str) -> bool:
    """A key, or the base of a plural key (``tr_plural`` reads ``<base>.one`` and ``<base>.other``)."""
    return literal in ENGLISH or all(f"{literal}.{form}" in ENGLISH for form in PLURAL_FORMS)


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
        if not _exists(literal)
    ]

    assert missing == []


TRANSLATE_METHODS: Final = frozenset({"tr", "tr_plural"})


def _call_name(func: ast.expr) -> str:
    """Name of a called function: ``x.tr(...)`` and a local alias ``tr(...)`` both give ``tr``."""
    if isinstance(func, ast.Attribute):
        return func.attr
    return func.id if isinstance(func, ast.Name) else ""


def _translated_literals(path: Path) -> list[tuple[str, int]]:
    """Return (key, line) for every literal first argument of a ``tr`` or ``tr_plural`` call."""
    return [
        (node.args[0].value, node.lineno)
        for node in ast.walk(parse(path))
        if isinstance(node, ast.Call)
        and _call_name(node.func) in TRANSLATE_METHODS
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    ]


def test_every_literal_translated_in_any_layer_exists() -> None:
    missing = [
        f"{relative(path)}:{line} {key}"
        for path in source_files()
        for key, line in _translated_literals(path)
        if not _exists(key)
    ]

    assert missing == []


def test_translated_literal_scan_sees_the_tr_calls() -> None:
    presenter = REPO_ROOT / "concentrator" / "presentation" / "timer" / "timer_presenter.py"

    assert {"timer.caption.paused", "timer.caption.ringing"} <= {key for key, _line in _translated_literals(presenter)}


def test_key_literal_scan_sees_the_shell_texts() -> None:
    families = "|".join(sorted({re.escape(key.split(".", 1)[0]) for key in ENGLISH}))
    key_pattern = re.compile(rf"(?:{families})\.[a-z0-9_]+(?:\.[a-z0-9_]+)*")
    shell = REPO_ROOT / "concentrator" / "presentation" / "shell"
    presenters = (shell / "shell_presenter.py", shell / "status_bar_presenter.py")

    literals = {literal for presenter in presenters for literal, _line in _key_literals(presenter, key_pattern)}

    assert {"app.title", "shell.language.button.fr", "placeholder.settings"} <= literals


@pytest.mark.parametrize("sound", sorted((REPO_ROOT / "assets" / "sounds").glob("*.mp3")), ids=lambda path: path.stem)
def test_every_shipped_sound_has_a_label(sound: Path) -> None:
    assert f"sound.builtin.{sound.stem}" in ENGLISH


def test_plural_base_needs_both_forms() -> None:
    assert _exists("storage.issue.more")
    assert not _exists("storage.issue")
