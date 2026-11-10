"""Snapshot of a read-only table shown by ``ui.widgets.SnapshotTableModel``."""

from dataclasses import dataclass

from concentrator.presentation.common.row_tone_enum import RowToneEnum


@dataclass(frozen=True, slots=True, kw_only=True)
class TableRowSnapshot:
    """One row.

    Attributes:
        key: Identifies the row among every row the table ever shows (sorting and appending keep it).
        cells: Text of each column.
        tone: Emphasis of the row.
    """

    key: int
    cells: tuple[str, ...]
    tone: RowToneEnum = RowToneEnum.NORMAL


@dataclass(frozen=True, slots=True, kw_only=True)
class TableSnapshot:
    """The whole table.

    Attributes:
        columns: Header texts.
        rows: Rows, in display order.
        selection: Indices of the selected rows.
        scroll_to_end: Whether the last row is kept in view.
        empty_text: Shown instead of the rows when there is none.
    """

    columns: tuple[str, ...]
    rows: tuple[TableRowSnapshot, ...]
    selection: tuple[int, ...] = ()
    scroll_to_end: bool = False
    empty_text: str = ""
