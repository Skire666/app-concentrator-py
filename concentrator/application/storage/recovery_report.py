"""State of the data file and of its side files, as inspected at startup."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from concentrator.application.storage.file_state_enum import FileStateEnum
from concentrator.application.storage.recovery_source_enum import RecoverySourceEnum
from concentrator.application.storage.user_data import StoredUserData
from concentrator.domain.common.validation_result import ValidationResult


@dataclass(frozen=True, slots=True, kw_only=True)
class FileProbe:
    """Outcome of loading one file.

    Attributes:
        state: Absent, valid or invalid.
        stored: The loaded data when valid.
        validation: Why the file is invalid (or its warnings).
    """

    state: FileStateEnum
    stored: StoredUserData | None
    validation: ValidationResult

    @property
    def saved_at(self) -> datetime | None:
        """``saved_at`` of a valid file, ``None`` otherwise."""
        return self.stored.saved_at if self.stored is not None else None

    @property
    def is_valid(self) -> bool:
        """Whether the file loaded."""
        return self.state is FileStateEnum.VALID and self.stored is not None


@dataclass(frozen=True, slots=True, kw_only=True)
class RecoveryReport:
    """The main file, ``<file>.tmp`` and ``<file>.bak``.

    Attributes:
        path: Main data file.
        main: Main file.
        temporary: ``<file>.tmp`` (left by an interrupted or failed save).
        backup: ``<file>.bak`` (previous version).
    """

    path: Path
    main: FileProbe
    temporary: FileProbe
    backup: FileProbe

    def probe_of(self, source: RecoverySourceEnum) -> FileProbe | None:
        """Return the probe of a recovery candidate.

        Args:
            source: Candidate.

        Returns:
            The probe, ``None`` for ``UNKNOWN`` or ``UNSET``.
        """
        if source is RecoverySourceEnum.TEMPORARY:
            return self.temporary
        if source is RecoverySourceEnum.BACKUP:
            return self.backup
        return None
