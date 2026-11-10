"""Clipboard and folder opener fakes recording what they were given."""

from pathlib import Path
from typing import override

from concentrator.application.ports.link_opener_port import LinkOpenerPort
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.presentation.ports.clipboard_port import ClipboardPort


class FakeClipboard(ClipboardPort):
    def __init__(self) -> None:
        self.texts: list[str] = []

    @override
    def set_text(self, text: str) -> None:
        self.texts.append(text)


class FakeLinkOpener(LinkOpenerPort):
    """``result`` is returned by every call."""

    def __init__(self) -> None:
        self.opened: list[tuple[Path, bool]] = []
        self.result = ValidationResult.success()

    @override
    def open_folder(self, path: Path, *, create_missing: bool = False) -> ValidationResult:
        self.opened.append((path, create_missing))
        return self.result
