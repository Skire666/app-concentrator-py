import os
from pathlib import Path

import pytest

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.infrastructure.persistence.file_fingerprint import FileFingerprint, FingerprintRegistry


@pytest.fixture
def data_file(tmp_path: Path) -> Path:
    path = tmp_path / "concentrator.toml"
    path.write_bytes(b"original")
    return path


def _remembered(path: Path) -> FingerprintRegistry:
    registry = FingerprintRegistry()
    registry.remember(path, FileFingerprint.of(path.read_bytes(), path.stat()))
    return registry


def test_unknown_file_is_not_a_conflict(data_file: Path) -> None:
    assert FingerprintRegistry().check_unchanged(data_file).is_success


def test_unchanged_file_passes(data_file: Path) -> None:
    assert _remembered(data_file).check_unchanged(data_file).is_success


def test_changed_content_is_a_conflict(data_file: Path) -> None:
    registry = _remembered(data_file)
    data_file.write_bytes(b"edited by hand")

    result = registry.check_unchanged(data_file)

    assert result.error_codes == (ErrorCodeEnum.STORAGE_FILE_CHANGED_EXTERNALLY,)


def test_same_size_change_is_found_by_the_hash(data_file: Path) -> None:
    registry = _remembered(data_file)
    stat = data_file.stat()
    data_file.write_bytes(b"ORIGINAL")
    os.utime(data_file, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))

    assert registry.check_unchanged(data_file).error_codes == (ErrorCodeEnum.STORAGE_FILE_CHANGED_EXTERNALLY,)


def test_touched_file_with_same_content_is_not_a_conflict_and_is_refreshed(data_file: Path) -> None:
    registry = _remembered(data_file)
    stat = data_file.stat()
    os.utime(data_file, ns=(stat.st_atime_ns, stat.st_mtime_ns + 5_000_000_000))

    assert registry.check_unchanged(data_file).is_success
    known = registry.known(data_file)
    assert known is not None
    assert known.mtime_ns == stat.st_mtime_ns + 5_000_000_000


def test_deleted_file_is_not_a_conflict(data_file: Path) -> None:
    registry = _remembered(data_file)
    data_file.unlink()

    assert registry.check_unchanged(data_file).is_success


def test_unreadable_same_size_file_is_left_to_the_replace(data_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    registry = _remembered(data_file)
    data_file.write_bytes(b"ORIGINAL")

    def denied(_self: Path) -> bytes:
        raise PermissionError("locked")

    monkeypatch.setattr(Path, "read_bytes", denied)

    assert registry.check_unchanged(data_file).is_success


def test_size_change_is_a_conflict_without_reading_the_file(data_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    registry = _remembered(data_file)
    data_file.write_bytes(b"edited by hand")

    def denied(_self: Path) -> bytes:
        raise PermissionError("locked")

    monkeypatch.setattr(Path, "read_bytes", denied)

    assert registry.check_unchanged(data_file).error_codes == (ErrorCodeEnum.STORAGE_FILE_CHANGED_EXTERNALLY,)


def test_forget_and_path_normalization(data_file: Path) -> None:
    registry = _remembered(data_file)

    assert registry.known(Path(str(data_file).upper())) is not None
    registry.forget(data_file)
    assert registry.known(data_file) is None


def test_same_size_and_same_mtime_change_is_found_by_the_hash(data_file: Path) -> None:
    registry = _remembered(data_file)
    stat = data_file.stat()
    data_file.write_bytes(b"ORIGINAL")
    os.utime(data_file, ns=(stat.st_atime_ns, stat.st_mtime_ns))

    assert registry.check_unchanged(data_file).error_codes == (ErrorCodeEnum.STORAGE_FILE_CHANGED_EXTERNALLY,)
