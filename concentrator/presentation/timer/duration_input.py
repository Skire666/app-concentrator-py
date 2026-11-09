"""The hours, minutes and seconds field shared by the timer and favorite dialogs."""

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.domain.timer.duration import SECONDS_PER_HOUR, Duration
from concentrator.presentation.timer.timer_edit_snapshot import DurationInputSnapshot


def duration_input(
    translator: TranslatorPort, *, label: str, duration: Duration, max_duration_seconds: int, error: str
) -> DurationInputSnapshot:
    """Describe a duration field.

    Args:
        translator: Current-language translator (unit texts).
        label: Translated field label.
        duration: Duration of the draft.
        max_duration_seconds: ``timer.max_duration_seconds`` (gives the highest hour value).
        error: Inline message, ``""`` when valid.

    Returns:
        The field snapshot.
    """
    tr = translator.tr
    hours, minutes, seconds = duration.hms
    return DurationInputSnapshot(
        label=label,
        hours=hours,
        minutes=minutes,
        seconds=seconds,
        max_hours=max_duration_seconds // SECONDS_PER_HOUR,
        hours_unit=tr("timer.edit.unit.hours"),
        minutes_unit=tr("timer.edit.unit.minutes"),
        seconds_unit=tr("timer.edit.unit.seconds"),
        error=error,
    )
