"""Helpers walking the ``concentrator`` source tree for architecture tests."""

import ast
import importlib
import pkgutil
from pathlib import Path
from types import ModuleType
from typing import Final

REPO_ROOT: Final = Path(__file__).resolve().parents[2]
PACKAGE_ROOT: Final = REPO_ROOT / "concentrator"
PACKAGE_NAME: Final = "concentrator"


def source_files() -> tuple[Path, ...]:
    """Every Python file of the package, sorted."""
    return tuple(sorted(path for path in PACKAGE_ROOT.rglob("*.py") if "__pycache__" not in path.parts))


def parse(path: Path) -> ast.Module:
    """Parse one source file."""
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def import_all_modules() -> tuple[ModuleType, ...]:
    """Import every module of the package so that subclass registries are complete."""
    names = [info.name for info in pkgutil.walk_packages([str(PACKAGE_ROOT)], prefix=f"{PACKAGE_NAME}.")]
    return tuple(importlib.import_module(name) for name in names)


def relative(path: Path) -> str:
    """Repository-relative POSIX path, for readable assertion messages."""
    return path.relative_to(REPO_ROOT).as_posix()
