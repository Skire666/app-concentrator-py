"""Snapshot of the list tabs (``TODO_TABS``)."""

from dataclasses import dataclass

from concentrator.presentation.common.button_snapshot import ButtonSnapshot


@dataclass(frozen=True, slots=True, kw_only=True)
class TabSnapshot:
    """One tab.

    Attributes:
        list_id: Id sent back when the tab is chosen or its menu is used.
        text: Name, priority badge and number of open tasks (``Work ▲ (3)``).
        tooltip: Priority and description of the list.
        menu: Edit, Move earlier, Move later, Delete (enabled for this list).
    """

    list_id: str
    text: str
    tooltip: str
    menu: tuple[ButtonSnapshot, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class TodoTabsSnapshot:
    """Everything the tab bar shows.

    Attributes:
        tabs: Tabs in display order (priority, then position).
        selected_index: Index of the current tab, ``-1`` when there is none.
        description: Description of the current list, shown under the tabs (``""`` hides it).
        add: The "+" button (``LIST_ADD``).
    """

    tabs: tuple[TabSnapshot, ...]
    selected_index: int
    description: str
    add: ButtonSnapshot
