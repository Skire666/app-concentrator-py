"""Case- and accent-insensitive text search (journal now, TODO lists in phase 6)."""

import unicodedata
from dataclasses import dataclass
from typing import Final, Self

_DECOMPOSED: Final = "NFKD"


def fold(text: str) -> str:
    """Return the form of a text used for comparisons: no accents, no case.

    ``"État"`` and ``"etat"`` give the same text; compatibility characters are decomposed too
    (``"ﬁ"`` gives ``"fi"``).

    Args:
        text: Any text.

    Returns:
        The folded text.
    """
    decomposed = unicodedata.normalize(_DECOMPOSED, text)
    return "".join(char for char in decomposed if not unicodedata.combining(char)).casefold()


@dataclass(frozen=True, slots=True)
class TextSearch:
    """A search query split into folded terms; a text matches when it contains every term.

    Attributes:
        query: The text typed by the user, as typed.
        terms: Its folded words.
    """

    query: str = ""
    terms: tuple[str, ...] = ()

    @classmethod
    def parse(cls, query: str) -> Self:
        """Split a query into terms.

        Args:
            query: Text typed by the user; words are separated by spaces.

        Returns:
            The search; an empty or blank query matches everything.
        """
        return cls(query=query, terms=tuple(fold(query).split()))

    @property
    def is_empty(self) -> bool:
        """Whether the search matches everything."""
        return not self.terms

    def matches(self, folded_text: str) -> bool:
        """Tell whether a text contains every term.

        Args:
            folded_text: Text already passed through ``fold`` (folded once, searched many times).

        Returns:
            Whether every term occurs in it.
        """
        return all(term in folded_text for term in self.terms)
