"""Builds the context menu of the task table from a ``TaskMenuSnapshot``."""

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial

from PySide6.QtWidgets import QMenu, QWidget

from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.todo.task_menu_snapshot import TaskMenuSnapshot
from concentrator.ui.support.plain_text import without_mnemonic


@dataclass(frozen=True, slots=True)
class TaskMenuIntents:
    """What the entries of the menu send.

    Attributes:
        action: Sends an action value (task actions).
        move: Sends a target list id ("Move to list").
        link: Sends the number of a link ("Open link").
    """

    action: Callable[[int], None]
    move: Callable[[str], None]
    link: Callable[[int], None]


def build_task_menu(parent: QWidget, snapshot: TaskMenuSnapshot, intents: TaskMenuIntents) -> QMenu:
    """Create the context menu: the task actions, "Move to list" and "Open link" submenus.

    Args:
        parent: Owner of the menu.
        snapshot: Task actions of the last render.
        intents: Receivers of the entries.

    Returns:
        The menu, not shown yet.
    """
    menu = QMenu(parent)
    for button in snapshot.buttons:
        if button.action is ActionIdEnum.TASK_MOVE:
            _add_move_menu(menu, snapshot, intents, enabled=button.enabled)
            continue
        entry = menu.addAction(button.text)
        entry.setToolTip(button.tooltip)
        entry.setEnabled(button.enabled)
        entry.triggered.connect(partial(intents.action, int(button.action)))
    _add_link_menu(menu, snapshot, intents)
    return menu


def _add_move_menu(menu: QMenu, snapshot: TaskMenuSnapshot, intents: TaskMenuIntents, *, enabled: bool) -> None:
    """Add the "Move to list" submenu.

    Args:
        menu: Context menu.
        snapshot: Task actions (the label of ``TASK_MOVE`` and the target lists).
        intents: Receivers of the entries.
        enabled: Whether moving is possible.
    """
    label = next(button.text for button in snapshot.buttons if button.action is ActionIdEnum.TASK_MOVE)
    submenu = menu.addMenu(label)
    submenu.setEnabled(enabled)
    for target in snapshot.move_targets:
        entry = submenu.addAction(without_mnemonic(target.text))
        entry.setEnabled(target.enabled)
        entry.triggered.connect(partial(intents.move, target.list_id))


def _add_link_menu(menu: QMenu, snapshot: TaskMenuSnapshot, intents: TaskMenuIntents) -> None:
    """Add the "Open link" submenu with the links of the selected task.

    Args:
        menu: Context menu.
        snapshot: Task actions and links.
        intents: Receivers of the entries.
    """
    button = snapshot.open_link
    if button is None:
        return
    submenu = menu.addMenu(button.text)
    submenu.setToolTip(button.tooltip)
    submenu.setEnabled(button.enabled)
    for link in snapshot.links:
        entry = submenu.addAction(without_mnemonic(link.text))
        entry.triggered.connect(partial(intents.link, link.index))
