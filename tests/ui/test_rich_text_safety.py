"""User text that looks like HTML is shown as typed everywhere in the window (phase 8 security audit)."""

from typing import Final

import pytest
from PySide6.QtCore import QAbstractItemModel, QAbstractListModel, QModelIndex, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QAbstractItemView, QComboBox, QLabel, QMenu, QTabBar, QWidget
from pytestqt.qtbot import QtBot

from concentrator.application.todo.task_list_commands import ListValues
from concentrator.domain.common.multiline_text import MultilineText
from concentrator.domain.todo.priority_enum import PriorityEnum
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from tests.fakes.todo_factory import WORK_LIST_ID
from tests.ui.shell_harness import ShellHarness

pytestmark = pytest.mark.ui

MARKUP: Final = "<b>bold</b>"
"""Raw markup: found unescaped in a label shown as rich text or in a tooltip, it would be interpreted."""


def _seed_hostile_texts(harness: ShellHarness) -> None:
    todo = harness.todo
    listed = todo.list_commands.create(
        ListValues(name=f"List {MARKUP}", description=MultilineText((f"About {MARKUP}",)), priority=PriorityEnum.HIGH)
    )
    assert listed.is_success
    task = todo.task_commands.quick_add(WORK_LIST_ID, f"Task {MARKUP} & <i>more</i>").data
    assert task is not None
    assert todo.focus.commands.add_tasks((task.id,)).is_success
    harness.turn()
    todo.table.on_selection_changed((task.id,))
    harness.stack.renderer.request(RenderSectionEnum.TODO_DETAILS, RenderSectionEnum.TODO_HISTORY)
    harness.turn()


def _model_tooltips(model: QAbstractItemModel) -> list[str]:
    return [
        str(model.data(model.index(row, column), Qt.ItemDataRole.ToolTipRole) or "")
        for row in range(model.rowCount(QModelIndex()))
        for column in range(1 if isinstance(model, QAbstractListModel) else model.columnCount(QModelIndex()))
    ]


def _widget_texts(widget: QWidget) -> list[str]:
    texts = [widget.toolTip()]
    if isinstance(widget, QLabel) and widget.textFormat() is not Qt.TextFormat.PlainText:
        texts.append(widget.text())
    if isinstance(widget, QTabBar):
        texts.extend(widget.tabToolTip(index) for index in range(widget.count()))
    if isinstance(widget, QComboBox):
        texts.extend(_model_tooltips(widget.model()))
    if isinstance(widget, QAbstractItemView):
        texts.extend(_model_tooltips(widget.model()))
    return texts


def _interpreted_markup(root: QWidget) -> list[str]:
    widgets = [root, *root.findChildren(QWidget)]
    found = [
        f"{type(widget).__name__}: {text!r}" for widget in widgets for text in _widget_texts(widget) if MARKUP in text
    ]
    found += [f"QAction: {action.toolTip()!r}" for action in root.findChildren(QAction) if _shows_markup(action)]
    return found


def _shows_markup(action: QAction) -> bool:
    """A menu item shows its tooltip only when set explicitly or when its menu shows tooltips.

    Without an explicit tooltip, ``toolTip()`` returns the item text, which a menu shows as plain text.
    """
    if MARKUP not in action.toolTip():
        return False
    explicit = action.toolTip() != action.text().replace("&&", "&")
    shown = any(isinstance(owner, QMenu) and owner.toolTipsVisible() for owner in action.associatedObjects())
    return explicit or shown


def test_hostile_texts_reach_the_window(qtbot: QtBot) -> None:
    harness = ShellHarness()
    qtbot.addWidget(harness.window)

    _seed_hostile_texts(harness)

    tabs = [bar.tabText(index) for bar in harness.window.findChildren(QTabBar) for index in range(bar.count())]
    plain = [label.text() for label in harness.window.findChildren(QLabel)]
    assert any(MARKUP in text for text in tabs)
    assert any(MARKUP in text for text in plain)


def test_no_label_or_tooltip_interprets_user_markup(qtbot: QtBot) -> None:
    harness = ShellHarness()
    qtbot.addWidget(harness.window)
    _seed_hostile_texts(harness)

    assert _interpreted_markup(harness.window) == []


def test_the_audit_finds_a_label_shown_as_rich_text(qtbot: QtBot) -> None:
    harness = ShellHarness()
    qtbot.addWidget(harness.window)

    QLabel(f"Task {MARKUP}", harness.window)

    assert _interpreted_markup(harness.window) == [f"QLabel: 'Task {MARKUP}'"]
