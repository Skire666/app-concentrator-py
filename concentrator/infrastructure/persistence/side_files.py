"""Names of the files kept next to the data file (``AGENTS.md`` section 7.2, ADR-027)."""

from datetime import datetime
from pathlib import Path
from typing import Final

TEMPORARY_SUFFIX: Final = ".tmp"
BACKUP_SUFFIX: Final = ".bak"
CORRUPT_SUFFIX: Final = ".corrupt-"
DISCARDED_SUFFIX: Final = ".tmp.discarded-"
BACKUP_DISCARDED_SUFFIX: Final = ".bak.discarded-"
STAMP_FORMAT: Final = "%Y%m%d-%H%M%S"


def _with_suffix(path: Path, suffix: str) -> Path:
    """Append a suffix to the full file name (``concentrator.toml`` -> ``concentrator.toml.tmp``).

    Args:
        path: Data file path.
        suffix: Text to append.

    Returns:
        The side file path, in the same folder.
    """
    return path.with_name(path.name + suffix)


def temporary_path(path: Path) -> Path:
    """``<file>.tmp``: written and verified before it replaces the data file.

    Args:
        path: Data file path.

    Returns:
        The temporary file path.
    """
    return _with_suffix(path, TEMPORARY_SUFFIX)


def backup_path(path: Path) -> Path:
    """``<file>.bak``: the previous version, copied before each replace.

    Args:
        path: Data file path.

    Returns:
        The backup file path.
    """
    return _with_suffix(path, BACKUP_SUFFIX)


def corrupt_path(path: Path, local_now: datetime) -> Path:
    """``<file>.corrupt-YYYYMMDD-HHMMSS``: a damaged data file put aside.

    Args:
        path: Data file path.
        local_now: Local time of the rename.

    Returns:
        The quarantine path.
    """
    return _with_suffix(path, CORRUPT_SUFFIX + local_now.strftime(STAMP_FORMAT))


def discarded_path(path: Path, local_now: datetime) -> Path:
    """``<file>.tmp.discarded-YYYYMMDD-HHMMSS``: a stale temporary file the user chose not to restore.

    Args:
        path: Data file path.
        local_now: Local time of the rename.

    Returns:
        The new name of the temporary file.
    """
    return _with_suffix(path, DISCARDED_SUFFIX + local_now.strftime(STAMP_FORMAT))


def discarded_backup_path(path: Path, local_now: datetime) -> Path:
    """``<file>.bak.discarded-YYYYMMDD-HHMMSS``: a backup put aside before a new data file is created.

    Args:
        path: Data file path.
        local_now: Local time of the rename.

    Returns:
        The new name of the backup file.
    """
    return _with_suffix(path, BACKUP_DISCARDED_SUFFIX + local_now.strftime(STAMP_FORMAT))
