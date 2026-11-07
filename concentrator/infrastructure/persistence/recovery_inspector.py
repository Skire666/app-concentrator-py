"""Builds the ``RecoveryReport`` of a data file and its side files."""

from pathlib import Path

from concentrator.application.storage.file_state_enum import FileStateEnum
from concentrator.application.storage.recovery_report import FileProbe, RecoveryReport
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.infrastructure.persistence.side_files import backup_path, temporary_path
from concentrator.infrastructure.persistence.user_data_file_reader import ReadFile, UserDataFileReader


def probe_from(result: DataResult[ReadFile]) -> FileProbe:
    """Turn a read result into a probe.

    Args:
        result: Outcome of ``UserDataFileReader.read``.

    Returns:
        ``VALID`` with the data, ``ABSENT`` for ``STORAGE_FILE_NOT_FOUND`` alone, ``INVALID`` otherwise.
    """
    if result.data is not None:
        return FileProbe(state=FileStateEnum.VALID, stored=result.data.stored, validation=result.validation)
    if result.validation.error_codes == (ErrorCodeEnum.STORAGE_FILE_NOT_FOUND,):
        return FileProbe(state=FileStateEnum.ABSENT, stored=None, validation=result.validation)
    return FileProbe(state=FileStateEnum.INVALID, stored=None, validation=result.validation)


class RecoveryInspector:
    """Reads ``<file>.tmp`` and ``<file>.bak`` next to an already read main file."""

    def __init__(self, reader: UserDataFileReader) -> None:
        """Create the inspector.

        Args:
            reader: File reader.
        """
        self._reader = reader

    def inspect(self, path: Path, main: DataResult[ReadFile]) -> RecoveryReport:
        """Build the report; the ``.bak`` is only read when the main file is not valid.

        Next to a valid main file only a newer ``.tmp`` matters (ADR-027), so a normal startup reads
        the data once.

        Args:
            path: Data file path.
            main: Result of reading the main file (read by the caller, which keeps its fingerprint).

        Returns:
            The report.
        """
        main_probe = probe_from(main)
        if main_probe.is_valid:
            backup = FileProbe(state=FileStateEnum.NOT_INSPECTED, stored=None, validation=ValidationResult.skipped())
        else:
            backup = probe_from(self._reader.read(backup_path(path)))
        return RecoveryReport(
            path=path, main=main_probe, temporary=probe_from(self._reader.read(temporary_path(path))), backup=backup
        )
