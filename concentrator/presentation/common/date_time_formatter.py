"""Dates and times through the catalog templates (``AGENTS.md`` section 9).

Day, month, hour, minute and second are zero-padded before they fill the templates, so a French date
reads ``06/11/2026``, never ``6/11/2026``. The ``locale`` module is not used.
"""

from datetime import datetime
from typing import Final

from concentrator.application.ports.clock_port import ClockPort
from concentrator.application.ports.translator_port import TranslatorPort

_TWO_DIGITS: Final = "02d"
_FOUR_DIGITS: Final = "04d"


class DateTimeFormatter:
    """Formats instants in local time with the current language's templates."""

    def __init__(self, translator: TranslatorPort, clock: ClockPort) -> None:
        """Create the formatter.

        Args:
            translator: Current-language templates (``format.*``).
            clock: Converts instants to local time.
        """
        self._translator = translator
        self._clock = clock

    def time(self, moment: datetime) -> str:
        """Local time without seconds, for example ``17:52``.

        Args:
            moment: Timezone-aware instant.

        Returns:
            The text.
        """
        local = self._clock.to_local(moment)
        return self._translator.tr(
            "format.time", hour=format(local.hour, _TWO_DIGITS), minute=format(local.minute, _TWO_DIGITS)
        )

    def time_with_seconds(self, moment: datetime) -> str:
        """Local time with seconds, for example ``17:44:03``.

        Args:
            moment: Timezone-aware instant.

        Returns:
            The text.
        """
        local = self._clock.to_local(moment)
        return self._translator.tr(
            "format.time_with_seconds",
            hour=format(local.hour, _TWO_DIGITS),
            minute=format(local.minute, _TWO_DIGITS),
            second=format(local.second, _TWO_DIGITS),
        )

    def date(self, moment: datetime) -> str:
        """Local date, for example ``06/11/2026`` in French.

        Args:
            moment: Timezone-aware instant.

        Returns:
            The text.
        """
        local = self._clock.to_local(moment)
        return self._translator.tr(
            "format.date",
            day=format(local.day, _TWO_DIGITS),
            month=format(local.month, _TWO_DIGITS),
            year=format(local.year, _FOUR_DIGITS),
        )

    def date_time(self, moment: datetime) -> str:
        """Local date and time with seconds.

        Args:
            moment: Timezone-aware instant.

        Returns:
            The text.
        """
        return self._translator.tr("format.datetime", date=self.date(moment), time=self.time_with_seconds(moment))
