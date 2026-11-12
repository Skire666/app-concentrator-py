"""Tab order of widgets created after their panel (phase 8): they belong where they show, not at the end."""

from collections.abc import Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget


def _is_moved(candidate: QWidget, widgets: Sequence[QWidget]) -> bool:
    """Tell whether a widget is one of the moved widgets or inside one of them.

    Args:
        candidate: Widget of the focus chain.
        widgets: Widgets being inserted.

    Returns:
        Whether it moves with them.
    """
    return any(candidate is widget or widget.isAncestorOf(candidate) for widget in widgets)


def _preceding(anchor: QWidget, widgets: Sequence[QWidget]) -> QWidget | None:
    """Find the widget the inserted ones must follow.

    ``QWidget.setTabOrder(first, second)`` puts ``second`` after ``first`` and all its descendants, and does
    nothing when either takes no focus: the containers of the anchor (which hold the inserted widgets too) and
    the widgets without focus (labels) are skipped.

    Args:
        anchor: Widget that follows the inserted ones on screen.
        widgets: Widgets being inserted.

    Returns:
        The last focusable widget before the anchor that is neither one of its containers nor a moved widget.
    """
    previous = anchor.previousInFocusChain()
    while previous is not None and previous is not anchor:
        focusable = previous.focusPolicy() != Qt.FocusPolicy.NoFocus
        if focusable and not previous.isAncestorOf(anchor) and not _is_moved(previous, widgets):
            return previous
        previous = previous.previousInFocusChain()
    return None


def insert_after(anchor: QWidget, widgets: Sequence[QWidget]) -> None:
    """Put widgets, in this order, right after ``anchor`` (and its descendants) in the Tab order.

    Use it when the widget shown before the new ones takes the focus; ``insert_before`` otherwise.

    Args:
        anchor: Focusable widget shown just before the inserted ones.
        widgets: Widgets to insert, in reading order.
    """
    previous = anchor
    for widget in widgets:
        QWidget.setTabOrder(previous, widget)
        previous = widget


def insert_before(anchor: QWidget, widgets: Sequence[QWidget]) -> None:
    """Put widgets, in this order, just before ``anchor`` in the Tab order of their window.

    A widget created by a render joins the end of the focus chain; this moves it back next to the widgets
    shown around it.

    Args:
        anchor: Widget that follows the inserted ones on screen.
        widgets: Widgets to insert, in reading order.
    """
    previous = _preceding(anchor, widgets)
    for widget in (*widgets, anchor):
        if previous is not None:
            QWidget.setTabOrder(previous, widget)
        previous = widget
