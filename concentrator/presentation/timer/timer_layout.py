"""Static look of the timer, handed to the ui (which may not import the application layer)."""

from dataclasses import dataclass
from typing import Self

from concentrator.application.common.app_config import UiSection


@dataclass(frozen=True, slots=True, kw_only=True)
class TimerLayout:
    """Font of the timer digits, from ``[ui]`` of ``concentrator.ini``.

    Attributes:
        font_family: ``ui.timer_font_family``.
        font_size_px: ``ui.timer_font_size_px``.
        spacing_px: ``ui.dialog_spacing_px``, also used between the parts of the edit dialog.
    """

    font_family: str
    font_size_px: int
    spacing_px: int

    @classmethod
    def from_ui_section(cls, ui: UiSection) -> Self:
        """Copy the values of the ``[ui]`` section.

        Args:
            ui: Loaded section.

        Returns:
            The layout.
        """
        return cls(
            font_family=ui.timer_font_family, font_size_px=ui.timer_font_size_px, spacing_px=ui.dialog_spacing_px
        )
