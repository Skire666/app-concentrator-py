"""Starts and stops the alarm when the timer rings, and draws the user's attention."""

import logging
from collections.abc import Callable
from typing import Final

from concentrator.application.ports.attention_port import AttentionPort
from concentrator.application.ports.sound_catalog_port import SoundCatalogPort
from concentrator.application.ports.sound_player_port import LOOP_FOREVER, SoundPlayback, SoundPlayerPort
from concentrator.application.timer.sound_candidates import sound_candidates
from concentrator.application.timer.timer_events import TimerChangedEvent
from concentrator.domain.timer.sound_ref import SoundRef
from concentrator.domain.timer.timer_settings import TimerSettings
from concentrator.domain.timer.timer_transition_enum import TimerTransitionEnum

_logger = logging.getLogger(__name__)

ALARM_PURPOSE: Final = "Alarm"

STOPPING_TRANSITIONS: Final = frozenset(
    {
        TimerTransitionEnum.ACKNOWLEDGED,
        TimerTransitionEnum.RESTARTED,
        TimerTransitionEnum.SNOOZED,
        TimerTransitionEnum.AUTO_STOPPED,
        TimerTransitionEnum.AUTO_RESTARTED,
    }
)


class AlarmCoordinator:
    """Subscribes to ``TimerChangedEvent``: plays the alarm sound at zero, stops it when ringing ends.

    The sound read at ringing time is used, so a sound changed while the timer runs applies to the next
    ringing. A sound that cannot be found falls back to ``timer.default_sound`` (WARNING), and the player
    falls back to the system beep. When no Concentrator window is active, the taskbar button flashes;
    nothing is shown in the notification area (ADR-038).
    """

    def __init__(
        self,
        *,
        player: SoundPlayerPort,
        catalog: SoundCatalogPort,
        attention: AttentionPort,
        settings: Callable[[], TimerSettings],
        fallback_sound: SoundRef,
    ) -> None:
        """Create the coordinator.

        Args:
            player: Alarm player instance.
            catalog: Finds the sound files.
            attention: Taskbar button.
            settings: Current timer settings.
            fallback_sound: ``timer.default_sound``.
        """
        self._player = player
        self._catalog = catalog
        self._attention = attention
        self._settings = settings
        self._fallback_sound = fallback_sound

    def on_timer_changed(self, event: TimerChangedEvent) -> None:
        """React to the timer transitions.

        Args:
            event: Published by the timer engine.
        """
        if TimerTransitionEnum.ALARM_STARTED in event.transitions:
            self._ring()
        elif STOPPING_TRANSITIONS.intersection(event.transitions):
            self._player.stop()

    def _ring(self) -> None:
        """Play the alarm and flash the taskbar button of an inactive application."""
        settings = self._settings()
        loops = LOOP_FOREVER if settings.loop_forever else settings.loop_count
        paths = sound_candidates(self._catalog, settings.sound, self._fallback_sound, ALARM_PURPOSE)
        playback = SoundPlayback(paths=paths, volume=settings.volume, loops=loops)
        played = self._player.play(playback)
        if played.is_failure:
            _logger.warning("Alarm sound not played: %s", [code.name for code in played.error_codes])
        if not self._attention.is_application_active():
            self._attention.request_attention()
