"""Timer display text."""

from concentrator.domain.timer.duration import Duration


def clock_text(seconds: int) -> str:
    """Format a number of seconds for the timer display.

    Args:
        seconds: Displayed value.

    Returns:
        ``HH:MM:SS``, always with two-digit parts (a monospaced font keeps the width steady).
    """
    return Duration(max(0, seconds)).as_clock_text()
