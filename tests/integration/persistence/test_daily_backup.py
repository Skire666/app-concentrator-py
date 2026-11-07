import errno
import shutil
from datetime import date
from pathlib import Path

import pytest

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.infrastructure.persistence.daily_backup import DailyBackup, backup_name

TODAY = date(2026, 11, 6)


class CountingCopy:
    def __init__(self) -> None:
        self.calls = 0
        self.error: OSError | None = None

    def __call__(self, source: Path, target: Path) -> object:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return shutil.copy2(source, target)


@pytest.fixture
def data_file(tmp_path: Path) -> Path:
    path = tmp_path / "concentrator.toml"
    path.write_text("{}", encoding="utf-8")
    return path


def _backup(tmp_path: Path, copy: CountingCopy, *, enabled: bool = True) -> DailyBackup:
    return DailyBackup(backup_dir=tmp_path / "backups", enabled=enabled, retention_days=7, copy=copy)


def test_backup_name_uses_stem_and_iso_date() -> None:
    assert backup_name("concentrator", TODAY) == "concentrator-2026-11-06.toml"


def test_first_save_of_the_day_copies_once(tmp_path: Path, data_file: Path) -> None:
    copy = CountingCopy()
    backup = _backup(tmp_path, copy)

    first = backup.after_save(data_file, TODAY)
    second = backup.after_save(data_file, TODAY)

    assert first.is_success
    assert second.is_success
    assert copy.calls == 1
    assert (tmp_path / "backups" / "concentrator-2026-11-06.toml").read_text(encoding="utf-8") == "{}"


def test_disabled_backup_does_nothing(tmp_path: Path, data_file: Path) -> None:
    copy = CountingCopy()

    assert _backup(tmp_path, copy, enabled=False).after_save(data_file, TODAY).is_success
    assert copy.calls == 0
    assert not (tmp_path / "backups").exists()


def test_copy_failure_is_a_warning(tmp_path: Path, data_file: Path) -> None:
    copy = CountingCopy()
    copy.error = OSError(errno.EACCES, "denied")

    result = _backup(tmp_path, copy).after_save(data_file, TODAY)

    assert result.is_success_with_warnings
    assert result.error_codes == (ErrorCodeEnum.STORAGE_BACKUP_FAILED,)


def test_retention_deletes_only_exact_old_copies_of_this_file(tmp_path: Path, data_file: Path) -> None:
    folder = tmp_path / "backups"
    folder.mkdir()
    kept_names = [
        "concentrator-2026-10-31.toml",  # 6 days old: inside the 7-day retention
        "concentrator-2026-11-07.toml",  # in the future (clock changed): kept
        "other-2026-10-01.toml",  # another data file
        "Concentrator-2026-10-01.toml",  # different case: not an exact match
        "concentrator-2026-10-01.toml.bak",
        "concentrator-2026-10-01.tomlx",
        "concentrator-2026-13-40.toml",  # not a real date
        "concentrator-2026-10-1.toml",
        "xconcentrator-2026-10-01.toml",
        "notes.txt",
    ]
    deleted_names = ["concentrator-2026-10-30.toml", "concentrator-2025-01-01.toml"]
    for name in kept_names + deleted_names:
        (folder / name).write_text(name, encoding="utf-8")
    (folder / "concentrator-2026-01-01.toml").mkdir()  # a folder with a matching name is never touched

    result = _backup(tmp_path, CountingCopy()).after_save(data_file, TODAY)

    remaining = sorted(entry.name for entry in folder.iterdir())
    assert result.is_success
    assert remaining == sorted([*kept_names, "concentrator-2026-01-01.toml", "concentrator-2026-11-06.toml"])
