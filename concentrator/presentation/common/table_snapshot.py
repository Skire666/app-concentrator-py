"""Snapshot of a read-only table shown by ``ui.widgets.SnapshotTableModel``."""

from dataclasses import dataclass

from concentrator.presentation.common.row_tone_enum import RowToneEnum


@dataclass(frozen=True, slots=True, kw_only=True)
class CellLinkSnapshot:
    """A clickable part of a cell, shown as a hyperlink.

    Attributes:
        column: Column of the cell.
        start: Index of the first character of the link in the cell text.
        end: Index after its last character.
        index: Number sent back when it is clicked.
    """

    column: int
    start: int
    end: int
    index: int


@dataclass(frozen=True, slots=True, kw_only=True)
class TableRowSnapshot:
    """One row.

    Attributes:
        key: Identifies the row among every row the table ever shows (sorting and appending keep it).
        cells: Text of each column.
        tone: Emphasis of the row.
        checked: State of the check box of the ``check_column`` of the table, ``None`` without one.
        check_enabled: Whether a click on that check box is sent back.
        links: Clickable parts of the cells.
        overflow: Drawn after the part of the cell of ``TableSnapshot.overflow_column`` that fits when its
            text is too wide (``... (5 lines)``), ``""`` for none.
        toggle_enabled: Whether a click on the cell of ``TableSnapshot.toggle_column`` is sent back.
    """

    key: int | str
    cells: tuple[str, ...]
    tone: RowToneEnum = RowToneEnum.NORMAL
    checked: bool | None = None
    check_enabled: bool = True
    links: tuple[CellLinkSnapshot, ...] = ()
    overflow: str = ""
    toggle_enabled: bool = False


@dataclass(frozen=True, slots=True, kw_only=True)
class TableSnapshot:
    """The whole table.

    Attributes:
        columns: Header texts.
        rows: Rows, in display order.
        selection: Indices of the selected rows.
        scroll_to_end: Whether the last row is kept in view.
        empty_text: Shown instead of the rows when there is none.
        check_column: Column whose cells carry the check box of the rows, ``-1`` for none.
        sort_column: Column of the sort indicator, ``-1`` for none.
        sort_descending: Direction of the sort indicator.
        hidden_columns: Columns not shown.
        overflow_column: Column whose long texts are cut and followed by the ``overflow`` of their row.
        toggle_column: Column whose cells act as a toggle button (the focus star), ``-1`` for none.
    """

    columns: tuple[str, ...]
    rows: tuple[TableRowSnapshot, ...]
    selection: tuple[int, ...] = ()
    scroll_to_end: bool = False
    empty_text: str = ""
    check_column: int = -1
    sort_column: int = -1
    sort_descending: bool = False
    hidden_columns: tuple[int, ...] = ()
    overflow_column: int = -1
    toggle_column: int = -1
