"""Delete build artefacts and caches.

Usage: ``uv run python scripts/clean.py [--all] [--dry-run]``. ``--all`` also deletes ``.venv/``; run
it with a Python interpreter from outside ``.venv`` (Windows locks the running interpreter).
"""

import argparse
import os
import shutil
import sys
from pathlib import Path
from typing import Final

REPO_ROOT: Final = Path(__file__).resolve().parents[1]
DIRECTORIES: Final = ("build", "dist", ".pytest_cache", ".ruff_cache", "htmlcov")
FILE_PATTERNS: Final = (".coverage", ".coverage.*", "coverage.json")
VENV: Final = ".venv"
SKIPPED_WALK_DIRECTORIES: Final = frozenset({VENV, ".git"})


def pycache_directories(root: Path) -> list[Path]:
    """Find every ``__pycache__`` directory, without descending into ``.venv`` or ``.git``.

    Args:
        root: Directory to search.

    Returns:
        The directories found.
    """
    found: list[Path] = []
    for current, directories, _files in os.walk(root):
        directories[:] = [name for name in directories if name not in SKIPPED_WALK_DIRECTORIES]
        if "__pycache__" in directories:
            found.append(Path(current) / "__pycache__")
            directories.remove("__pycache__")
    return found


def targets(root: Path, *, include_venv: bool) -> list[Path]:
    """List the existing paths to delete.

    Args:
        root: Repository root.
        include_venv: Whether ``.venv`` is deleted too.

    Returns:
        Existing paths, directories first.
    """
    names = [*DIRECTORIES, VENV] if include_venv else list(DIRECTORIES)
    paths = [root / name for name in names]
    paths.extend(path for pattern in FILE_PATTERNS for path in root.glob(pattern))
    paths.extend(pycache_directories(root))
    return [path for path in paths if path.exists()]


def delete(path: Path) -> bool:
    """Delete one file or directory tree.

    Args:
        path: Path to delete.

    Returns:
        True on success; failures are printed.
    """
    try:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    except OSError as error:
        print(f"could not delete {path}: {error}")
        return False
    return True


def main() -> int:
    """Parse the options and delete the targets.

    Returns:
        0 when everything was deleted, 1 otherwise.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="also delete .venv")
    parser.add_argument("--dry-run", action="store_true", help="list the paths without deleting them")
    options = parser.parse_args()
    paths = targets(REPO_ROOT, include_venv=options.all)
    for path in paths:
        print(("would delete " if options.dry_run else "deleting ") + str(path.relative_to(REPO_ROOT)))
    if options.dry_run:
        return 0
    deleted = [delete(path) for path in paths]  # no short-circuit: try every path
    return 0 if all(deleted) else 1


if __name__ == "__main__":
    sys.exit(main())
