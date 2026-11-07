"""Atomic replacement of the data file (``AGENTS.md`` section 7.2 steps 1-5, ADR-005, ADR-033).

The main file always exists and is either the old or the new complete version.
"""

import errno
import hashlib
import logging
import os
import shutil
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.infrastructure.persistence.side_files import backup_path, temporary_path

_logger = logging.getLogger(__name__)

MS_PER_SECOND: Final = 1000


def _read_bytes(path: Path) -> bytes:
    """Read a whole file.

    Args:
        path: File path.

    Returns:
        Its bytes.
    """
    return path.read_bytes()


@dataclass(frozen=True, slots=True)
class FileSystem:
    """File operations used by the writer; replaced in tests to simulate failures."""

    replace: Callable[[Path, Path], None] = os.replace
    copy: Callable[[Path, Path], object] = shutil.copy2
    read_bytes: Callable[[Path], bytes] = _read_bytes
    sleep: Callable[[float], None] = time.sleep


def _code_for(error: OSError, default: ErrorCodeEnum) -> ErrorCodeEnum:
    """Choose the code of a file system error.

    Args:
        error: The error.
        default: Code when the disk is not full.

    Returns:
        ``STORAGE_DISK_FULL`` for ``ENOSPC``, else ``default``.
    """
    return ErrorCodeEnum.STORAGE_DISK_FULL if error.errno == errno.ENOSPC else default


class AtomicFileWriter:
    """Writes the temporary file, verifies it, checks for external changes, keeps ``.bak``, replaces."""

    def __init__(
        self, *, replace_retry_count: int, replace_retry_delay_ms: int, file_system: FileSystem | None = None
    ) -> None:
        """Create the writer.

        Args:
            replace_retry_count: ``storage.replace_retry_count``.
            replace_retry_delay_ms: ``storage.replace_retry_delay_ms``.
            file_system: File operations (real ones by default).
        """
        self._retry_count = replace_retry_count
        self._retry_delay_s = replace_retry_delay_ms / MS_PER_SECOND
        self._fs = file_system or FileSystem()

    def write(
        self, target: Path, content: bytes, before_replace: Callable[[], ValidationResult] | None = None
    ) -> ValidationResult:
        """Replace ``target`` with ``content`` atomically.

        Args:
            target: Data file path.
            content: Complete new content.
            before_replace: Check run after the temporary file is verified and before anything else
                changes (the external modification check); a failure deletes the temporary file.

        Returns:
            Success (possibly with a ``STORAGE_BACKUP_FAILED`` warning), or ``STORAGE_DIRECTORY_NOT_WRITABLE``,
            ``STORAGE_WRITE_FAILED``, ``STORAGE_DISK_FULL``, ``STORAGE_VERIFY_FAILED``, the check's failure,
            or ``STORAGE_REPLACE_FAILED`` (the verified temporary file is then left in place).
        """
        temporary = temporary_path(target)
        prepared = self._write_temporary(temporary, content)
        if prepared.is_success:
            prepared = self._verify(temporary, content)
        if prepared.is_success and before_replace is not None:
            prepared = before_replace()
        if prepared.is_failure:
            self._discard(temporary)
            return prepared
        return self._copy_backup(target).merge(self._replace(temporary, target))

    @staticmethod
    def _write_temporary(temporary: Path, content: bytes) -> ValidationResult:
        """Step 1: write, flush and ``fsync`` the temporary file (creating its folder).

        Args:
            temporary: ``<file>.tmp``.
            content: Bytes to write.

        Returns:
            Success or the coded failure.
        """
        try:
            temporary.parent.mkdir(parents=True, exist_ok=True)
            stream = temporary.open("wb")
        except OSError as error:
            _logger.warning("Cannot create %s: %s", temporary, error)
            return ValidationResult.failure(_code_for(error, ErrorCodeEnum.STORAGE_DIRECTORY_NOT_WRITABLE))
        try:
            with stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError as error:
            _logger.warning("Cannot write %s: %s", temporary, error)
            return ValidationResult.failure(_code_for(error, ErrorCodeEnum.STORAGE_WRITE_FAILED))
        return ValidationResult.success()

    def _verify(self, temporary: Path, content: bytes) -> ValidationResult:
        """Step 2: re-read the temporary file and compare its SHA-256 with the bytes written.

        Args:
            temporary: ``<file>.tmp``.
            content: Bytes written.

        Returns:
            Success or ``STORAGE_VERIFY_FAILED``.
        """
        try:
            written = self._fs.read_bytes(temporary)
        except OSError as error:
            _logger.warning("Cannot re-read %s: %s", temporary, error)
            return ValidationResult.failure(ErrorCodeEnum.STORAGE_VERIFY_FAILED)
        if hashlib.sha256(written).digest() != hashlib.sha256(content).digest():
            _logger.warning("Content of %s differs from the bytes written", temporary)
            return ValidationResult.failure(ErrorCodeEnum.STORAGE_VERIFY_FAILED)
        return ValidationResult.success()

    def _copy_backup(self, target: Path) -> ValidationResult:
        """Step 4: copy the current file to ``<file>.bak``.

        Args:
            target: Data file path.

        Returns:
            Success, or a ``STORAGE_BACKUP_FAILED`` warning (the save goes on).
        """
        if not target.is_file():
            return ValidationResult.success()
        try:
            self._fs.copy(target, backup_path(target))
        except OSError as error:
            _logger.warning("Cannot copy %s to its backup: %s", target, error)
            return ValidationResult.warning(ErrorCodeEnum.STORAGE_BACKUP_FAILED)
        return ValidationResult.success()

    def _replace(self, temporary: Path, target: Path) -> ValidationResult:
        """Step 5: ``os.replace``, retried on ``PermissionError`` (antivirus, indexer, sync clients).

        Args:
            temporary: ``<file>.tmp``.
            target: Data file path.

        Returns:
            Success or ``STORAGE_REPLACE_FAILED``.
        """
        for attempt in range(self._retry_count + 1):
            try:
                self._fs.replace(temporary, target)
            except PermissionError as error:
                _logger.info("Replace of %s refused (attempt %d): %s", target, attempt + 1, error)
                if attempt < self._retry_count:
                    self._fs.sleep(self._retry_delay_s)
            except OSError as error:
                _logger.warning("Cannot replace %s: %s", target, error)
                return ValidationResult.failure(ErrorCodeEnum.STORAGE_REPLACE_FAILED)
            else:
                return ValidationResult.success()
        _logger.warning("Replace of %s still refused after %d attempts", target, self._retry_count + 1)
        return ValidationResult.failure(ErrorCodeEnum.STORAGE_REPLACE_FAILED)

    @staticmethod
    def _discard(temporary: Path) -> None:
        """Delete a temporary file that must not be used.

        Args:
            temporary: ``<file>.tmp``.
        """
        try:
            temporary.unlink(missing_ok=True)
        except OSError as error:
            _logger.warning("Cannot delete %s: %s", temporary, error)
