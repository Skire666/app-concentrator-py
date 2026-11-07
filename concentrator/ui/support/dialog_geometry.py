"""Where a dialog may stand inside the main window (ADR-036): pure geometry, no Qt."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Box:
    """A window rectangle in screen coordinates.

    Attributes:
        x: Left edge.
        y: Top edge.
        width: Width.
        height: Height.
    """

    x: int
    y: int
    width: int
    height: int


def _clamped_start(start: int, size: int, host_start: int, host_size: int) -> int:
    """Clamp one axis.

    Args:
        start: Wanted start of the dialog.
        size: Dialog size along the axis.
        host_start: Start of the main window.
        host_size: Main window size along the axis.

    Returns:
        The nearest start that keeps the dialog inside, or the centered start when it is larger.
    """
    if size >= host_size:
        return host_start + (host_size - size) // 2
    return min(max(start, host_start), host_start + host_size - size)


def clamped(dialog: Box, host: Box) -> Box:
    """Move a dialog as little as possible so that it stays inside the main window.

    Args:
        dialog: Wanted dialog rectangle.
        host: Main window rectangle.

    Returns:
        The dialog rectangle, same size, inside the host; centered along an axis where it is larger.
    """
    return Box(
        x=_clamped_start(dialog.x, dialog.width, host.x, host.width),
        y=_clamped_start(dialog.y, dialog.height, host.y, host.height),
        width=dialog.width,
        height=dialog.height,
    )
