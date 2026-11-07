"""Debounced saving of the in-memory user data (ADR-006, ADR-029, ADR-032, ADR-033)."""

import logging
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from concentrator.application.common.app_config import StorageSection
from concentrator.application.common.event_bus import EventBus
from concentrator.application.ports.scheduler_port import ScheduledCallPort, SchedulerPort
from concentrator.application.ports.user_data_file_port import UserDataFilePort
from concentrator.application.ports.user_data_session_port import UserDataSessionPort
from concentrator.application.storage.save_outcome import SaveOutcome
from concentrator.application.storage.save_state_enum import SaveStateEnum
from concentrator.application.storage.storage_events import SaveStatusChangedEvent, UserDataChangedEvent
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult

_logger = logging.getLogger(__name__)


class _SaveTimers:
    """Debounce timer (restarted at each change), maximum delay timer (not restarted) and retry timer."""

    def __init__(self, scheduler: SchedulerPort) -> None:
        """Create idle timers.

        Args:
            scheduler: Main-thread scheduler.
        """
        self._scheduler = scheduler
        self._debounce: ScheduledCallPort | None = None
        self._deadline: ScheduledCallPort | None = None
        self._retry: ScheduledCallPort | None = None

    def after_change(self, debounce_ms: int, max_delay_ms: int, callback: Callable[[], None]) -> None:
        """Restart the debounce timer; start the maximum delay timer at the first unsaved change.

        Args:
            debounce_ms: ``storage.save_debounce_ms``.
            max_delay_ms: ``storage.save_max_delay_ms``.
            callback: The save.
        """
        if self._debounce is not None:
            self._debounce.cancel()
        self._debounce = self._scheduler.call_later(debounce_ms, callback)
        if self._deadline is None:
            self._deadline = self._scheduler.call_later(max_delay_ms, callback)

    def retry_later(self, delay_ms: int, callback: Callable[[], None]) -> None:
        """Schedule an automatic retry after a failed save (callers have cancelled every timer before).

        Args:
            delay_ms: ``storage.failed_save_retry_ms``.
            callback: The save.
        """
        self._retry = self._scheduler.call_later(delay_ms, callback)

    def cancel_all(self) -> None:
        """Cancel every pending timer (a save starts now, or the coordinator stops)."""
        for call in (self._debounce, self._deadline, self._retry):
            if call is not None:
                call.cancel()
        self._debounce = self._deadline = self._retry = None


class SaveCoordinator:
    """Saves the session data to the open file; publishes ``SaveStatusChangedEvent``.

    One save is in flight at a time; changes made meanwhile are saved right after it. A failed save
    keeps the data in memory and is retried every ``storage.failed_save_retry_ms``, except after
    ``STORAGE_FILE_CHANGED_EXTERNALLY``: then no save is attempted until the user reloads the file or
    keeps Concentrator's version.
    """

    def __init__(
        self,
        *,
        session: UserDataSessionPort,
        file: UserDataFilePort,
        scheduler: SchedulerPort,
        event_bus: EventBus,
        storage: StorageSection,
    ) -> None:
        """Create the coordinator (no file attached yet) and subscribe to ``UserDataChangedEvent``.

        Args:
            session: In-memory data.
            file: Data file adapter.
            scheduler: Main-thread scheduler.
            event_bus: Receives the status events; publishes the change events.
            storage: ``[storage]`` timings.
        """
        self._session = session
        self._file = file
        self._event_bus = event_bus
        self._storage = storage
        self._timers = _SaveTimers(scheduler)
        self._path: Path | None = None
        self._saved_revision = 0
        self._in_flight: int | None = None
        self._save_again = False
        self._conflict = False
        self._overwrite_next = False
        self._closed = False
        self._status = SaveStatusChangedEvent(state=SaveStateEnum.NO_FILE)
        event_bus.subscribe(UserDataChangedEvent, self._on_data_changed)

    @property
    def status(self) -> SaveStatusChangedEvent:
        """Last published status."""
        return self._status

    @property
    def has_unsaved_changes(self) -> bool:
        """Whether the session holds changes that are not in the file yet."""
        return self._path is not None and self._session.revision() != self._saved_revision

    def attach(self, path: Path, saved_at: datetime) -> None:
        """Start saving to a file whose content is the session's current data (opened or reloaded).

        Args:
            path: Data file path.
            saved_at: ``saved_at`` of the file.
        """
        self._timers.cancel_all()
        self._path = path
        self._saved_revision = self._session.revision()
        self._in_flight = None
        self._save_again = self._conflict = self._overwrite_next = self._closed = False
        _logger.info("Saving to %s", path)
        self._publish(SaveStateEnum.SAVED, ValidationResult.success(), saved_at)

    def keep_local_version(self) -> None:
        """Resolve an external modification by overwriting the file (ADR-033), until a save succeeds."""
        if not self._conflict:
            return
        _logger.info("Keeping Concentrator's version over the externally changed file")
        self._conflict = False
        self._overwrite_next = True
        self._save_now()

    def flush_for_shutdown(self, *, overwrite_external: bool = False) -> ValidationResult:
        """Save pending changes synchronously (close, quit, Windows session end; ADR-032).

        Args:
            overwrite_external: Overwrite a file changed outside Concentrator; this resolves the
                conflict like ``keep_local_version`` and holds until a save succeeds.

        Returns:
            Success when nothing is pending or the save succeeded, else the failure (a retry is then
            scheduled, unless the file was changed externally).
        """
        self._timers.cancel_all()
        if overwrite_external:
            self._conflict = False
            self._overwrite_next = True
        path = self._path
        revision = self._session.revision()
        if path is None or self._closed or (revision == self._saved_revision and self._in_flight is None):
            return ValidationResult.success()
        outcome = self._file.save(
            path,
            self._session.current(),
            revision,
            timeout_ms=self._storage.shutdown_flush_timeout_ms,
            overwrite_external=self._overwrite_next,
        )
        self._in_flight = None
        self._save_again = False
        self._apply_outcome(outcome)
        return outcome.validation

    def close(self) -> None:
        """Stop saving (the application quits); late save results are ignored."""
        self._closed = True
        self._timers.cancel_all()

    def _on_data_changed(self, _event: UserDataChangedEvent) -> None:
        """Schedule a save after a change.

        Args:
            _event: The change (its revision is read from the session when saving).
        """
        if self._path is None or self._closed or self._conflict:
            return
        if self._status.state in {SaveStateEnum.SAVED, SaveStateEnum.NO_FILE}:
            self._publish(SaveStateEnum.PENDING, ValidationResult.success(), self._status.saved_at)
        self._timers.after_change(self._storage.save_debounce_ms, self._storage.save_max_delay_ms, self._save_now)

    def _save_now(self) -> None:
        """Start a save of the current data, unless one is in flight (it is then repeated after)."""
        self._timers.cancel_all()
        path = self._path
        if path is None or self._closed or self._conflict:
            return
        if self._in_flight is not None:
            self._save_again = True
            return
        revision = self._session.revision()
        if revision == self._saved_revision:
            if self._status.state is not SaveStateEnum.SAVED:
                self._publish(SaveStateEnum.SAVED, ValidationResult.success(), self._status.saved_at)
            return
        self._in_flight = revision
        self._publish(SaveStateEnum.SAVING, ValidationResult.success(), self._status.saved_at)
        self._file.save_async(
            path, self._session.current(), revision, self._on_saved, overwrite_external=self._overwrite_next
        )

    def _on_saved(self, outcome: SaveOutcome) -> None:
        """Handle the result of an asynchronous save (main thread).

        Args:
            outcome: Result delivered by the file adapter.
        """
        if self._closed or outcome.revision < self._saved_revision:
            _logger.debug("Late save result for revision %d ignored", outcome.revision)
            return
        self._in_flight = None
        self._apply_outcome(outcome)
        if self._save_again:
            self._save_again = False
            if outcome.validation.is_success:
                self._save_now()

    def _apply_outcome(self, outcome: SaveOutcome) -> None:
        """Update the state after a save.

        Args:
            outcome: Result of the save.
        """
        if outcome.validation.is_success:
            self._saved_revision = outcome.revision
            self._overwrite_next = False
            pending = self._session.revision() != self._saved_revision
            state = SaveStateEnum.PENDING if pending else SaveStateEnum.SAVED
            self._publish(state, outcome.validation, outcome.saved_at or self._status.saved_at)
            return
        codes = outcome.validation.error_codes
        _logger.warning("Save of revision %d failed: %s", outcome.revision, [code.name for code in codes])
        if ErrorCodeEnum.STORAGE_FILE_CHANGED_EXTERNALLY in codes:
            self._conflict = True
            self._save_again = False
            self._timers.cancel_all()
        else:
            self._timers.retry_later(self._storage.failed_save_retry_ms, self._save_now)
        self._publish(SaveStateEnum.FAILED, outcome.validation, self._status.saved_at)

    def _publish(self, state: SaveStateEnum, validation: ValidationResult, saved_at: datetime | None) -> None:
        """Publish the status when it changes.

        Args:
            state: New state.
            validation: Issues to show.
            saved_at: Last successful save.
        """
        status = SaveStatusChangedEvent(state=state, path=self._path, saved_at=saved_at, validation=validation)
        if status == self._status:
            return
        self._status = status
        self._event_bus.publish(status)
