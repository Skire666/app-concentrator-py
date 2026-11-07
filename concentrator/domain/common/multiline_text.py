"""Multi-line text value object (task text, notes): stored as a tuple of lines."""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Final, Self

_LINE_BREAK: Final = re.compile(r"\r\n|\r|\n")
_LINE_SEPARATOR: Final = "\n"


@dataclass(frozen=True, slots=True)
class MultilineText:
    """Normalized multi-line text: no trailing whitespace per line, no blank first or last line.

    Use ``from_text`` or ``from_lines`` to build a normalized value; the constructor keeps the lines
    as given.

    Attributes:
        lines: The lines, without line break characters.
    """

    lines: tuple[str, ...] = ()

    @classmethod
    def from_text(cls, text: str) -> Self:
        r"""Split and normalize a text.

        Lines are split on ``\r\n``, ``\n`` and ``\r``; trailing whitespace is stripped from every
        line; leading and trailing blank lines are removed (blank lines inside the text are kept).

        Args:
            text: Raw text, for example from an editor.

        Returns:
            The normalized value; empty when the text is blank.
        """
        lines = [line.rstrip() for line in _LINE_BREAK.split(text)]
        first = next((position for position, line in enumerate(lines) if line), len(lines))
        last = next((position for position in range(len(lines) - 1, -1, -1) if lines[position]), -1)
        return cls(tuple(lines[first : last + 1]))

    @classmethod
    def from_lines(cls, lines: Iterable[str]) -> Self:
        """Normalize lines read from storage (a line may itself contain line breaks).

        Args:
            lines: Raw lines.

        Returns:
            The normalized value.
        """
        return cls.from_text(_LINE_SEPARATOR.join(lines))

    def as_text(self) -> str:
        r"""Join the lines with ``\n``.

        Returns:
            The text, ``""`` when blank.
        """
        return _LINE_SEPARATOR.join(self.lines)

    @property
    def first_line(self) -> str:
        """First line, ``""`` when blank."""
        return self.lines[0] if self.lines else ""

    @property
    def is_blank(self) -> bool:
        """Whether there is no non-blank line."""
        return not any(self.lines)

    @property
    def line_count(self) -> int:
        """Number of lines."""
        return len(self.lines)
