"""Fingerprint of the data file, to detect changes made outside Concentrator (ADR-033)."""

import hashlib
import logging
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult

_logger = logging.getLogger(__name__)


def content_digest(content: bytes) -> str:
    """SHA-256 of file bytes.

    Args:
        content: File bytes.

    Returns:
        The hexadecimal digest.
    """
    return hashlib.sha256(content).hexdigest()


@dataclass(frozen=True, slots=True)
class FileFingerprint:
    """Size, modification time and content hash of a file at one instant.

    Attributes:
        size: Size in bytes.
        mtime_ns: Modification time in nanoseconds.
        sha256: Hexadecimal SHA-256 of the content.
    """

    size: int
    mtime_ns: int
    sha256: str

    @classmethod
    def of(cls, content: bytes, stat: os.stat_result) -> Self:
        """Fingerprint of bytes just read from, or written to, a file.

        Args:
            content: File bytes.
            stat: ``stat`` of the same file.

        Returns:
            The fingerprint.
        """
        return cls(size=stat.st_size, mtime_ns=stat.st_mtime_ns, sha256=content_digest(content))


def _key(path: Path) -> str:
    """Normalized registry key (case and separators do not matter on Windows).

    Args:
        path: File path.

    Returns:
        The key.
    """
    return os.path.normcase(path.absolute())


class FingerprintRegistry:
    """Last known fingerprint per data file; shared by the main and the writer thread (locked)."""

    def __init__(self) -> None:
        """Create an empty registry."""
        self._lock = threading.Lock()
        self._fingerprints: dict[str, FileFingerprint] = {}

    def remember(self, path: Path, fingerprint: FileFingerprint) -> None:
        """Record the fingerprint after a load or a save.

        Args:
            path: Data file path.
            fingerprint: Its fingerprint.
        """
        with self._lock:
            self._fingerprints[_key(path)] = fingerprint

    def forget(self, path: Path) -> None:
        """Drop the fingerprint (the file was renamed away).

        Args:
            path: Data file path.
        """
        with self._lock:
            self._fingerprints.pop(_key(path), None)

    def known(self, path: Path) -> FileFingerprint | None:
        """Return the recorded fingerprint.

        Args:
            path: Data file path.

        Returns:
            The fingerprint, ``None`` when the file was never loaded or saved.
        """
        with self._lock:
            return self._fingerprints.get(_key(path))

    def check_unchanged(self, path: Path) -> ValidationResult:
        """Compare the file on disk with its recorded fingerprint (writer thread, before replacing).

        Another size is a change. With the same size the SHA-256 decides: ``mtime_ns`` is never trusted
        to prove the file unchanged, because an edit made within the timestamp granularity of the last
        save can keep it. A file touched without a content change is not a conflict and its fingerprint
        is refreshed. A missing file, a file never seen, or a file that cannot be read here (the replace
        will report it) is not a conflict.

        Args:
            path: Data file path.

        Returns:
            Success, or ``STORAGE_FILE_CHANGED_EXTERNALLY``.
        """
        known = self.known(path)
        if known is None:
            return ValidationResult.success()
        try:
            stat = path.stat()
            if stat.st_size != known.size:
                return self._changed(path)
            content = path.read_bytes()
        except FileNotFoundError:
            _logger.warning("Data file %s was deleted outside Concentrator; it will be written again", path)
            return ValidationResult.success()
        except OSError as error:
            _logger.info("Cannot inspect %s before saving (%s); the replace will report it", path, error)
            return ValidationResult.success()
        if content_digest(content) == known.sha256:
            if stat.st_mtime_ns != known.mtime_ns:
                self.remember(path, FileFingerprint.of(content, stat))
            return ValidationResult.success()
        return self._changed(path)

    @staticmethod
    def _changed(path: Path) -> ValidationResult:
        """Report an external modification.

        Args:
            path: Data file path.

        Returns:
            ``STORAGE_FILE_CHANGED_EXTERNALLY``.
        """
        _logger.warning("Data file %s was changed outside Concentrator; nothing was written", path)
        return ValidationResult.failure(ErrorCodeEnum.STORAGE_FILE_CHANGED_EXTERNALLY)
