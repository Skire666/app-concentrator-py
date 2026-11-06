"""Keys of the layout blobs stored in ``ui-state.ini`` through ``LayoutStateKeeper``.

Every layout key starts with ``layout/`` so that "Reset layout" (phase 4) can remove ``layout/*`` and
nothing else; other UI state, such as ``storage/data_file_path``, never uses this prefix.
"""

from typing import Final

LAYOUT_PREFIX: Final = "layout/"
LAYOUT_MAIN_WINDOW_GEOMETRY: Final = "layout/main_window/geometry"
LAYOUT_FOCUS_PAGE_SPLITTER: Final = "layout/focus_page/splitter"
