"""Full hours of the hourly chime as catalog times (``08:00``)."""

from typing import Final

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.domain.timer.hourly_chime_rules import FIRST_HOUR, LAST_HOUR

_TWO_DIGITS: Final = "02d"
_FULL_HOUR_MINUTE: Final = "00"


def hour_text(translator: TranslatorPort, hour: int) -> str:
    """Return a full hour with the ``format.time`` template, hour zero-padded.

    Args:
        translator: Current-language translator.
        hour: Hour (0-23).

    Returns:
        The text, for example ``08:00``.
    """
    return translator.tr("format.time", hour=format(hour, _TWO_DIGITS), minute=_FULL_HOUR_MINUTE)


def hour_options(translator: TranslatorPort) -> tuple[str, ...]:
    """Return every hour of a day, for the hour lists of the chime dialog.

    Args:
        translator: Current-language translator.

    Returns:
        ``00:00`` to ``23:00``; the index of an option is its hour.
    """
    return tuple(hour_text(translator, hour) for hour in range(FIRST_HOUR, LAST_HOUR + 1))
