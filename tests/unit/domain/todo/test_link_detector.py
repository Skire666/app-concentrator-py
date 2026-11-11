import pytest

from concentrator.domain.common.multiline_text import MultilineText
from concentrator.domain.todo.link_detector import DetectedLink, LinkDetector
from concentrator.domain.todo.link_kind_enum import LinkKindEnum
from concentrator.domain.todo.link_target import LinkTarget

DETECTOR = LinkDetector.of(("http", "HTTPS"))


def _targets(*lines: str) -> list[LinkTarget]:
    return [link.target for link in DETECTOR.find(MultilineText(lines))]


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("https://example.org/backup-guide", LinkTarget(LinkKindEnum.URL, "https://example.org/backup-guide")),
        ("HTTP://Example.org/A?b=1", LinkTarget(LinkKindEnum.URL, "HTTP://Example.org/A?b=1")),
        ("https://example.org/page.", LinkTarget(LinkKindEnum.URL, "https://example.org/page.")),
        (r"C:\Users\me\Documents\My folder", LinkTarget(LinkKindEnum.LOCAL_PATH, "C:/Users/me/Documents/My folder")),
        ("d:/Projects/Concentrator", LinkTarget(LinkKindEnum.LOCAL_PATH, "D:/Projects/Concentrator")),
        (r"E:\notes.txt", LinkTarget(LinkKindEnum.LOCAL_PATH, "E:/notes.txt")),
        (r"\\nas\backup\projects", LinkTarget(LinkKindEnum.UNC_PATH, "//nas/backup/projects")),
        ("//nas/backup/projects", LinkTarget(LinkKindEnum.UNC_PATH, "//nas/backup/projects")),
        ("  - C:/Windows/notepad.exe  ", LinkTarget(LinkKindEnum.LOCAL_PATH, "C:/Windows/notepad.exe")),
    ],
)
def test_a_line_holding_only_a_link_is_detected(line: str, expected: LinkTarget) -> None:
    assert _targets(line) == [expected]


@pytest.mark.parametrize(
    "line",
    [
        "See https://example.org/backup-guide",
        r"Copy D:\Projects to the NAS",
        "ratio 3:2",
        "Meeting at 10:30",
        "Note: bring the folder",
        "ftp://example.org/file",
        "file:///C:/Users",
        "https://",
        "C:",
        "C:folder",
        "///nas",
        '"C:/My folder"',
        "",
    ],
)
def test_other_lines_are_plain_text(line: str) -> None:
    assert _targets(line) == []


def test_links_are_numbered_in_reading_order_with_their_place() -> None:
    text = MultilineText(("Weekly backup", "- D:/Projects", "https://example.org"))

    assert DETECTOR.find(text) == (
        DetectedLink(line=1, start=2, end=13, target=LinkTarget(LinkKindEnum.LOCAL_PATH, "D:/Projects")),
        DetectedLink(line=2, start=0, end=19, target=LinkTarget(LinkKindEnum.URL, "https://example.org")),
    )


def test_normalized_rewrites_backslashes_of_paths_only() -> None:
    text = MultilineText((r"Copy C:\a to \\nas\b", r"  - C:\Users\me\My folder", r"\\nas\share", r"https://x.org/a\b"))

    normalized = DETECTOR.normalized(text)

    assert normalized.lines == (
        r"Copy C:\a to \\nas\b",
        "  - C:/Users/me/My folder",
        "//nas/share",
        r"https://x.org/a\b",
    )
    assert DETECTOR.normalized(normalized) is normalized


def test_normalized_keeps_a_text_without_paths() -> None:
    text = MultilineText(("Plain", "https://example.org"))

    assert DETECTOR.normalized(text) is text
