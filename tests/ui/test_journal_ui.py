import logging

import pytest
from PySide6.QtCore import QModelIndex, QPoint, Qt
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QWidget
from pytestqt.qtbot import QtBot

from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.layout_keys import LAYOUT_JOURNAL_LEVELS
from concentrator.presentation.common.row_tone_enum import RowToneEnum
from concentrator.presentation.common.table_snapshot import TableRowSnapshot
from concentrator.ui.widgets.badge_button import BadgeButton
from concentrator.ui.widgets.snapshot_table_model import SnapshotTableModel
from tests.fakes.journal_stack import DEBOUNCE_MS
from tests.ui.shell_harness import ShellHarness

pytestmark = pytest.mark.ui


def _row(key: int, text: str = "", tone: RowToneEnum = RowToneEnum.NORMAL) -> TableRowSnapshot:
    return TableRowSnapshot(key=key, cells=(f"t{key}", text or f"message {key}"), tone=tone)


class _Signals:
    def __init__(self, model: SnapshotTableModel) -> None:
        self.events: list[str] = []
        self.renamed: list[int] = []
        model.rowsInserted.connect(self._inserted)
        model.rowsRemoved.connect(self._removed)
        model.modelReset.connect(self._reset)
        model.headerDataChanged.connect(self._renamed)

    def _inserted(self, _parent: QModelIndex, _first: int, _last: int) -> None:
        self.events.append("inserted")

    def _removed(self, _parent: QModelIndex, _first: int, _last: int) -> None:
        self.events.append("removed")

    def _reset(self) -> None:
        self.events.append("reset")

    def _renamed(self, _orientation: Qt.Orientation, first: int, _last: int) -> None:
        self.renamed.append(first)


@pytest.fixture
def model(qtbot: QtBot) -> SnapshotTableModel:
    del qtbot
    table = SnapshotTableModel()
    table.set_columns(("Time", "Message"))
    table.set_rows(tuple(_row(key) for key in range(1, 4)))
    return table


def test_appended_rows_are_inserted(model: SnapshotTableModel) -> None:
    signals = _Signals(model)

    reset = model.set_rows((*model.rows, _row(4), _row(5)))

    assert not reset
    assert signals.events == ["inserted"]
    assert model.rowCount() == 5
    assert model.data(model.index(4, 1)) == "message 5"


def test_dropping_the_oldest_rows_removes_them_then_inserts(model: SnapshotTableModel) -> None:
    signals = _Signals(model)

    reset = model.set_rows((*model.rows[2:], _row(4)))

    assert not reset
    assert signals.events == ["removed", "inserted"]
    assert [row.key for row in model.rows] == [3, 4]


def test_other_changes_reset_the_model(model: SnapshotTableModel) -> None:
    signals = _Signals(model)

    assert model.set_rows((_row(1), _row(3)))
    assert model.set_rows((_row(1, "changed"), _row(3)))
    assert model.set_rows(())
    assert signals.events == ["reset", "reset", "reset"]


def test_same_rows_change_nothing(model: SnapshotTableModel) -> None:
    signals = _Signals(model)

    assert not model.set_rows(tuple(_row(key) for key in range(1, 4)))
    assert signals.events == []


def test_columns_renamed_in_place_or_reset_when_their_number_changes(model: SnapshotTableModel) -> None:
    signals = _Signals(model)

    model.set_columns(("Heure", "Message"))
    model.set_columns(("Heure", "Message"))
    model.set_columns(("Heure", "Niveau", "Message"))

    assert signals.renamed == [0]
    assert signals.events == ["reset"]
    assert model.headerData(1, Qt.Orientation.Horizontal) == "Niveau"
    assert model.headerData(9, Qt.Orientation.Horizontal) is None
    assert model.headerData(0, Qt.Orientation.Vertical) is None


def test_missing_cell_is_empty(model: SnapshotTableModel) -> None:
    model.set_columns(("Time", "Message", "Extra"))
    model.set_rows((_row(1),))

    cell = model.data(model.index(0, 2))

    assert isinstance(cell, str)
    assert not cell


def test_tones_set_font_and_color(model: SnapshotTableModel) -> None:
    model.set_rows((_row(1, tone=RowToneEnum.MUTED), _row(2, tone=RowToneEnum.ERROR), _row(3)))

    assert model.data(model.index(0, 0), Qt.ItemDataRole.ForegroundRole) is not None
    font = model.data(model.index(1, 0), Qt.ItemDataRole.FontRole)
    assert isinstance(font, QFont)
    assert font.bold()
    assert model.data(model.index(2, 0), Qt.ItemDataRole.ForegroundRole) is None
    assert model.data(model.index(2, 0), Qt.ItemDataRole.FontRole) is None
    assert model.data(QModelIndex()) is None
    assert model.rowCount(model.index(0, 0)) == 0
    assert model.columnCount(model.index(0, 0)) == 0


def _show_journal(harness: ShellHarness) -> None:
    harness.window.module_bar.button(ActionIdEnum.SHELL_SHOW_JOURNAL).click()
    harness.turn()


def test_journal_page_shows_the_entries_and_follows(qtbot: QtBot) -> None:
    harness = ShellHarness()
    qtbot.addWidget(harness.window)
    harness.journal.feed.log("first")
    harness.journal.feed.log("Save failed", logging.ERROR)

    _show_journal(harness)

    page = harness.window.journal_page
    assert page.table.model.rowCount() == 2
    assert page.table.model.headerData(4, Qt.Orientation.Horizontal) == "en:journal.column.message"
    assert [toggle.text() for toggle in page.toolbar.level_toggles][3] == (
        "en:journal.level.count(level=en:journal.level.error,count=1)"
    )
    assert not page.table.empty_text


def test_level_toggle_and_search_filter_the_table(qtbot: QtBot) -> None:
    harness = ShellHarness()
    qtbot.addWidget(harness.window)
    harness.journal.feed.log("info entry")
    harness.journal.feed.log("timer started", logging.WARNING)
    _show_journal(harness)
    page = harness.window.journal_page

    page.toolbar.level_toggles[1].click()
    harness.turn()
    assert page.table.model.rowCount() == 1
    assert harness.preferences.values[LAYOUT_JOURNAL_LEVELS] == "1,3,4,5"

    harness.scheduler.advance(100)
    page.toolbar.level_toggles[1].click()
    harness.turn()
    page.toolbar.search_box.setText("TIMER")
    harness.scheduler.advance(DEBOUNCE_MS)
    assert page.table.model.rowCount() == 1
    assert page.toolbar.search_box.text() == "TIMER"


def test_selecting_a_row_fills_the_detail_and_ctrl_c_copies(qtbot: QtBot) -> None:
    harness = ShellHarness()
    qtbot.addWidget(harness.window)
    harness.journal.feed.log("first")
    harness.journal.feed.log("second")
    _show_journal(harness)
    page = harness.window.journal_page

    page.table.table.selectRow(1)
    harness.turn()
    assert page.detail.text.endswith("| second")
    shortcut = page.table.table.findChild(QShortcut)
    assert shortcut is not None
    assert shortcut.key() == QKeySequence(QKeySequence.StandardKey.Copy)
    shortcut.activated.emit()
    harness.scheduler.advance(100)

    assert harness.journal.clipboard.texts[-1].endswith("| second")


def test_clear_view_shows_the_empty_text(qtbot: QtBot) -> None:
    harness = ShellHarness()
    qtbot.addWidget(harness.window)
    harness.journal.feed.log("first")
    _show_journal(harness)
    page = harness.window.journal_page

    page.toolbar.buttons()[3].click()
    harness.turn()

    assert page.table.model.rowCount() == 0
    assert page.table.empty_text == "en:journal.empty"


def test_errors_while_hidden_put_a_badge_on_the_journal_button(qtbot: QtBot) -> None:
    harness = ShellHarness()
    qtbot.addWidget(harness.window)
    button = harness.window.module_bar.button(ActionIdEnum.SHELL_SHOW_JOURNAL)
    assert isinstance(button, BadgeButton)

    harness.journal.feed.log("crash", logging.CRITICAL)
    harness.journal_presenter.on_tick()
    harness.turn()
    assert button.badge == "1"
    button.grab()

    _show_journal(harness)
    assert not button.badge


def test_badge_button_paints_without_and_with_a_badge(qtbot: QtBot) -> None:
    parent = QWidget()
    qtbot.addWidget(parent)
    button = BadgeButton(parent)
    button.setText("Journal")
    button.resize(90, 60)

    button.set_badge("")
    empty = button.grab().toImage()
    button.set_badge("99+")
    badged = button.grab().toImage()

    assert empty != badged
    assert button.badge == "99+"


def test_reset_layout_applies_the_default_sizes_at_once(qtbot: QtBot) -> None:
    harness = ShellHarness()
    qtbot.addWidget(harness.window)
    harness.window.restore_layout()
    harness.window.resize(1000, 700)
    harness.window.show()
    qtbot.waitExposed(harness.window)
    header = harness.window.journal_page.table.table.horizontalHeader()
    header.resizeSection(0, 300)

    harness.window.reset_layout()

    assert harness.window.size().toTuple() == (1400, 860)
    assert header.sectionSize(0) == 110
    assert QApplication.instance() is not None
    assert harness.window.mapToGlobal(QPoint(0, 0)) is not None
