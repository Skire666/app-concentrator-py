"""Finds the links of the text of a task (ADR-014, owner decision of the phase 6 plan)."""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Final, Self

from concentrator.domain.common.multiline_text import MultilineText
from concentrator.domain.todo.link_kind_enum import LinkKindEnum
from concentrator.domain.todo.link_target import LinkTarget, flat_path

_BULLET: Final = "- "
_SCHEME_SUFFIX: Final = "://"
_DRIVE_PATH: Final = re.compile(r"[A-Za-z]:[\\/]")
_UNC_PATH: Final = re.compile(r"(\\\\|//)[^\\/\s]")


@dataclass(frozen=True, slots=True, kw_only=True)
class DetectedLink:
    """A link and its place in the text.

    Attributes:
        line: Index of the line.
        start: Index of its first character in the line.
        end: Index after its last character.
        target: Normalized target.
    """

    line: int
    start: int
    end: int
    target: LinkTarget


@dataclass(frozen=True, slots=True)
class LinkDetector:
    r"""A link is a whole line, written alone on it (after an optional ``- `` bullet).

    The line starts with a web address of a configured scheme (``https://...``), a drive path (``C:\...``,
    ``d:/...``) or a network path (``\\server\share``, ``//server/share``). Paths may hold spaces; the
    surrounding spaces of the line are not part of the link. Links in the middle of a sentence are plain
    text.

    Attributes:
        url_schemes: Lower-case schemes of the web addresses (``links.url_schemes``).
    """

    url_schemes: tuple[str, ...]

    @classmethod
    def of(cls, url_schemes: Iterable[str]) -> Self:
        """Build a detector.

        Args:
            url_schemes: Schemes, any case.

        Returns:
            The detector.
        """
        return cls(tuple(scheme.strip().lower() for scheme in url_schemes))

    def find(self, text: MultilineText) -> tuple[DetectedLink, ...]:
        """Return the links of a text, in reading order (their index is their number).

        Args:
            text: Text of a task.

        Returns:
            The links.
        """
        found: list[DetectedLink] = []
        for index, line in enumerate(text.lines):
            link = self.find_in_line(line, index)
            if link is not None:
                found.append(link)
        return tuple(found)

    def find_in_line(self, line: str, index: int = 0) -> DetectedLink | None:
        """Return the link a line holds.

        Args:
            line: One line.
            index: Its index in the text.

        Returns:
            The link, ``None`` when the line is not one.
        """
        start = len(line) - len(line.lstrip())
        if line.startswith(_BULLET, start):
            start += len(_BULLET)
        candidate = line[start:].strip()
        kind = self._kind(candidate)
        if kind is LinkKindEnum.UNSET:
            return None
        end = start + len(candidate)
        return DetectedLink(line=index, start=start, end=end, target=LinkTarget.create(kind, candidate))

    def normalized(self, text: MultilineText) -> MultilineText:
        r"""Rewrite the paths of a text with ``/`` (``C:\Docs`` -> ``C:/Docs``); everything else is kept.

        Args:
            text: Text as typed.

        Returns:
            The text to store; idempotent.
        """
        lines = list(text.lines)
        for link in self.find(text):
            if link.target.kind is LinkKindEnum.URL:
                continue
            line = lines[link.line]
            lines[link.line] = line[: link.start] + flat_path(line[link.start : link.end]) + line[link.end :]
        changed = tuple(lines)
        return text if changed == text.lines else MultilineText(changed)

    def _kind(self, candidate: str) -> LinkKindEnum:
        """Tell what a line holds.

        Args:
            candidate: Line without its bullet and surrounding spaces.

        Returns:
            The kind, ``UNSET`` for plain text.
        """
        scheme, separator, rest = candidate.partition(_SCHEME_SUFFIX)
        if separator and rest and scheme.lower() in self.url_schemes:
            return LinkKindEnum.URL
        if _DRIVE_PATH.match(candidate):
            return LinkKindEnum.LOCAL_PATH
        if _UNC_PATH.match(candidate):
            return LinkKindEnum.UNC_PATH
        return LinkKindEnum.UNSET
