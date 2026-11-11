"""Scripted dialogs recording what was asked."""

from collections.abc import Callable
from datetime import date
from typing import override

from concentrator.presentation.ports.dialog_port import DatePrompt, DialogPort


class FakeDialogs(DialogPort):
    """Answers from ``confirm_answers`` / ``choices`` / ``chosen_paths`` first (in order), then
    ``confirm_answer`` / ``choice`` / ``chosen_path``; ``on_error`` runs inside ``error``."""

    def __init__(self, *, confirm_answer: bool = True, chosen_path: str | None = None) -> None:
        self.confirm_answer = confirm_answer
        self.chosen_path = chosen_path
        self.confirm_answers: list[bool] = []
        self.choice = 0
        self.choices: list[int] = []
        self.chosen_paths: list[str | None] = []
        self.calls: list[tuple[str, tuple[str, ...]]] = []
        self.on_error: Callable[[], None] = lambda: None
        self.date_answer: date | None = None
        self.prompts: list[DatePrompt] = []

    def kinds(self) -> list[str]:
        return [kind for kind, _texts in self.calls]

    def texts(self, kind: str) -> list[tuple[str, ...]]:
        return [texts for call_kind, texts in self.calls if call_kind == kind]

    @override
    def confirm(self, title: str, message: str, accept_text: str, reject_text: str) -> bool:
        self.calls.append(("confirm", (title, message, accept_text, reject_text)))
        return self.confirm_answers.pop(0) if self.confirm_answers else self.confirm_answer

    @override
    def choose(self, title: str, message: str, options: tuple[str, ...], cancel_index: int) -> int:
        self.calls.append(("choose", (title, message, *options)))
        return self.choices.pop(0) if self.choices else self.choice

    @override
    def ask_date(self, prompt: DatePrompt) -> date | None:
        self.calls.append(("ask_date", (prompt.title, prompt.label, prompt.accept_text, prompt.reject_text)))
        self.prompts.append(prompt)
        return self.date_answer

    @override
    def inform(self, title: str, message: str, button_text: str) -> None:
        self.calls.append(("inform", (title, message, button_text)))

    @override
    def warn(self, title: str, message: str, button_text: str) -> None:
        self.calls.append(("warn", (title, message, button_text)))

    @override
    def error(self, title: str, message: str, button_text: str) -> None:
        self.calls.append(("error", (title, message, button_text)))
        self.on_error()

    @override
    def choose_open_file(self, title: str, directory: str, name_filter: str) -> str | None:
        self.calls.append(("choose_open_file", (title, directory, name_filter)))
        return self._path()

    @override
    def choose_save_file(self, title: str, directory: str, name_filter: str) -> str | None:
        self.calls.append(("choose_save_file", (title, directory, name_filter)))
        return self._path()

    @override
    def choose_folder(self, title: str, directory: str) -> str | None:
        self.calls.append(("choose_folder", (title, directory)))
        return self.chosen_path

    def _path(self) -> str | None:
        return self.chosen_paths.pop(0) if self.chosen_paths else self.chosen_path
