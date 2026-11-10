"""Scripted ``UserDataFilePort``: asynchronous saves wait until the test completes them."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import override

from concentrator.application.ports.user_data_file_port import UserDataFilePort
from concentrator.application.storage.file_state_enum import FileStateEnum
from concentrator.application.storage.recovery_report import FileProbe, RecoveryReport
from concentrator.application.storage.recovery_source_enum import RecoverySourceEnum
from concentrator.application.storage.save_outcome import SaveOutcome
from concentrator.application.storage.user_data import StoredUserData, UserData
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from tests.fakes.user_data_factory import SAVED_AT

NOT_FOUND = ValidationResult.failure(ErrorCodeEnum.STORAGE_FILE_NOT_FOUND)


def absent() -> FileProbe:
    return FileProbe(state=FileStateEnum.ABSENT, stored=None, validation=NOT_FOUND)


def valid(stored: StoredUserData) -> FileProbe:
    return FileProbe(state=FileStateEnum.VALID, stored=stored, validation=ValidationResult.success())


def invalid(code: ErrorCodeEnum = ErrorCodeEnum.STORAGE_SYNTAX_INVALID) -> FileProbe:
    return FileProbe(state=FileStateEnum.INVALID, stored=None, validation=ValidationResult.failure(code))


def report(
    path: Path, main: FileProbe, temporary: FileProbe | None = None, backup: FileProbe | None = None
) -> RecoveryReport:
    return RecoveryReport(path=path, main=main, temporary=temporary or absent(), backup=backup or absent())


@dataclass
class PendingSave:
    path: Path
    data: UserData
    revision: int
    on_done: Callable[[SaveOutcome], None]
    overwrite_external: bool


class FakeUserDataFile(UserDataFilePort):
    """Answers from ``reports``, ``loads`` and the ``*_failure`` attributes; records ``calls``.

    ``create`` makes ``load`` return the created data, unless ``loads`` already has an answer.
    """

    def __init__(self, saved_at: datetime = SAVED_AT) -> None:
        self.saved_at = saved_at
        self.existing: set[Path] = set()
        self.reports: dict[Path, RecoveryReport] = {}
        self.loads: dict[Path, DataResult[StoredUserData]] = {}
        self.probe_failure: ValidationResult | None = None
        self.create_failure: ValidationResult | None = None
        self.restore_failure: ValidationResult | None = None
        self.rename_failure: ValidationResult | None = None
        self.blocking_validation = ValidationResult.success()
        self.blocking_validations: list[ValidationResult] = []
        self.pending: list[PendingSave] = []
        self.blocking: list[tuple[int, bool]] = []
        self.calls: list[tuple[str, Path]] = []

    @override
    def exists(self, path: Path) -> bool:
        return path in self.existing

    @override
    def is_same_file(self, first: Path, second: Path) -> bool:
        return first.as_posix().casefold() == second.as_posix().casefold()

    @override
    def load(self, path: Path) -> DataResult[StoredUserData]:
        self.calls.append(("load", path))
        return self.loads.get(path, DataResult.fail(NOT_FOUND))

    @override
    def probe(self, path: Path) -> DataResult[RecoveryReport]:
        self.calls.append(("probe", path))
        if self.probe_failure is not None:
            return DataResult.fail(self.probe_failure)
        return DataResult.ok(self.reports.get(path, report(path, absent())))

    @override
    def restore(self, path: Path, source: RecoverySourceEnum) -> DataResult[StoredUserData]:
        self.calls.append((f"restore:{source.name}", path))
        if self.restore_failure is not None:
            return DataResult.fail(self.restore_failure)
        probe = self.reports[path].probe_of(source)
        assert probe is not None
        assert probe.stored is not None
        return DataResult.ok(StoredUserData(data=probe.stored.data, saved_at=self.saved_at))

    @override
    def create(self, path: Path, data: UserData) -> DataResult[StoredUserData]:
        self.calls.append(("create", path))
        if self.create_failure is not None:
            return DataResult.fail(self.create_failure)
        self.existing.add(path)
        stored = StoredUserData(data=data, saved_at=self.saved_at)
        self.loads.setdefault(path, DataResult.ok(stored))
        return DataResult.ok(stored)

    @override
    def quarantine(self, path: Path) -> DataResult[str]:
        return self._rename("quarantine", path, ".corrupt-20261106-100000")

    @override
    def discard_temporary(self, path: Path) -> DataResult[str]:
        return self._rename("discard", path, ".tmp.discarded-20261106-100000")

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
        self.calls.append(("save_async", path))
        self.pending.append(PendingSave(path, data, revision, on_done, overwrite_external))

    @override
    def save(
        self, path: Path, data: UserData, revision: int, *, timeout_ms: int, overwrite_external: bool = False
    ) -> SaveOutcome:
        self.calls.append(("save", path))
        self.blocking.append((revision, overwrite_external))
        validation = self.blocking_validations.pop(0) if self.blocking_validations else self.blocking_validation
        saved_at = self.saved_at if validation.is_success else None
        return SaveOutcome(revision=revision, saved_at=saved_at, validation=validation)

    @override
    def flush(self, timeout_ms: int) -> ValidationResult:
        return ValidationResult.success()

    def complete(self, validation: ValidationResult | None = None, saved_at: datetime | None = None) -> PendingSave:
        """Deliver the outcome of the oldest pending save."""
        save = self.pending.pop(0)
        result = validation or ValidationResult.success()
        when = (saved_at or self.saved_at) if result.is_success else None
        save.on_done(SaveOutcome(revision=save.revision, saved_at=when, validation=result))
        return save

    def _rename(self, name: str, path: Path, suffix: str) -> DataResult[str]:
        self.calls.append((name, path))
        if self.rename_failure is not None:
            return DataResult.fail(self.rename_failure)
        return DataResult.ok(path.with_name(path.name + suffix).as_posix())
