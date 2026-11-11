import logging
from pathlib import Path

import pytest
from PySide6.QtCore import QUrl

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.severity_enum import SeverityEnum
from concentrator.domain.todo.link_kind_enum import LinkKindEnum
from concentrator.domain.todo.link_target import LinkTarget
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


@pytest.mark.parametrize(
    ("target", "expected"),
    [
        (LinkTarget(LinkKindEnum.URL, "https://example.org/a?b=1"), "https://example.org/a?b=1"),
        (LinkTarget(LinkKindEnum.LOCAL_PATH, "Z:/Does/Not/Exist/My folder"), "file:///Z:/Does/Not/Exist/My folder"),
        (LinkTarget(LinkKindEnum.UNC_PATH, "//nas/share/projects"), "file://nas/share/projects"),
    ],
)
def test_open_hands_the_target_to_the_shell_without_checking_it(target: LinkTarget, expected: str) -> None:
    shell = _Shell()

    result = QtLinkOpener(shell.open_url).open(target)

    assert result.is_success
    assert [url.toString() for url in shell.urls] == [expected]


def test_a_refused_link_is_a_warning_logged_without_the_link(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG):
        result = QtLinkOpener(_Shell(accept=False).open_url).open(LinkTarget(LinkKindEnum.URL, "https://secret.org"))

    assert result.error_codes == (ErrorCodeEnum.LINK_OPEN_FAILED,)
    assert result.severity is SeverityEnum.WARNING
    assert "refused to open a link (URL)" in caplog.text
    assert "secret" not in caplog.text


def test_an_invalid_url_is_not_handed_to_the_shell() -> None:
    shell = _Shell()

    result = QtLinkOpener(shell.open_url).open(LinkTarget(LinkKindEnum.URL, "http://exa mple.org:99999"))

    assert result.error_codes == (ErrorCodeEnum.LINK_OPEN_FAILED,)
    assert shell.urls == []
