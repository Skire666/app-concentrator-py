"""The user data file on disk: load, inspect, recover, create and save (``AGENTS.md`` section 7)."""

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from concentrator.application.storage.recovery_report import RecoveryReport
from concentrator.application.storage.recovery_source_enum import RecoverySourceEnum
from concentrator.application.storage.save_outcome import SaveOutcome
from concentrator.application.storage.user_data import StoredUserData, UserData
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.validation_result import ValidationResult


class UserDataFilePort(Protocol):
    """Reads run on the calling thread; every write runs on the single writer thread (ADR-028).

    Synchronous writes (``create``, ``restore``, ``quarantine``, ``discard_temporary``) wait at most
    ``storage.blocking_write_timeout_ms`` and then fail with ``STORAGE_FLUSH_TIMEOUT``.
    """

    def exists(self, path: Path) -> bool:
        """Tell whether a file exists at a path.

        Args:
            path: Data file path.

        Returns:
            Whether it is an existing file.
        """
        ...

    def is_same_file(self, first: Path, second: Path) -> bool:
        """Tell whether two paths name the same file (case, ``..``, links and drive letters ignored).

        Args:
            first: A path.
            second: Another path; it may not exist.

        Returns:
            Whether they are the same file.
        """
        ...

    def load(self, path: Path) -> DataResult[StoredUserData]:
        """Load the data file through the read pipeline and remember its fingerprint (ADR-033).

        Args:
            path: Data file path.

        Returns:
            The stored data, or the coded failures (2001-2009, 2020, rule errors).
        """
        ...

    def probe(self, path: Path) -> DataResult[RecoveryReport]:
        """Inspect the data file, ``<file>.tmp`` and ``<file>.bak`` (loads the valid ones).

        Args:
            path: Data file path.

        Returns:
            The report.
        """
        ...

    def restore(self, path: Path, source: RecoverySourceEnum) -> DataResult[StoredUserData]:
        """Replace the data file with a recovery candidate.

        A damaged main file is quarantined first, so that the ``.bak`` being restored is never
        overwritten by it; an unreadable main file or one written by a newer version is never renamed
        and the restore fails (ADR-027).

        Args:
            path: Data file path.
            source: Candidate to restore.

        Returns:
            The restored data and its new ``saved_at``, or the failure.
        """
        ...

    def create(self, path: Path, data: UserData) -> DataResult[StoredUserData]:
        """Create a new data file (and its folder).

        A ``.tmp`` or ``.bak`` left at that path is put aside first (``<file>.tmp.discarded-...``,
        ``<file>.bak.discarded-...``), never overwritten.

        Args:
            path: Data file path.
            data: Initial content.

        Returns:
            The written data, ``STORAGE_FILE_ALREADY_EXISTS``, ``STORAGE_REPLACE_FAILED`` when a side
            file cannot be put aside, or a write failure.
        """
        ...

    def quarantine(self, path: Path) -> DataResult[str]:
        """Rename a damaged data file to ``<file>.corrupt-YYYYMMDD-HHMMSS``.

        Args:
            path: Data file path.

        Returns:
            The new path, or the failure.
        """
        ...

    def discard_temporary(self, path: Path) -> DataResult[str]:
        """Rename a stale ``<file>.tmp`` to ``<file>.tmp.discarded-YYYYMMDD-HHMMSS`` (ADR-027).

        Args:
            path: Data file path.

        Returns:
            The new path, or the failure.
        """
        ...

    def save_async(
        self,
        path: Path,
        data: UserData,
        revision: int,
        on_done: Callable[[SaveOutcome], None],
        *,
        overwrite_external: bool = False,
    ) -> None:
        """Queue a save on the writer thread; ``on_done`` runs on the main thread.

        Args:
            path: Data file path.
            data: Immutable snapshot to write.
            revision: Revision of the snapshot, echoed in the outcome.
            on_done: Receives the outcome on the main thread.
            overwrite_external: Skip the external modification check once ("Keep Concentrator's
                version", ADR-033).
        """
        ...

    def save(
        self, path: Path, data: UserData, revision: int, *, timeout_ms: int, overwrite_external: bool = False
    ) -> SaveOutcome:
        """Save on the writer thread and wait for the outcome (shutdown flush, ADR-032).

        The job runs after any queued save, so the returned outcome is the last word on the file.

        Args:
            path: Data file path.
            data: Immutable snapshot to write.
            revision: Revision of the snapshot, echoed in the outcome.
            timeout_ms: Longest wait (``storage.shutdown_flush_timeout_ms``).
            overwrite_external: Skip the external modification check once.

        Returns:
            The outcome; ``STORAGE_FLUSH_TIMEOUT`` when the wait times out.
        """
        ...

    def flush(self, timeout_ms: int) -> ValidationResult:
        """Wait until every queued write has finished.

        Args:
            timeout_ms: Longest wait.

        Returns:
            Success, or ``STORAGE_FLUSH_TIMEOUT``.
        """
        ...
