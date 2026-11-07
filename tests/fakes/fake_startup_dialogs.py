"""Startup dialogs whose "user" is a script of steps run while a dialog is shown."""

from collections.abc import Callable
from typing import override

from concentrator.presentation.ports.startup_dialogs_port import StartupDialogsPort

type Step = Callable[[], None]


class FakeStartupDialogs(StartupDialogsPort):
    """Each ``show_*`` runs the next steps until a step closes the dialog; when the script runs out with
    the dialog still open, the user closes it (window button)."""

    def __init__(self, steps: list[Step] | None = None) -> None:
        self.steps: list[Step] = list(steps or [])
        self.shown: list[str] = []
        self.closed = 0
        self._open = False

    @override
    def show_first_run(self) -> None:
        self._show("first_run")

    @override
    def show_recovery(self) -> None:
        self._show("recovery")

    @override
    def close_current(self) -> None:
        self.closed += 1
        self._open = False

    def _show(self, name: str) -> None:
        self.shown.append(name)
        self._open = True
        while self._open and self.steps:
            self.steps.pop(0)()
        self._open = False
