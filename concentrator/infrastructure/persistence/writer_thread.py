"""The single thread that writes user data (``AGENTS.md`` section 6.4, ADR-028)."""

import logging
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, wait
from typing import Final

from concentrator.application.ports.error_reporter_port import ErrorReporterPort
from concentrator.application.ports.main_thread_dispatcher_port import MainThreadDispatcherPort
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult

_logger = logging.getLogger(__name__)

THREAD_NAME_PREFIX: Final = "writer"
MS_PER_SECOND: Final = 1000


def _no_op() -> None:
    """Job marking the end of the queue for ``flush``."""


class WriterThread:
    """Runs write jobs one at a time, in submission order.

    A job that raises unexpectedly (a programming error) is logged CRITICAL with its traceback,
    forwarded to the error reporter and replaced by the caller's fallback value.
    """

    def __init__(self, dispatcher: MainThreadDispatcherPort, reporter: ErrorReporterPort) -> None:
        """Start the executor.

        Args:
            dispatcher: Brings asynchronous results back to the main thread.
            reporter: Receives the exceptions raised by jobs.
        """
        self._dispatcher = dispatcher
        self._reporter = reporter
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix=THREAD_NAME_PREFIX)

    def submit[T](self, job: Callable[[], T], fallback: T, on_done: Callable[[T], None]) -> None:
        """Queue a job; ``on_done`` receives its result on the main thread.

        Args:
            job: Work to run on the writer thread.
            fallback: Result used when the job raises.
            on_done: Called on the main thread with the result.
        """
        future = self._executor.submit(job)
        future.add_done_callback(lambda done: self._dispatcher.dispatch(lambda: on_done(self._result(done, fallback))))

    def run_sync[T](self, job: Callable[[], T], fallback: T, timeout_ms: int, timed_out: T) -> T:
        """Run a job on the writer thread and wait for it (startup and shutdown).

        Args:
            job: Work to run on the writer thread.
            fallback: Result used when the job raises.
            timeout_ms: Longest wait.
            timed_out: Result returned when the wait times out (the job keeps running).

        Returns:
            The job's result, ``fallback`` or ``timed_out``.
        """
        future = self._executor.submit(job)
        done, _not_done = wait([future], timeout=timeout_ms / MS_PER_SECOND)
        if not done:
            _logger.error("A blocking write did not finish within %d ms", timeout_ms)
            return timed_out
        return self._result(future, fallback)

    def flush(self, timeout_ms: int) -> ValidationResult:
        """Wait for every queued job: one worker runs jobs in order, so a no-op job queued now ends last.

        Args:
            timeout_ms: Longest wait.

        Returns:
            Success, or ``STORAGE_FLUSH_TIMEOUT``.
        """
        marker = self._executor.submit(_no_op)
        done, _not_done = wait([marker], timeout=timeout_ms / MS_PER_SECOND)
        if not done:
            _logger.error("Writes still running after %d ms", timeout_ms)
            return ValidationResult.failure(ErrorCodeEnum.STORAGE_FLUSH_TIMEOUT)
        return ValidationResult.success()

    def shutdown(self) -> None:
        """Stop accepting jobs; a job still running finishes in the background."""
        self._executor.shutdown(wait=False)

    def _result[T](self, future: Future[T], fallback: T) -> T:
        """Return a completed job's result, reporting its exception.

        Args:
            future: Completed job.
            fallback: Result used when the job raised.

        Returns:
            The result or the fallback.
        """
        error = future.exception()
        if error is None:
            return future.result()
        _logger.critical("A write job failed", exc_info=error)
        self._reporter.report(error)
        return fallback
