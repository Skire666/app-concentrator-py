"""Startup situation and the actions it allows; ``classify`` is the ADR-027 matrix."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Final

from concentrator.application.storage.file_state_enum import FileStateEnum
from concentrator.application.storage.recovery_report import FileProbe, RecoveryReport
from concentrator.application.storage.recovery_source_enum import RecoverySourceEnum
from concentrator.application.storage.startup_reason_enum import StartupReasonEnum
from concentrator.application.storage.startup_step_enum import StartupStepEnum
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult

_RETRY_REASONS: Final = frozenset(
    {StartupReasonEnum.FILE_NOT_FOUND, StartupReasonEnum.FILE_MISSING, StartupReasonEnum.FILE_UNREADABLE}
)
_START_EMPTY_REASONS: Final = frozenset({StartupReasonEnum.FILE_DAMAGED, StartupReasonEnum.FILE_MISSING})
_CHOOSE_ANOTHER_REASONS: Final = frozenset(
    {
        StartupReasonEnum.FILE_DAMAGED,
        StartupReasonEnum.FILE_MISSING,
        StartupReasonEnum.FILE_UNREADABLE,
        StartupReasonEnum.NEWER_VERSION,
    }
)


@dataclass(frozen=True, slots=True)
class RecoveryCandidate:
    """A valid side file that can replace the data file.

    Attributes:
        source: ``.tmp`` or ``.bak``.
        saved_at: Its ``saved_at``.
    """

    source: RecoverySourceEnum
    saved_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class StartupPlan:
    """Where the startup stands and what the dialogs may offer.

    Attributes:
        step: What has to happen next.
        reason: Row of the ADR-027 matrix.
        path: Data file concerned, ``None`` at first run.
        default_path: ``paths.default_data_file``.
        default_exists: Whether a file exists at the default location.
        candidates: Restorable side files, newest first (``.tmp`` first on a tie).
        problem: Why the data file cannot be used (empty when ready or at first run).
    """

    step: StartupStepEnum
    reason: StartupReasonEnum
    path: Path | None
    default_path: Path
    default_exists: bool
    candidates: tuple[RecoveryCandidate, ...] = ()
    problem: ValidationResult = field(default_factory=ValidationResult.success)

    @property
    def can_retry(self) -> bool:
        """Whether "Retry" is offered: locked file, drive not connected yet, or file absent but put back."""
        return self.reason in _RETRY_REASONS

    @property
    def can_keep_current(self) -> bool:
        """Whether "Keep the current file" is offered (valid file with a newer ``.tmp``)."""
        return self.reason is StartupReasonEnum.NEWER_TEMPORARY

    @property
    def can_start_empty(self) -> bool:
        """Whether "Start with an empty file" is offered."""
        return self.reason in _START_EMPTY_REASONS

    @property
    def can_choose_another(self) -> bool:
        """Whether "Choose another file..." is offered in the recovery dialog."""
        return self.reason in _CHOOSE_ANOTHER_REASONS


def _candidate(source: RecoverySourceEnum, probe: FileProbe) -> RecoveryCandidate | None:
    """Turn a valid side file into a candidate.

    Args:
        source: Side file.
        probe: Its probe.

    Returns:
        The candidate, ``None`` when the file is absent or invalid.
    """
    saved_at = probe.saved_at
    return RecoveryCandidate(source, saved_at) if probe.is_valid and saved_at is not None else None


def _candidates(report: RecoveryReport) -> tuple[RecoveryCandidate, ...]:
    """Valid side files, newest first; the sort is stable, so ``.tmp`` comes first on a tie.

    Args:
        report: Inspection of the data file.

    Returns:
        The candidates.
    """
    found = (
        _candidate(RecoverySourceEnum.TEMPORARY, report.temporary),
        _candidate(RecoverySourceEnum.BACKUP, report.backup),
    )
    return tuple(sorted((item for item in found if item is not None), key=lambda item: item.saved_at, reverse=True))


def _classify_invalid_main(report: RecoveryReport) -> tuple[StartupStepEnum, StartupReasonEnum]:
    """Step of a main file that exists but does not load.

    Args:
        report: Inspection of the data file.

    Returns:
        ``FATAL`` for a locked file or a newer schema (never renamed or written), else recovery.
    """
    codes = report.main.validation.error_codes
    if ErrorCodeEnum.STORAGE_FILE_UNREADABLE in codes:
        return StartupStepEnum.FATAL, StartupReasonEnum.FILE_UNREADABLE
    if ErrorCodeEnum.STORAGE_SCHEMA_VERSION_UNSUPPORTED in codes:
        return StartupStepEnum.FATAL, StartupReasonEnum.NEWER_VERSION
    return StartupStepEnum.NEEDS_RECOVERY, StartupReasonEnum.FILE_DAMAGED


type _Verdict = tuple[StartupStepEnum, StartupReasonEnum, tuple[RecoveryCandidate, ...]]


def _verdict(report: RecoveryReport) -> _Verdict:
    """Step, reason and restorable candidates of an inspection.

    Args:
        report: Inspection of the data file, ``.tmp`` and ``.bak``.

    Returns:
        The verdict; candidates are only kept when the step is ``NEEDS_RECOVERY``.
    """
    main = report.main
    candidates = _candidates(report)
    if main.is_valid:
        main_saved_at = main.saved_at
        newer = tuple(
            item
            for item in candidates
            if item.source is RecoverySourceEnum.TEMPORARY
            and main_saved_at is not None
            and item.saved_at > main_saved_at
        )
        if newer:
            return StartupStepEnum.NEEDS_RECOVERY, StartupReasonEnum.NEWER_TEMPORARY, newer
        return StartupStepEnum.READY, StartupReasonEnum.OPENED, ()
    if main.state is FileStateEnum.ABSENT:
        if candidates:
            return StartupStepEnum.NEEDS_RECOVERY, StartupReasonEnum.FILE_MISSING, candidates
        return StartupStepEnum.NEEDS_LOCATION, StartupReasonEnum.FILE_NOT_FOUND, ()
    step, reason = _classify_invalid_main(report)
    return step, reason, candidates if step is StartupStepEnum.NEEDS_RECOVERY else ()


def classify(report: RecoveryReport, *, default_path: Path, default_exists: bool) -> StartupPlan:
    """Apply the ADR-027 matrix to an inspection.

    Args:
        report: Inspection of the data file, ``.tmp`` and ``.bak``.
        default_path: ``paths.default_data_file``.
        default_exists: Whether a file exists there.

    Returns:
        The plan.
    """
    step, reason, candidates = _verdict(report)
    return StartupPlan(
        step=step,
        reason=reason,
        path=report.path,
        default_path=default_path,
        default_exists=default_exists,
        candidates=candidates,
        problem=ValidationResult.success() if report.main.is_valid else report.main.validation,
    )
