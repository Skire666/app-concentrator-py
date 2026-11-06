"""Reporting of unexpected errors (programming errors) to the user."""

from typing import Protocol


class ErrorReporterPort(Protocol):
    """Shows an unexpected error to the user, once it has been logged.

    Shared by the global exception hooks and by ``EventBus`` dispatch, the only two places allowed to
    catch ``Exception`` (AGENTS.md rule 4, ADR-021). May be called from any thread.
    """

    def report(self, error: BaseException) -> None:
        """Tell the user that an unexpected error happened.

        Args:
            error: The exception, already logged with its traceback by the caller.
        """
        ...
