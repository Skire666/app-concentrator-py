"""Static sizes of zone 1 and of the TODO dialogs, from ``concentrator.ini``."""

from dataclasses import dataclass
from typing import Self

from concentrator.application.common.app_config import AppConfig


@dataclass(frozen=True, slots=True, kw_only=True)
class TodoLayout:
    """What the TODO widgets need from the ini (the ui cannot read ``AppConfig``).

    Attributes:
        table_ratio_percent: Initial height share of the task table above the details pane.
        column_widths_px: Default widths of every column but the task column.
        text_width_percent: Share of the task column the text may fill before it is cut.
        spacing_px: Space between the parts of zone 1 and of the dialogs.
    """

    table_ratio_percent: int
    column_widths_px: tuple[int, ...]
    text_width_percent: int
    spacing_px: int

    @classmethod
    def from_config(cls, config: AppConfig) -> Self:
        """Read the ``[todo]`` and ``[ui]`` values.

        Args:
            config: Loaded configuration.

        Returns:
            The layout.
        """
        return cls(
            table_ratio_percent=config.todo.default_table_ratio_percent,
            column_widths_px=config.todo.default_column_widths_px,
            text_width_percent=config.todo.text_width_percent,
            spacing_px=config.ui.dialog_spacing_px,
        )
