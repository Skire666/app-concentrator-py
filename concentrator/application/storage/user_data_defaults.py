"""Sections a data file does not have yet, created from the ``concentrator.ini`` defaults."""

import logging
from dataclasses import dataclass
from typing import Self

from concentrator.application.ports.clock_port import ClockPort
from concentrator.application.ports.id_generator_port import IdGeneratorPort
from concentrator.application.ports.user_data_session_port import UserDataSessionPort
from concentrator.application.settings.settings_defaults import SettingsDefaults
from concentrator.application.storage.user_data import UserData
from concentrator.application.timer.chime_defaults import ChimeDefaults
from concentrator.application.timer.timer_defaults import TimerDefaults
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.settings.user_settings import UserSettings, UserSettingsId
from concentrator.domain.timer.chime_settings import ChimeSettings
from concentrator.domain.timer.duration import Duration
from concentrator.domain.timer.hourly_chime import HourlyChime, HourlyChimeId
from concentrator.domain.timer.timer_config import TimerConfig, TimerConfigId
from concentrator.domain.timer.timer_preset import TimerPreset, TimerPresetId
from concentrator.domain.timer.timer_presets_collection import TimerPresetsCollection
from concentrator.domain.timer.timer_settings import TimerSettings

_logger = logging.getLogger(__name__)

AUTO_LABEL = ""


@dataclass(frozen=True, slots=True, kw_only=True)
class SectionDefaults:
    """Content of a section created from the ini.

    Attributes:
        timer: Timer configuration (``[timer]`` defaults).
        presets: Durations of the favorites, in order (``timer.default_presets_minutes``).
        chime_enabled: Switch of the hourly chime (``chime.default_enabled``).
        chime: Sound, volume and hours of the hourly chime (``[chime]`` defaults).
        settings: General values of new settings (``[settings]`` defaults).
    """

    timer: TimerSettings
    presets: tuple[Duration, ...]
    chime_enabled: bool
    chime: ChimeSettings
    settings: SettingsDefaults

    @classmethod
    def from_defaults(cls, timer: TimerDefaults, chime: ChimeDefaults, settings: SettingsDefaults) -> Self:
        """Gather the defaults of the sections.

        Args:
            timer: ``[timer]`` values.
            chime: ``[chime]`` values.
            settings: ``[settings]`` values.

        Returns:
            The section defaults.
        """
        return cls(
            timer=timer.settings,
            presets=timer.presets,
            chime_enabled=chime.enabled,
            chime=chime.settings,
            settings=settings,
        )


class UserDataDefaults:
    """Builds new data files and completes files written before a section existed.

    Phase 2 added ``[timer]``; phase 3 added the favorites and ``[hourly_chime]``. The favorites are
    seeded only when the file has no ``timer_presets`` key: ``timer_presets = []`` means the user deleted
    every favorite.
    """

    def __init__(self, ids: IdGeneratorPort, clock: ClockPort, sections: SectionDefaults) -> None:
        """Create the helper.

        Args:
            ids: Ids of the created sections.
            clock: Creation instant of the created sections.
            sections: Content of the created sections.
        """
        self._ids = ids
        self._clock = clock
        self._sections = sections

    def new_settings(self, language: LanguageEnum) -> UserSettings:
        """Settings of a new data file.

        Args:
            language: Language chosen in the first-run dialog.

        Returns:
            The settings; validate them with ``UserSettingsRules``.
        """
        general = self._sections.settings.general(language)
        return UserSettings.create(UserSettingsId(self._ids.new_id()), self._clock.now_utc(), general)

    def initial(self, settings: UserSettings) -> UserData:
        """Content of a new data file.

        Args:
            settings: Settings of the new file.

        Returns:
            The data with every section.
        """
        return UserData.initial(settings, self._new_timer(), self._new_presets(), self._new_chime())

    def complete(self, data: UserData) -> UserData:
        """Add the missing sections.

        Args:
            data: Data read from a file.

        Returns:
            The data with every section (the same object when nothing was missing).
        """
        completed = data
        if completed.timer is None:
            completed = completed.with_timer(self._new_timer())
        if completed.timer_presets is None:
            completed = completed.with_timer_presets(self._new_presets())
        if completed.hourly_chime is None:
            completed = completed.with_hourly_chime(self._new_chime())
        return completed

    def complete_session(self, session: UserDataSessionPort) -> None:
        """Complete the data just opened; a change is published, so the completed file is saved.

        Args:
            session: In-memory data, with the save coordinator already attached.
        """
        current = session.current()
        completed = self.complete(current)
        if completed is not current:
            sections: dict[str, object] = {
                "timer": current.timer,
                "timer_presets": current.timer_presets,
                "hourly_chime": current.hourly_chime,
            }
            missing = [name for name, value in sections.items() if value is None]
            _logger.info("Data file completed with the default sections: %s", ", ".join(missing))
            session.apply(completed)

    def _new_timer(self) -> TimerConfig:
        """Create a timer configuration from the defaults.

        Returns:
            The configuration.
        """
        return TimerConfig.create(TimerConfigId(self._ids.new_id()), self._clock.now_utc(), self._sections.timer)

    def _new_presets(self) -> TimerPresetsCollection:
        """Create the default favorites, with the automatic label.

        Returns:
            The favorites at positions ``0, 1, 2...``.
        """
        now = self._clock.now_utc()
        return TimerPresetsCollection(
            TimerPreset.create(
                TimerPresetId(self._ids.new_id()), now, label=AUTO_LABEL, duration=duration, position=position
            )
            for position, duration in enumerate(self._sections.presets)
        )

    def _new_chime(self) -> HourlyChime:
        """Create the hourly chime from the defaults.

        Returns:
            The chime.
        """
        return HourlyChime.create(
            HourlyChimeId(self._ids.new_id()),
            self._clock.now_utc(),
            enabled=self._sections.chime_enabled,
            settings=self._sections.chime,
        )
