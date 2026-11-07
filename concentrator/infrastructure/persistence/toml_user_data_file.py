"""``UserDataFilePort`` on a TOML file: read pipeline, atomic save, recovery and external changes."""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Final, override

from concentrator.application.common.app_config import StorageSection
from concentrator.application.ports.clock_port import ClockPort
from concentrator.application.ports.user_data_file_port import UserDataFilePort
from concentrator.application.storage.recovery_report import RecoveryReport
from concentrator.application.storage.recovery_source_enum import RecoverySourceEnum
from concentrator.application.storage.save_outcome import SaveOutcome
from concentrator.application.storage.user_data import StoredUserData, UserData
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.infrastructure.persistence.atomic_file_writer import AtomicFileWriter, FileSystem
from concentrator.infrastructure.persistence.daily_backup import DailyBackup
from concentrator.infrastructure.persistence.file_fingerprint import FileFingerprint, FingerprintRegistry
from concentrator.infrastructure.persistence.recovery_inspector import RecoveryInspector
from concentrator.infrastructure.persistence.side_files import backup_path, corrupt_path, discarded_path, temporary_path
from concentrator.infrastructure.persistence.user_data_codec import UserDataCodec
from concentrator.infrastructure.persistence.user_data_file_reader import ReadFile, UserDataFileReader
from concentrator.infrastructure.persistence.writer_thread import WriterThread

_logger = logging.getLogger(__name__)

TEXT_ENCODING: Final = "utf-8"
SOURCE_FIELD: Final = "source"


def _crashed[T]() -> DataResult[T]:
    """Result of a write job that raised (the writer thread has logged and reported it).

    Returns:
        ``STORAGE_WRITE_FAILED``.
    """
    return DataResult.fail(ValidationResult.failure(ErrorCodeEnum.STORAGE_WRITE_FAILED))


def _timed_out[T]() -> DataResult[T]:
    """Result of a blocking write that did not finish in time.

    Returns:
        ``STORAGE_FLUSH_TIMEOUT``.
    """
    return DataResult.fail(ValidationResult.failure(ErrorCodeEnum.STORAGE_FLUSH_TIMEOUT))


class TomlUserDataFile(UserDataFilePort):
    """Reads on the calling thread, writes on the writer thread, keeps the data file fingerprints."""

    def __init__(
        self,
        *,
        codec: UserDataCodec,
        writer: WriterThread,
        clock: ClockPort,
        storage: StorageSection,
        backup_dir: Path,
        file_system: FileSystem | None = None,
    ) -> None:
        """Create the adapter.

        Args:
            codec: Read and write pipelines.
            writer: The single writer thread.
            clock: ``saved_at``, daily backup date and rename stamps.
            storage: ``[storage]`` settings.
            backup_dir: ``paths.backup_dir``.
            file_system: File operations (real ones by default; replaced in tests).
        """
        fs = file_system or FileSystem()
        self._codec = codec
        self._reader = UserDataFileReader(codec)
        self._inspector = RecoveryInspector(self._reader)
        self._writer = writer
        self._clock = clock
        self._fingerprints = FingerprintRegistry()
        self._atomic = AtomicFileWriter(
            replace_retry_count=storage.replace_retry_count,
            replace_retry_delay_ms=storage.replace_retry_delay_ms,
            file_system=fs,
        )
        self._daily = DailyBackup(
            backup_dir=backup_dir,
            enabled=storage.daily_backup_enabled,
            retention_days=storage.daily_backup_retention_days,
            copy=fs.copy,
        )
        self._blocking_timeout_ms = storage.blocking_write_timeout_ms

    @override
    def exists(self, path: Path) -> bool:
        return path.is_file()

    @override
    def load(self, path: Path) -> DataResult[StoredUserData]:
        read = self._read_main(path)
        if read.data is None:
            return DataResult.fail(read.validation)
        return DataResult.ok(read.data.stored, read.validation)

    @override
    def probe(self, path: Path) -> DataResult[RecoveryReport]:
        return DataResult.ok(self._inspector.inspect(path, self._read_main(path)))

    @override
    def restore(self, path: Path, source: RecoverySourceEnum) -> DataResult[StoredUserData]:
        return self._blocking(lambda: self._restore_job(path, source))

    @override
    def create(self, path: Path, data: UserData) -> DataResult[StoredUserData]:
        return self._blocking(lambda: self._create_job(path, data))

    @override
    def quarantine(self, path: Path) -> DataResult[str]:
        return self._blocking(lambda: self._rename(path, corrupt_path(path, self._clock.now_local())))

    @override
    def discard_temporary(self, path: Path) -> DataResult[str]:
        return self._blocking(lambda: self._rename(temporary_path(path), discarded_path(path, self._clock.now_local())))

    @override
    def save_async(
        self,
        path: Path,
        data: UserData,
        revision: int,
        on_done: Callable[[SaveOutcome], None],
        *,
        overwrite_external: bool = False,
    ) -> None:
        crashed = SaveOutcome(revision=revision, saved_at=None, validation=_crashed().validation)
        self._writer.submit(lambda: self._save_job(path, data, revision, overwrite_external), crashed, on_done)

    @override
    def save(
        self, path: Path, data: UserData, revision: int, *, timeout_ms: int, overwrite_external: bool = False
    ) -> SaveOutcome:
        return self._writer.run_sync(
            lambda: self._save_job(path, data, revision, overwrite_external),
            SaveOutcome(revision=revision, saved_at=None, validation=_crashed().validation),
            timeout_ms,
            SaveOutcome(revision=revision, saved_at=None, validation=_timed_out().validation),
        )

    @override
    def flush(self, timeout_ms: int) -> ValidationResult:
        return self._writer.flush(timeout_ms)

    def _read_main(self, path: Path) -> DataResult[ReadFile]:
        """Read the data file and remember its fingerprint when it loads.

        Args:
            path: Data file path.

        Returns:
            The read result.
        """
        read = self._reader.read(path)
        if read.data is not None:
            self._fingerprints.remember(path, read.data.fingerprint)
        return read

    def _blocking[T](self, job: Callable[[], DataResult[T]]) -> DataResult[T]:
        """Run a write on the writer thread and wait for it.

        Args:
            job: The write.

        Returns:
            Its result, ``STORAGE_WRITE_FAILED`` if it raised, ``STORAGE_FLUSH_TIMEOUT`` if it is too slow.
        """
        return self._writer.run_sync(job, _crashed(), self._blocking_timeout_ms, _timed_out())

    def _save_job(self, path: Path, data: UserData, revision: int, overwrite_external: bool) -> SaveOutcome:
        """Writer thread: one save.

        Args:
            path: Data file path.
            data: Snapshot to write.
            revision: Its revision.
            overwrite_external: Skip the external modification check.

        Returns:
            The outcome.
        """
        written = self._write(path, data, check_external=not overwrite_external)
        saved_at = written.data.saved_at if written.data is not None else None
        return SaveOutcome(revision=revision, saved_at=saved_at, validation=written.validation)

    def _create_job(self, path: Path, data: UserData) -> DataResult[StoredUserData]:
        """Writer thread: create a new data file.

        Args:
            path: Data file path.
            data: Initial content.

        Returns:
            The written data or the failure.
        """
        if path.exists():
            _logger.warning("Cannot create %s: a file already exists", path)
            return DataResult.fail(ValidationResult.failure(ErrorCodeEnum.STORAGE_FILE_ALREADY_EXISTS))
        return self._write(path, data, check_external=False)

    def _restore_job(self, path: Path, source: RecoverySourceEnum) -> DataResult[StoredUserData]:
        """Writer thread: replace the data file with a candidate, quarantining a damaged main file first.

        Args:
            path: Data file path.
            source: Candidate.

        Returns:
            The restored data or the failure.
        """
        candidate_path = {
            RecoverySourceEnum.TEMPORARY: temporary_path(path),
            RecoverySourceEnum.BACKUP: backup_path(path),
        }
        source_path = candidate_path.get(source)
        if source_path is None:
            return DataResult.fail(ValidationResult.failure(ErrorCodeEnum.ENUM_VALUE_UNKNOWN, field=SOURCE_FIELD))
        candidate = self._reader.read(source_path)
        if candidate.data is None:
            return DataResult.fail(candidate.validation)
        main = self._reader.read(path)
        if main.data is None and main.validation.error_codes != (ErrorCodeEnum.STORAGE_FILE_NOT_FOUND,):
            moved = self._rename(path, corrupt_path(path, self._clock.now_local()))
            if moved.data is None:
                return DataResult.fail(moved.validation)
        _logger.info("Restoring %s from its %s file", path, source.name.lower())
        return self._write(path, candidate.data.stored.data, check_external=False)

    def _write(self, path: Path, data: UserData, *, check_external: bool) -> DataResult[StoredUserData]:
        """Writer thread: encode, write atomically, remember the fingerprint, make the daily copy.

        Args:
            path: Data file path.
            data: Content.
            check_external: Refuse to replace a file changed outside Concentrator (ADR-033).

        Returns:
            The written data and its ``saved_at`` (warnings allowed), or the failure.
        """
        stored = StoredUserData(data=data, saved_at=self._clock.now_utc())
        content = self._codec.encode(stored).encode(TEXT_ENCODING)
        guard = (lambda: self._fingerprints.check_unchanged(path)) if check_external else None
        written = self._atomic.write(path, content, guard)
        if written.is_failure:
            return DataResult.fail(written)
        self._remember_written(path, content)
        backup = self._daily.after_save(path, self._clock.now_local().date())
        return DataResult.ok(stored, written.merge(backup))

    def _remember_written(self, path: Path, content: bytes) -> None:
        """Record the fingerprint of the bytes just written.

        Args:
            path: Data file path.
            content: Bytes written.
        """
        try:
            stat = path.stat()
        except OSError as error:
            _logger.warning("Cannot stat %s after saving: %s", path, error)
            self._fingerprints.forget(path)
            return
        self._fingerprints.remember(path, FileFingerprint.of(content, stat))

    def _rename(self, source: Path, target: Path) -> DataResult[str]:
        """Writer thread: rename a file without overwriting anything.

        Args:
            source: File to rename.
            target: New path.

        Returns:
            The new path with ``/`` separators, ``STORAGE_FILE_NOT_FOUND`` or ``STORAGE_REPLACE_FAILED``.
        """
        try:
            source.rename(target)
        except FileNotFoundError:
            _logger.warning("Cannot rename %s: it does not exist", source)
            return DataResult.fail(ValidationResult.failure(ErrorCodeEnum.STORAGE_FILE_NOT_FOUND))
        except OSError as error:
            _logger.warning("Cannot rename %s to %s: %s", source, target, error)
            return DataResult.fail(ValidationResult.failure(ErrorCodeEnum.STORAGE_REPLACE_FAILED))
        self._fingerprints.forget(source)
        _logger.info("Renamed %s to %s", source, target.name)
        return DataResult.ok(target.as_posix())
