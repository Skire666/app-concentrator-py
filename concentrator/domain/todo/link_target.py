"""A link found in the text of a task: a web address or a Windows path."""

from dataclasses import dataclass
from typing import Final, Self

from concentrator.domain.todo.link_kind_enum import LinkKindEnum

WINDOWS_SEPARATOR: Final = "\\"
PATH_SEPARATOR: Final = "/"
_DRIVE_SEPARATOR: Final = ":"
_PATH_KINDS: Final = frozenset({LinkKindEnum.LOCAL_PATH, LinkKindEnum.UNC_PATH})


def flat_path(path: str) -> str:
    r"""Write a Windows path with ``/`` separators (ADR-014): ``C:\Docs`` becomes ``C:/Docs``.

    Args:
        path: Path as typed.

    Returns:
        The path with ``/`` only.
    """
    return path.replace(WINDOWS_SEPARATOR, PATH_SEPARATOR)


@dataclass(frozen=True, slots=True)
class LinkTarget:
    """Normalized link: opened as it is, never checked (ADR-014).

    Attributes:
        kind: Web address, local path or network (UNC) path.
        value: Single line; paths use ``/`` and an upper-case drive letter.
    """

    kind: LinkKindEnum
    value: str

    @classmethod
    def create(cls, kind: LinkKindEnum, text: str) -> Self:
        """Normalize a link as written in a task.

        Args:
            kind: Kind found by ``LinkDetector``.
            text: Link text, one line.

        Returns:
            The target.
        """
        value = text.strip()
        if kind in _PATH_KINDS:
            value = flat_path(value)
        if kind is LinkKindEnum.LOCAL_PATH and value[1:2] == _DRIVE_SEPARATOR:
            value = value[0].upper() + value[1:]
        return cls(kind, value)
