"""One copy of the data file per local day in ``paths.backup_dir`` (``AGENTS.md`` section 7.2 step 6)."""

import logging
import re
import shutil
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Final

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult

_logger = logging.getLogger(__name__)

BACKUP_EXTENSION: Final = ".toml"


def backup_name(stem: str, day: date) -> str:
    """Name of the daily copy.

    Args:
        stem: Stem of the data file (``concentrator``).
        day: Local date of the copy.

    Returns:
        ``<stem>-YYYY-MM-DD.toml``.
    """
    return f"{stem}-{day.isoformat()}{BACKUP_EXTENSION}"


def _date_of(name: str, stem: str) -> date | None:
    """Date of a daily copy, when ``name`` matches ``<stem>-YYYY-MM-DD.toml`` exactly.

    Args:
        name: File name found in the backup folder.
        stem: Stem of the data file.

    Returns:
        The date, ``None`` for any other name (such files are never deleted).
    """
    match = re.fullmatch(rf"{re.escape(stem)}-(\d{{4}})-(\d{{2}})-(\d{{2}}){re.escape(BACKUP_EXTENSION)}", name)
    if match is None:
        return None
    try:
        return date(int(match[1]), int(match[2]), int(match[3]))
    except ValueError:
        return None


class DailyBackup:
    """Copies the data file once per day and deletes the copies older than the retention."""

    def __init__(
        self,
        *,
        backup_dir: Path,
        enabled: bool,
        retention_days: int,
        copy: Callable[[Path, Path], object] = shutil.copy2,
    ) -> None:
        """Create the service.

        Args:
            backup_dir: ``paths.backup_dir``.
            enabled: ``storage.daily_backup_enabled``.
            retention_days: ``storage.daily_backup_retention_days``: today and the previous days kept.
            copy: File copy function (replaced in tests).
        """
        self._backup_dir = backup_dir
        self._enabled = enabled
        self._retention_days = retention_days
        self._copy = copy

    def after_save(self, data_file: Path, today: date) -> ValidationResult:
        """Make today's copy if it does not exist yet, then apply the retention (writer thread).

        Args:
            data_file: Data file just saved.
            today: Local date.

        Returns:
            Success, or a ``STORAGE_BACKUP_FAILED`` warning.
        """
        if not self._enabled:
            return ValidationResult.success()
        target = self._backup_dir / backup_name(data_file.stem, today)
        if not target.exists():
            try:
                self._backup_dir.mkdir(parents=True, exist_ok=True)
                self._copy(data_file, target)
            except OSError as error:
                _logger.warning("Cannot make the daily backup %s: %s", target, error)
                return ValidationResult.warning(ErrorCodeEnum.STORAGE_BACKUP_FAILED)
            _logger.info("Daily backup written to %s", target)
        return self._prune(data_file.stem, today)

    def _prune(self, stem: str, today: date) -> ValidationResult:
        """Delete this data file's daily copies older than the retention; other files stay.

        Args:
            stem: Stem of the data file.
            today: Local date.

        Returns:
            Success, or a ``STORAGE_BACKUP_FAILED`` warning when a copy cannot be deleted.
        """
        try:
            entries = [entry for entry in self._backup_dir.iterdir() if entry.is_file()]
        except OSError as error:
            _logger.warning("Cannot list the backup folder %s: %s", self._backup_dir, error)
            return ValidationResult.warning(ErrorCodeEnum.STORAGE_BACKUP_FAILED)
        result = ValidationResult.success()
        for entry in entries:
            day = _date_of(entry.name, stem)
            if day is None or (today - day).days < self._retention_days:
                continue
            try:
                entry.unlink()
            except OSError as error:
                _logger.warning("Cannot delete the old backup %s: %s", entry, error)
                result = ValidationResult.warning(ErrorCodeEnum.STORAGE_BACKUP_FAILED)
            else:
                _logger.info("Old daily backup deleted: %s", entry)
        return result
