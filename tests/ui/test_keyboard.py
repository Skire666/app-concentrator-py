"""Keyboard use of the dialogs and pages (phase 8): captions bound to their fields, names for screen readers,
a tab order that follows the reading order, Alt and a letter."""

import itertools
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final, cast

import pytest
from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QAbstractButton,
    QAbstractItemView,
    QDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QSplitter,
    QTabBar,
    QWidget,
)
from pytestqt.qtbot import QtBot

from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.button_snapshot import ButtonSnapshot
from concentrator.presentation.journal.journal_snapshot import SearchBoxSnapshot
from concentrator.presentation.timer.timer_layout import TimerLayout
from concentrator.presentation.todo.todo_layout import TodoLayout
from concentrator.ui.support.mnemonics import accessible_name, bind_caption, mnemonic_free, set_caption
from concentrator.ui.support.modal_host import ScreenDialogRunner
from concentrator.ui.widgets.search_box_widget import SearchBoxWidget
from concentrator.ui.widgets.snapshot_button import SnapshotButton
from concentrator.ui.windows.chime_settings_dialog import ChimeSettingsWindow
from concentrator.ui.windows.preset_edit_dialog import PresetEditWindow
from concentrator.ui.windows.timer_edit_dialog import TimerEditWindow
from concentrator.ui.windows.todo_edit_dialogs import ListEditWindow, TaskEditWindow
from tests.fakes.app_config_factory import make_ui_section
from tests.fakes.timer_ui_stack import TimerUiStack
from tests.fakes.todo_factory import WORK_LIST_ID
from tests.fakes.todo_ui_stack import TodoUiStack
from tests.ui.shell_harness import ShellHarness

pytestmark = pytest.mark.ui

TIMER_LAYOUT: Final = TimerLayout.from_ui_section(make_ui_section())
TODO_LAYOUT: Final = TodoLayout(
    table_ratio_percent=75,
    column_widths_px=(60, 40, 120, 140, 130, 50, 50, 140, 140),
    text_width_percent=80,
    spacing_px=10,
)


@dataclass(frozen=True, slots=True)
class Seen:
    """What a dialog showed while it was open."""

    captions: dict[str, str]
    """Caption text to the accessible name of its field (of its focus proxy for a composite field)."""
    backward_steps: list[str]
    """Tab steps that go back up or to the left (empty when the tab order follows the reading order)."""
    unnamed: list[str]
    """Controls Tab reaches that a screen reader cannot name."""


def _tab_chain(root: QWidget) -> list[QWidget]:
    """Widgets that Tab reaches inside ``root``, in order."""
    chain: list[QWidget] = []
    visited: set[int] = set()
    window = root.window()
    current = window.nextInFocusChain()
    while current is not None and current is not window and id(current) not in visited:
        visited.add(id(current))
        reachable = bool(current.focusPolicy().value & Qt.FocusPolicy.TabFocus.value)
        if root.isAncestorOf(current) and reachable and current.isVisibleTo(root) and current.isEnabled():
            chain.append(current)
        current = current.nextInFocusChain()
    return [widget for widget in chain if widget.focusProxy() is None]


def _backward_steps(root: QWidget) -> list[str]:
    steps: list[str] = []
    chain = _tab_chain(root)
    for before, after in itertools.pairwise(chain):
        top_left = before.mapTo(root, QPoint(0, 0))
        next_top_left = after.mapTo(root, QPoint(0, 0))
        same_row = (
            next_top_left.y() < top_left.y() + before.height() and top_left.y() < next_top_left.y() + after.height()
        )
        above = next_top_left.y() + after.height() <= top_left.y()
        if above or (same_row and next_top_left.x() < top_left.x()):
            steps.append(f"{type(before).__name__} -> {type(after).__name__}")
    return steps


CONTAINERS: Final = (QTabBar, QAbstractItemView, QScrollArea)
"""Qt names their tabs, rows and cells itself."""


def _unnamed(root: QWidget) -> list[str]:
    return [
        type(widget).__name__
        for widget in _tab_chain(root)
        if not widget.accessibleName()
        and not isinstance(widget, CONTAINERS)
        and not (isinstance(widget, QAbstractButton) and widget.text())
    ]


def _seen(root: QWidget) -> Seen:
    return Seen(_captions(root), _backward_steps(root), _unnamed(root))


def _captions(root: QWidget) -> dict[str, str]:
    seen: dict[str, str] = {}
    for label in root.findChildren(QLabel):
        buddy = cast("QWidget | None", label.buddy())
        if buddy is None or not label.text():
            continue
        target = buddy.focusProxy() or buddy
        seen[label.text()] = target.accessibleName()
    return seen


def _inspect_then_close(dialog: QDialog, seen: list[Seen]) -> Callable[[], None]:
    def inspect() -> None:
        seen.append(_seen(dialog))
        dialog.reject()

    return inspect


def _assert_keyboard_ready(seen: list[Seen], captions: int) -> None:
    assert len(seen) == 1
    assert len(seen[0].captions) == captions
    assert all(name == mnemonic_free(text) and name for text, name in seen[0].captions.items())
    assert seen[0].backward_steps == []
    assert seen[0].unnamed == []


def test_timer_dialog_is_keyboard_ready(qtbot: QtBot) -> None:
    stack = TimerUiStack(register_editor=False)
    window = TimerEditWindow(stack.editor, stack.renderer, ScreenDialogRunner(), TIMER_LAYOUT)
    qtbot.addWidget(window.dialog)
    stack.editor.attach(window, stack.dialogs)
    seen: list[Seen] = []

    QTimer.singleShot(0, _inspect_then_close(window.dialog, seen))
    stack.click(ActionIdEnum.TIMER_EDIT)

    _assert_keyboard_ready(seen, captions=5)


def test_favorite_dialog_is_keyboard_ready(qtbot: QtBot) -> None:
    stack = TimerUiStack(register_editor=False)
    window = PresetEditWindow(stack.preset_editor, stack.renderer, ScreenDialogRunner(), TIMER_LAYOUT)
    qtbot.addWidget(window.dialog)
    stack.preset_editor.attach(window)
    seen: list[Seen] = []

    QTimer.singleShot(0, _inspect_then_close(window.dialog, seen))
    stack.preset_action(ActionIdEnum.PRESET_ADD)

    _assert_keyboard_ready(seen, captions=2)


def test_chime_dialog_is_keyboard_ready(qtbot: QtBot) -> None:
    stack = TimerUiStack(register_editor=False)
    window = ChimeSettingsWindow(stack.chime_editor, stack.renderer, ScreenDialogRunner(), TIMER_LAYOUT)
    qtbot.addWidget(window.dialog)
    stack.chime_editor.attach(window, stack.dialogs)
    seen: list[Seen] = []

    QTimer.singleShot(0, _inspect_then_close(window.dialog, seen))
    stack.chime_editor.open()

    _assert_keyboard_ready(seen, captions=4)


def test_task_dialog_is_keyboard_ready(qtbot: QtBot) -> None:
    stack = TodoUiStack(register_editors=False)
    window = TaskEditWindow(stack.task_editor, stack.renderer, ScreenDialogRunner(), TODO_LAYOUT)
    qtbot.addWidget(window.dialog)
    stack.task_editor.attach(window, stack.dialogs)
    seen: list[Seen] = []

    QTimer.singleShot(0, _inspect_then_close(window.dialog, seen))
    stack.task_editor.open_new(WORK_LIST_ID)

    _assert_keyboard_ready(seen, captions=4)


def test_list_dialog_is_keyboard_ready(qtbot: QtBot) -> None:
    stack = TodoUiStack(register_editors=False)
    window = ListEditWindow(stack.list_editor, stack.renderer, ScreenDialogRunner(), TODO_LAYOUT)
    qtbot.addWidget(window.dialog)
    stack.list_editor.attach(window, stack.dialogs)
    seen: list[Seen] = []

    QTimer.singleShot(0, _inspect_then_close(window.dialog, seen))
    stack.list_editor.open_new()

    _assert_keyboard_ready(seen, captions=3)


def test_settings_page_is_keyboard_ready(qtbot: QtBot) -> None:
    harness = ShellHarness()
    qtbot.addWidget(harness.window)
    harness.window.show()
    qtbot.waitExposed(harness.window)
    harness.window.module_bar.button(ActionIdEnum.SHELL_SHOW_SETTINGS).click()
    harness.turn()
    page = harness.window.settings_page

    _assert_keyboard_ready([_seen(page)], captions=6)


@pytest.fixture
def shown(qtbot: QtBot) -> ShellHarness:
    harness = ShellHarness()
    qtbot.addWidget(harness.window)
    harness.window.resize(1400, 900)
    harness.window.show()
    qtbot.waitExposed(harness.window)
    return harness


def test_focus_page_zones_are_keyboard_ready(shown: ShellHarness) -> None:
    todo = shown.todo
    for number in range(2):
        assert todo.task_commands.quick_add(WORK_LIST_ID, f"Task {number}").is_success
    shown.turn()
    splitter = shown.window.focus_page.findChildren(QSplitter)[0]

    zones = [_seen(cast("QWidget", splitter.widget(index))) for index in range(splitter.count())]

    assert [(zone.backward_steps, zone.unnamed) for zone in zones] == [([], []), ([], [])]


def test_journal_page_is_keyboard_ready(shown: ShellHarness) -> None:
    shown.window.module_bar.button(ActionIdEnum.SHELL_SHOW_JOURNAL).click()
    shown.turn()

    seen = _seen(shown.window.journal_page)

    assert (seen.backward_steps, seen.unnamed) == ([], [])


def test_module_buttons_are_named_after_their_text(qtbot: QtBot) -> None:
    harness = ShellHarness()
    qtbot.addWidget(harness.window)

    button = harness.window.module_bar.button(ActionIdEnum.SHELL_SHOW_JOURNAL)

    assert button.accessibleName() == mnemonic_free(button.text())
    assert button.accessibleName()


def test_alt_and_the_letter_of_a_caption_focus_its_field(qtbot: QtBot) -> None:
    form = QWidget()
    qtbot.addWidget(form)
    layout = QFormLayout(form)
    fields = (QLineEdit(form), QLineEdit(form))
    for text, field in zip(("&Name", "&Description"), fields, strict=True):
        caption = QLabel(form)
        bind_caption(caption, field)
        set_caption(caption, text)
        layout.addRow(caption, field)
    form.show()
    form.activateWindow()
    qtbot.waitActive(form)
    fields[0].setFocus()
    qtbot.waitUntil(fields[0].hasFocus, timeout=1000)

    QTest.keyClick(fields[0], Qt.Key.Key_D, Qt.KeyboardModifier.AltModifier)

    qtbot.waitUntil(fields[1].hasFocus, timeout=1000)
    assert fields[1].accessibleName() == "Description"


def test_no_scroll_area_is_a_tab_stop(shown: ShellHarness) -> None:
    shown.window.module_bar.button(ActionIdEnum.SHELL_SHOW_SETTINGS).click()
    shown.turn()

    stops = _tab_chain(shown.window.focus_page) + _tab_chain(shown.window.settings_page)

    assert [widget for widget in stops if isinstance(widget, QScrollArea)] == []


def test_a_placeholder_name_keeps_its_ampersand(qtbot: QtBot) -> None:
    box = SearchBoxWidget()
    qtbot.addWidget(box)

    box.apply(SearchBoxSnapshot(text="", placeholder="Tasks & notes", tooltip="Search"))

    assert box.accessibleName() == "Tasks & notes"
    assert accessible_name("Sa&ve", "Tasks & notes") == "Save"


def test_an_icon_button_is_named_after_its_tooltip(qtbot: QtBot) -> None:

    button = SnapshotButton()
    qtbot.addWidget(button)

    button.apply(ButtonSnapshot(text="", tooltip="Remove", enabled=True, visible=True, action=ActionIdEnum.UNSET))

    assert button.accessibleName() == "Remove"
