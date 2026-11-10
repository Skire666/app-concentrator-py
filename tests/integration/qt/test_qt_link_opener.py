import logging
from pathlib import Path

import pytest
from PySide6.QtCore import QUrl

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.severity_enum import SeverityEnum
from concentrator.infrastructure.qt.qt_link_opener import QtLinkOpener


class _Shell:
    def __init__(self, *, accept: bool = True) -> None:
        self.accept = accept
        self.urls: list[QUrl] = []

    def open_url(self, url: QUrl) -> bool:
        self.urls.append(url)
        return self.accept


def test_open_folder_hands_a_local_file_url_to_the_shell(tmp_path: Path) -> None:
    shell = _Shell()

    result = QtLinkOpener(shell.open_url).open_folder(tmp_path)

    assert result.is_success
    assert [Path(url.toLocalFile()) for url in shell.urls] == [tmp_path]


def test_missing_folder_is_created_only_when_asked(tmp_path: Path) -> None:
    shell = _Shell()
    opener = QtLinkOpener(shell.open_url)
    missing = tmp_path / "logs" / "nested"

    opener.open_folder(missing)
    assert not missing.exists()

    assert opener.open_folder(missing, create_missing=True).is_success
    assert missing.is_dir()


def test_refusal_is_a_logged_warning(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        result = QtLinkOpener(_Shell(accept=False).open_url).open_folder(tmp_path)

    assert result.error_codes == (ErrorCodeEnum.LINK_OPEN_FAILED,)
    assert result.severity is SeverityEnum.WARNING
    assert not result.is_failure
    assert "refused" in caplog.text


def test_folder_that_cannot_be_created_is_not_opened(tmp_path: Path) -> None:
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    shell = _Shell()

    result = QtLinkOpener(shell.open_url).open_folder(blocker / "logs", create_missing=True)

    assert result.error_codes == (ErrorCodeEnum.LINK_OPEN_FAILED,)
    assert shell.urls == []
