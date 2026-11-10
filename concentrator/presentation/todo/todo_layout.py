"""Static sizes of zone 1 and of the TODO dialogs, from ``concentrator.ini``."""

from dataclasses import dataclass
from typing import Self

from concentrator.application.common.app_config import AppConfig


@dataclass(frozen=True, slots=True, kw_only=True)
class TodoLayout:
    """What the TODO widgets need from the ini (the ui cannot read ``AppConfig``).

    Attributes:
        table_ratio_percent: Initial height share of the task table above the details pane.
        column_widths_px: Default widths of the state, due, created and updated columns.
        spacing_px: Space between the parts of zone 1 and of the dialogs.
    """

    table_ratio_percent: int
    column_widths_px: tuple[int, ...]
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
            spacing_px=config.ui.dialog_spacing_px,
        )
