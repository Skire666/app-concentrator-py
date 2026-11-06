"""Static sizes of the window shell, handed to the ui (which may not import the application layer)."""

from dataclasses import dataclass
from typing import Self

from concentrator.application.common.app_config import UiSection


@dataclass(frozen=True, slots=True, kw_only=True)
class ShellLayout:
    """Sizes from ``[ui]`` of ``concentrator.ini``.

    Attributes:
        module_bar_width_px: Fixed width of the module bar.
        zone1_ratio_percent: Initial share of zone 1 on the Focus page.
        default_width_px: Window width when no layout was saved yet.
        default_height_px: Window height when no layout was saved yet.
        min_width_px: Minimum window width.
        min_height_px: Minimum window height.
    """

    module_bar_width_px: int
    zone1_ratio_percent: int
    default_width_px: int
    default_height_px: int
    min_width_px: int
    min_height_px: int

    @classmethod
    def from_ui_section(cls, ui: UiSection) -> Self:
        """Copy the sizes of the ``[ui]`` section.

        Args:
            ui: Loaded section.

        Returns:
            The layout.
        """
        return cls(
            module_bar_width_px=ui.module_bar_width_px,
            zone1_ratio_percent=ui.zone1_ratio_percent,
            default_width_px=ui.default_window_width_px,
            default_height_px=ui.default_window_height_px,
            min_width_px=ui.min_window_width_px,
            min_height_px=ui.min_window_height_px,
        )
