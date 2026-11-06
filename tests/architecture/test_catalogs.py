"""Catalog parity and completeness (AGENTS.md section 9).

Convention checked here: a catalog key used in code is either the literal first argument of ``tr`` /
``tr_plural``, or the string value of a constant whose name ends with ``_KEY``.
"""

import ast
import json
import string
from pathlib import Path
from typing import Final, cast

import pytest

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from tests.architecture.source_tree import REPO_ROOT, parse, relative, source_files

CATALOG_DIR: Final = REPO_ROOT / "assets" / "i18n"
CATALOG_NAMES: Final = ("en.json", "fr.json")


def _load(name: str) -> dict[str, str]:
    return cast("dict[str, str]", json.loads((CATALOG_DIR / name).read_text(encoding="utf-8")))


def _placeholders(text: str) -> set[str]:
    return {field for _literal, field, _spec, _conversion in string.Formatter().parse(text) if field}


def _referenced_keys(path: Path) -> list[tuple[str, int, bool]]:
    """Return (key, line, is_plural) for every catalog key referenced in one module."""
    found: list[tuple[str, int, bool]] = []
    for node in ast.walk(parse(path)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.args:
            first = node.args[0]
            if (
                node.func.attr in {"tr", "tr_plural"}
                and isinstance(first, ast.Constant)
                and isinstance(first.value, str)
            ):
                found.append((first.value, node.lineno, node.func.attr == "tr_plural"))
        elif isinstance(node, ast.Assign | ast.AnnAssign):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names = [target.id for target in targets if isinstance(target, ast.Name)]
            value = node.value
            is_key_constant = any(name.endswith("_KEY") for name in names)
            if is_key_constant and isinstance(value, ast.Constant) and isinstance(value.value, str):
                found.append((value.value, node.lineno, False))
    return found


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
    assert f"error.{code.name.lower()}" in ENGLISH


def test_every_key_referenced_in_code_exists() -> None:
    missing: list[str] = []
    for path in source_files():
        for key, line, is_plural in _referenced_keys(path):
            expected = [f"{key}.one", f"{key}.other"] if is_plural else [key]
            missing.extend(f"{relative(path)}:{line} {item}" for item in expected if item not in ENGLISH)

    assert missing == []
