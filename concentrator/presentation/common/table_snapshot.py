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
        checked: State of the check box of the ``check_column`` of the table, ``None`` without one.
        check_enabled: Whether a click on that check box is sent back.
    """

    key: int | str
    cells: tuple[str, ...]
    tone: RowToneEnum = RowToneEnum.NORMAL
    checked: bool | None = None
    check_enabled: bool = True


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
    """

    columns: tuple[str, ...]
    rows: tuple[TableRowSnapshot, ...]
    selection: tuple[int, ...] = ()
    scroll_to_end: bool = False
    empty_text: str = ""
    check_column: int = -1
    sort_column: int = -1
    sort_descending: bool = False
