"""Level toggles and Follow of the journal, kept in ``ui-state.ini`` under ``layout/journal_page/*``.

They are layout keys, so "Reset layout" restores the defaults: every level shown, Follow on. The
search, the pause and "Clear view" last for the session only.
"""

import logging
from typing import Final

from concentrator.domain.settings.log_level_enum import LogLevelEnum
from concentrator.presentation.common.layout_keys import LAYOUT_JOURNAL_FOLLOW, LAYOUT_JOURNAL_LEVELS
from concentrator.presentation.common.layout_state_keeper import LayoutStateKeeper
from concentrator.presentation.journal.journal_filter import JournalFilter

_logger = logging.getLogger(__name__)

LEVEL_SEPARATOR: Final = ","
FOLLOW_ON: Final = "1"
FOLLOW_OFF: Final = "0"


def _levels(text: str) -> frozenset[LogLevelEnum] | None:
    """Read stored level toggles.

    Args:
        text: Comma-separated ``LogLevelEnum`` values (``""`` when every level is hidden).

    Returns:
        The levels, ``None`` when the text is not understood.
    """
    parts = [part.strip() for part in text.split(LEVEL_SEPARATOR) if part.strip()]
    if not all(part.isdigit() for part in parts):
        return None
    levels = frozenset(LogLevelEnum.parse(int(part)) for part in parts)
    return None if any(not level.is_set for level in levels) else levels


class JournalFilterStore:
    """Loads and saves the persisted part of the journal filter."""

    def __init__(self, layout: LayoutStateKeeper) -> None:
        """Create the store.

        Args:
            layout: ``layout/*`` keys of ``ui-state.ini``.
        """
        self._layout = layout

    def load(self) -> JournalFilter:
        """Read the level toggles and Follow; anything missing or not understood takes its default.

        Returns:
            A filter without search, pause or cleared entries.
        """
        default = JournalFilter()
        stored_levels = self._layout.load(LAYOUT_JOURNAL_LEVELS)
        levels = default.levels if stored_levels is None else _levels(stored_levels)
        if levels is None:
            _logger.warning("Stored journal level filter ignored: %r", stored_levels)
            levels = default.levels
        follow = self._layout.load(LAYOUT_JOURNAL_FOLLOW) != FOLLOW_OFF
        return JournalFilter(levels=levels, follow=follow)

    def save(self, journal_filter: JournalFilter) -> None:
        """Store the level toggles and Follow.

        Args:
            journal_filter: Current filter.
        """
        levels = LEVEL_SEPARATOR.join(str(int(level)) for level in sorted(journal_filter.levels))
        self._layout.save(LAYOUT_JOURNAL_LEVELS, levels)
        self._layout.save(LAYOUT_JOURNAL_FOLLOW, FOLLOW_ON if journal_filter.follow else FOLLOW_OFF)
