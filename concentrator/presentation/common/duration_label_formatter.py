"""Short duration labels through the catalog: ``15 min``, ``1 h``, ``1 h 30``, ``1 min 30 s``."""

from typing import Final

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.domain.timer.duration import Duration

_TWO_DIGITS: Final = "02d"
_PART_SEPARATOR: Final = " "


class DurationLabelFormatter:
    """Builds the automatic label of a favorite (the domain stores ``""`` for it)."""

    def __init__(self, translator: TranslatorPort) -> None:
        """Create the formatter.

        Args:
            translator: Current-language templates (``duration.label.*``).
        """
        self._translator = translator

    def label(self, duration: Duration) -> str:
        """Return the short label of a duration.

        Whole minutes read ``15 min``, ``2 h`` or ``1 h 30`` (minutes zero-padded); a duration with
        seconds lists its non-zero parts, for example ``1 min 30 s``.

        Args:
            duration: Duration to describe.

        Returns:
            The label.
        """
        tr = self._translator.tr
        hours, minutes, seconds = duration.hms
        if seconds:
            parts = (
                tr("duration.label.hours", hours=hours) if hours else "",
                tr("duration.label.minutes", minutes=minutes) if minutes else "",
                tr("duration.label.seconds", seconds=seconds),
            )
            return _PART_SEPARATOR.join(part for part in parts if part)
        if not hours:
            return tr("duration.label.minutes", minutes=minutes)
        if not minutes:
            return tr("duration.label.hours", hours=hours)
        return tr("duration.label.hours_minutes", hours=hours, minutes=format(minutes, _TWO_DIGITS))
