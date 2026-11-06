"""Error reporter remembering what it was given."""

from typing import override

from concentrator.application.ports.error_reporter_port import ErrorReporterPort


class RecordingErrorReporter(ErrorReporterPort):
    """Appends every reported exception to ``errors``."""

    def __init__(self) -> None:
        self.errors: list[BaseException] = []

    @override
    def report(self, error: BaseException) -> None:
        self.errors.append(error)
