"""Scripted dialogs recording what was asked."""

from collections.abc import Callable
from typing import override

from concentrator.presentation.ports.dialog_port import DialogPort


class FakeDialogs(DialogPort):
    """Answers with ``confirm_answer`` and ``chosen_path``; ``on_error`` runs inside ``error``."""

    def __init__(self, *, confirm_answer: bool = True, chosen_path: str | None = None) -> None:
        self.confirm_answer = confirm_answer
        self.chosen_path = chosen_path
        self.calls: list[tuple[str, tuple[str, ...]]] = []
        self.on_error: Callable[[], None] = lambda: None

    @override
    def confirm(self, title: str, message: str, accept_text: str, reject_text: str) -> bool:
        self.calls.append(("confirm", (title, message, accept_text, reject_text)))
        return self.confirm_answer

    @override
    def inform(self, title: str, message: str, button_text: str) -> None:
        self.calls.append(("inform", (title, message, button_text)))

    @override
    def error(self, title: str, message: str, button_text: str) -> None:
        self.calls.append(("error", (title, message, button_text)))
        self.on_error()

    @override
    def choose_open_file(self, title: str, directory: str, name_filter: str) -> str | None:
        self.calls.append(("choose_open_file", (title, directory, name_filter)))
        return self.chosen_path

    @override
    def choose_save_file(self, title: str, directory: str, name_filter: str) -> str | None:
        self.calls.append(("choose_save_file", (title, directory, name_filter)))
        return self.chosen_path

    @override
    def choose_folder(self, title: str, directory: str) -> str | None:
        self.calls.append(("choose_folder", (title, directory)))
        return self.chosen_path
