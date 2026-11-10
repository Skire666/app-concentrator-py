"""Static sizes of the journal page, handed to the ui (which may not import the application layer)."""

from dataclasses import dataclass
from typing import Self

from concentrator.application.common.app_config import JournalSection


@dataclass(frozen=True, slots=True, kw_only=True)
class JournalLayout:
    """Sizes from ``[journal]`` of ``concentrator.ini``.

    Attributes:
        table_ratio_percent: Initial height share of the table above the detail pane.
        column_widths_px: Initial widths of the time, level, source and thread columns.
    """

    table_ratio_percent: int
    column_widths_px: tuple[int, ...]

    @classmethod
    def from_journal_section(cls, journal: JournalSection) -> Self:
        """Copy the sizes of the ``[journal]`` section.

        Args:
            journal: Loaded section.

        Returns:
            The layout.
        """
        return cls(
            table_ratio_percent=journal.default_table_ratio_percent, column_widths_px=journal.default_column_widths_px
        )
