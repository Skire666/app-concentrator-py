"""Reads a data file (or a side file) from disk through the read pipeline."""

import codecs
import logging
import os
from dataclasses import dataclass
from pathlib import Path

from concentrator.application.storage.user_data import StoredUserData
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.infrastructure.persistence.file_fingerprint import FileFingerprint
from concentrator.infrastructure.persistence.user_data_codec import UserDataCodec

_logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ReadFile:
    """A file that loaded.

    Attributes:
        stored: Its data and ``saved_at``.
        fingerprint: Size, modification time and hash of the bytes read.
    """

    stored: StoredUserData
    fingerprint: FileFingerprint


@dataclass(frozen=True, slots=True)
class _RawFile:
    """Bytes read from a file and the ``stat`` of the same open handle."""

    content: bytes
    stat: os.stat_result


class UserDataFileReader:
    """File bytes -> UTF-8 text (a leading BOM is accepted) -> ``UserDataCodec``."""

    def __init__(self, codec: UserDataCodec) -> None:
        """Create the reader.

        Args:
            codec: Read pipeline.
        """
        self._codec = codec

    def read(self, path: Path) -> DataResult[ReadFile]:
        """Read and validate one file.

        Args:
            path: File to read.

        Returns:
            The file, or ``STORAGE_FILE_NOT_FOUND``, ``STORAGE_FILE_UNREADABLE``,
            ``STORAGE_ENCODING_INVALID`` or the read pipeline failures.
        """
        raw = self._read_raw(path)
        if raw.data is None:
            return DataResult.fail(raw.validation)
        content = raw.data.content.removeprefix(codecs.BOM_UTF8)
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as error:
            _logger.warning("Data file %s is not UTF-8 (byte %d)", path, error.start)
            return DataResult.fail(ValidationResult.failure(ErrorCodeEnum.STORAGE_ENCODING_INVALID))
        decoded = self._codec.decode(text)
        if decoded.data is None:
            _logger.warning("Data file %s is invalid: %s", path, [code.name for code in decoded.validation.error_codes])
            return DataResult.fail(decoded.validation)
        fingerprint = FileFingerprint.of(raw.data.content, raw.data.stat)
        return DataResult.ok(ReadFile(decoded.data, fingerprint), decoded.validation)

    @staticmethod
    def _read_raw(path: Path) -> DataResult[_RawFile]:
        """Read the bytes and the ``stat`` of the same open file.

        Args:
            path: File to read.

        Returns:
            The bytes, ``STORAGE_FILE_NOT_FOUND`` or ``STORAGE_FILE_UNREADABLE``.
        """
        try:
            with path.open("rb") as stream:
                stat = os.fstat(stream.fileno())
                content = stream.read()
        except FileNotFoundError:
            _logger.debug("No file at %s", path)
            return DataResult.fail(ValidationResult.failure(ErrorCodeEnum.STORAGE_FILE_NOT_FOUND))
        except OSError as error:
            _logger.warning("Cannot read %s: %s", path, error)
            return DataResult.fail(ValidationResult.failure(ErrorCodeEnum.STORAGE_FILE_UNREADABLE))
        return DataResult.ok(_RawFile(content, stat))
