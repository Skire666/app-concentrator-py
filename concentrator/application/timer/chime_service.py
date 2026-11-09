"""Plays the hourly chime, driven by ``AppTicker``."""

import logging
from collections.abc import Callable
from datetime import date
from typing import Final

from concentrator.application.ports.clock_port import ClockPort
from concentrator.application.ports.sound_catalog_port import SoundCatalogPort
from concentrator.application.ports.sound_player_port import SoundPlayback, SoundPlayerPort
from concentrator.application.timer.chime_queries import ChimeQueries
from concentrator.application.timer.sound_candidates import sound_candidates
from concentrator.domain.timer.duration import SECONDS_PER_MINUTE

_logger = logging.getLogger(__name__)

CHIME_PURPOSE: Final = "Chime"
CHIME_LOOPS: Final = 1


class ChimeService:
    """Chimes once at each full hour ``H:00`` local time while the chime is on and ``H`` is active.

    A tick chimes when the local time is at most ``chime.trigger_window_seconds`` after ``H:00:00`` and
    this local (date, hour) has not been handled yet; a later tick never catches a missed hour up. The
    hour handled last is the only one remembered: when the clocks go back, the repeated hour has the
    same (date, hour) and does not chime twice. While the timer rings the hour is skipped (INFO), and
    the chime has its own player, so it never cuts an alarm.
    """

    def __init__(
        self,
        *,
        clock: ClockPort,
        queries: ChimeQueries,
        ringing: Callable[[], bool],
        player: SoundPlayerPort,
        catalog: SoundCatalogPort,
        window_seconds: int,
    ) -> None:
        """Create the service.

        Args:
            clock: Local wall-clock time.
            queries: Switch and settings of the chime.
            ringing: Tells whether the timer alarm rings.
            player: Chime player instance.
            catalog: Finds the sound files.
            window_seconds: ``chime.trigger_window_seconds``.
        """
        self._clock = clock
        self._queries = queries
        self._ringing = ringing
        self._player = player
        self._catalog = catalog
        self._window_seconds = window_seconds
        self._handled: tuple[date, int] | None = None

    def tick(self) -> None:
        """Chime if a full hour has just started (called every ``timer.tick_interval_ms``)."""
        now = self._clock.now_local()
        if now.minute * SECONDS_PER_MINUTE + now.second > self._window_seconds:
            return
        hour = (now.date(), now.hour)
        if hour == self._handled or not self._queries.enabled():
            return
        settings = self._queries.settings()
        if not settings.covers(now.hour):
            return
        self._handled = hour
        if self._ringing():
            _logger.info("Hourly chime of %02d:00 skipped: the timer is ringing", now.hour)
            return
        paths = sound_candidates(self._catalog, settings.sound, self._queries.defaults.fallback_sound, CHIME_PURPOSE)
        played = self._player.play(SoundPlayback(paths=paths, volume=settings.volume, loops=CHIME_LOOPS))
        if played.is_failure:
            _logger.warning("Hourly chime not played: %s", [code.name for code in played.error_codes])
            return
        _logger.info("Hourly chime of %02d:00 played", now.hour)
