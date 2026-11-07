"""Sizes of the first-run and recovery dialogs, handed to the ui (which may not import the application)."""

from dataclasses import dataclass
from typing import Self

from concentrator.application.common.app_config import UiSection


@dataclass(frozen=True, slots=True, kw_only=True)
class StartupDialogLayout:
    """Sizes from ``[ui]`` of ``concentrator.ini``.

    Attributes:
        min_width_px: Minimum width of the first-run and recovery dialogs.
        spacing_px: Space between the parts of a dialog.
    """

    min_width_px: int
    spacing_px: int

    @classmethod
    def from_ui_section(cls, ui: UiSection) -> Self:
        """Copy the sizes of the ``[ui]`` section.

        Args:
            ui: Loaded section.

        Returns:
            The layout.
        """
        return cls(min_width_px=ui.startup_dialog_min_width_px, spacing_px=ui.dialog_spacing_px)
