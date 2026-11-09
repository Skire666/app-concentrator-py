"""Modal edit dialog (timer, favorite, hourly chime), implemented by the ``ui.windows`` edit windows."""

from typing import Protocol


class EditorDialogPort(Protocol):
    """Shows one edit dialog; its panel is registered with the render coordinator under its own section."""

    def show_editor(self) -> None:
        """Render and show the dialog over the main window; return when it closes."""
        ...

    def close_editor(self) -> None:
        """Close the dialog (saved, or cancelled)."""
        ...
