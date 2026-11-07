import errno
import os
import shutil
from pathlib import Path

import pytest

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.infrastructure.persistence.atomic_file_writer import AtomicFileWriter, FileSystem


class Recorder:
    """File operations that fail on demand and record the sleeps."""

    def __init__(self, *, replace_failures: int = 0, replace_error: OSError | None = None) -> None:
        self.replace_failures = replace_failures
        self.replace_error = replace_error
        self.replace_calls = 0
        self.sleeps: list[float] = []
        self.copy_error: OSError | None = None
        self.read_back: bytes | None = None
        self.read_error: OSError | None = None

    def replace(self, source: Path, target: Path) -> None:
        self.replace_calls += 1
        if self.replace_error is not None:
            raise self.replace_error
        if self.replace_calls <= self.replace_failures:
            raise PermissionError(errno.EACCES, "locked", str(target))
        source.replace(target)

    def copy(self, source: Path, target: Path) -> object:
        if self.copy_error is not None:
            raise self.copy_error
        return shutil.copy2(source, target)

    def read_bytes(self, path: Path) -> bytes:
        if self.read_error is not None:
            raise self.read_error
        return self.read_back if self.read_back is not None else path.read_bytes()

    def file_system(self) -> FileSystem:
        return FileSystem(replace=self.replace, copy=self.copy, read_bytes=self.read_bytes, sleep=self.sleeps.append)


def _writer(recorder: Recorder, retries: int = 5) -> AtomicFileWriter:
    return AtomicFileWriter(replace_retry_count=retries, replace_retry_delay_ms=200, file_system=recorder.file_system())


@pytest.fixture
def target(tmp_path: Path) -> Path:
    return tmp_path / "data" / "concentrator.toml"


def test_first_write_creates_folder_and_file_without_backup(target: Path) -> None:
    result = _writer(Recorder()).write(target, b"one")

    assert result.is_success
    assert not result.issues
    assert target.read_bytes() == b"one"
    assert not target.with_name("concentrator.toml.tmp").exists()
    assert not target.with_name("concentrator.toml.bak").exists()


def test_second_write_keeps_the_previous_version_in_bak(target: Path) -> None:
    writer = _writer(Recorder())
    writer.write(target, b"one")

    result = writer.write(target, b"two")

    assert result.is_success
    assert target.read_bytes() == b"two"
    assert target.with_name("concentrator.toml.bak").read_bytes() == b"one"


def test_replace_refused_twice_then_accepted(target: Path) -> None:
    recorder = Recorder(replace_failures=2)

    result = _writer(recorder).write(target, b"one")

    assert result.is_success
    assert recorder.replace_calls == 3
    assert recorder.sleeps == [0.2, 0.2]
    assert target.read_bytes() == b"one"


def test_replace_always_refused_leaves_main_untouched_and_keeps_tmp(target: Path) -> None:
    _writer(Recorder()).write(target, b"old")
    recorder = Recorder(replace_failures=99)

    result = _writer(recorder, retries=3).write(target, b"new")

    assert result.error_codes == (ErrorCodeEnum.STORAGE_REPLACE_FAILED,)
    assert recorder.replace_calls == 4
    assert len(recorder.sleeps) == 3
    assert target.read_bytes() == b"old"
    assert target.with_name("concentrator.toml.tmp").read_bytes() == b"new"


def test_other_replace_error_fails_at_once(target: Path) -> None:
    recorder = Recorder(replace_error=OSError(errno.EXDEV, "cross device"))

    result = _writer(recorder).write(target, b"one")

    assert result.error_codes == (ErrorCodeEnum.STORAGE_REPLACE_FAILED,)
    assert recorder.replace_calls == 1
    assert recorder.sleeps == []


def test_hash_mismatch_fails_and_deletes_tmp(target: Path) -> None:
    _writer(Recorder()).write(target, b"old")
    recorder = Recorder()
    recorder.read_back = b"corrupted"

    result = _writer(recorder).write(target, b"new")

    assert result.error_codes == (ErrorCodeEnum.STORAGE_VERIFY_FAILED,)
    assert target.read_bytes() == b"old"
    assert not target.with_name("concentrator.toml.tmp").exists()


def test_unreadable_tmp_is_a_verify_failure(target: Path) -> None:
    recorder = Recorder()
    recorder.read_error = PermissionError(errno.EACCES, "denied")

    assert _writer(recorder).write(target, b"one").error_codes == (ErrorCodeEnum.STORAGE_VERIFY_FAILED,)


def test_failed_check_before_replace_writes_nothing(target: Path) -> None:
    _writer(Recorder()).write(target, b"old")

    result = _writer(Recorder()).write(
        target, b"new", lambda: ValidationResult.failure(ErrorCodeEnum.STORAGE_FILE_CHANGED_EXTERNALLY)
    )

    assert result.error_codes == (ErrorCodeEnum.STORAGE_FILE_CHANGED_EXTERNALLY,)
    assert target.read_bytes() == b"old"
    assert not target.with_name("concentrator.toml.tmp").exists()
    assert not target.with_name("concentrator.toml.bak").exists()


def test_passing_check_lets_the_write_happen(target: Path) -> None:
    assert _writer(Recorder()).write(target, b"one", ValidationResult.success).is_success
    assert target.read_bytes() == b"one"


def test_backup_copy_failure_is_a_warning_and_the_save_succeeds(target: Path) -> None:
    _writer(Recorder()).write(target, b"old")
    recorder = Recorder()
    recorder.copy_error = PermissionError(errno.EACCES, "locked")

    result = _writer(recorder).write(target, b"new")

    assert result.is_success_with_warnings
    assert result.error_codes == (ErrorCodeEnum.STORAGE_BACKUP_FAILED,)
    assert target.read_bytes() == b"new"


def test_folder_that_cannot_be_created_is_reported(tmp_path: Path) -> None:
    blocker = tmp_path / "blocker"
    blocker.write_text("a file, not a folder", encoding="utf-8")

    result = _writer(Recorder()).write(blocker / "concentrator.toml", b"one")

    assert result.error_codes == (ErrorCodeEnum.STORAGE_DIRECTORY_NOT_WRITABLE,)


@pytest.mark.parametrize(
    ("error_number", "code"),
    [(errno.ENOSPC, ErrorCodeEnum.STORAGE_DISK_FULL), (errno.EIO, ErrorCodeEnum.STORAGE_WRITE_FAILED)],
)
def test_write_errors_are_coded(
    target: Path, monkeypatch: pytest.MonkeyPatch, error_number: int, code: ErrorCodeEnum
) -> None:
    def failing_fsync(_descriptor: int) -> None:
        raise OSError(error_number, "write failed")

    monkeypatch.setattr(os, "fsync", failing_fsync)

    result = _writer(Recorder()).write(target, b"one")

    assert result.error_codes == (code,)
    assert not target.exists()
    assert not target.with_name("concentrator.toml.tmp").exists()
