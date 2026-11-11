"""Keys of the layout blobs stored in ``ui-state.ini`` through ``LayoutStateKeeper``.

Every layout key starts with ``layout/`` so that "Reset layout" (phase 4) can remove ``layout/*`` and
nothing else; other UI state, such as ``storage/data_file_path``, never uses this prefix.
"""

from typing import Final

LAYOUT_GROUP: Final = "layout"
LAYOUT_PREFIX: Final = f"{LAYOUT_GROUP}/"
LAYOUT_MAIN_WINDOW_GEOMETRY: Final = "layout/main_window/geometry"
LAYOUT_FOCUS_PAGE_SPLITTER: Final = "layout/focus_page/splitter"
LAYOUT_JOURNAL_SPLITTER: Final = "layout/journal_page/splitter"
LAYOUT_JOURNAL_HEADER: Final = "layout/journal_page/header"
LAYOUT_JOURNAL_LEVELS: Final = "layout/journal_page/levels"
LAYOUT_JOURNAL_FOLLOW: Final = "layout/journal_page/follow"
LAYOUT_TODO_SPLITTER: Final = "layout/focus_page/todo_splitter"
LAYOUT_TODO_HEADER: Final = "layout/focus_page/todo_header_v3"
LAYOUT_TODO_LIST: Final = "layout/todo/list"
LAYOUT_TODO_SORT: Final = "layout/todo/sort"
LAYOUT_TODO_SORT_DESCENDING: Final = "layout/todo/sort_descending"
LAYOUT_TODO_SHOW_DONE: Final = "layout/todo/show_done"
LAYOUT_TODO_SHOW_ARCHIVED: Final = "layout/todo/show_archived"
LAYOUT_TODO_DUE_FILTER: Final = "layout/todo/due_filter"
LAYOUT_TODO_RECURRING_ONLY: Final = "layout/todo/recurring_only"
LAYOUT_TODO_SCOPE: Final = "layout/todo/scope"
LAYOUT_TODO_SEARCH: Final = "layout/todo/search"
