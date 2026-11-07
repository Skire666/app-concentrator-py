"""Sections a data file does not have yet, created from the ``concentrator.ini`` defaults."""

import logging

from concentrator.application.ports.clock_port import ClockPort
from concentrator.application.ports.id_generator_port import IdGeneratorPort
from concentrator.application.ports.user_data_session_port import UserDataSessionPort
from concentrator.application.storage.user_data import UserData
from concentrator.domain.settings.user_settings import UserSettings
from concentrator.domain.timer.timer_config import TimerConfig, TimerConfigId
from concentrator.domain.timer.timer_settings import TimerSettings

_logger = logging.getLogger(__name__)


class UserDataDefaults:
    """Builds new data files and completes files written before a section existed (phase 2 ``[timer]``)."""

    def __init__(self, ids: IdGeneratorPort, clock: ClockPort, timer: TimerSettings) -> None:
        """Create the helper.

        Args:
            ids: Ids of the created sections.
            clock: Creation instant of the created sections.
            timer: Timer configuration of a new file (``[timer]`` defaults of the ini).
        """
        self._ids = ids
        self._clock = clock
        self._timer = timer

    def initial(self, settings: UserSettings) -> UserData:
        """Content of a new data file.

        Args:
            settings: Settings of the new file.

        Returns:
            The data with every section.
        """
        return UserData.initial(settings, self._new_timer())

    def complete(self, data: UserData) -> UserData:
        """Add the missing sections.

        Args:
            data: Data read from a file.

        Returns:
            The data with every section (the same object when nothing was missing).
        """
        if data.timer is None:
            return data.with_timer(self._new_timer())
        return data

    def complete_session(self, session: UserDataSessionPort) -> None:
        """Complete the data just opened; a change is published, so the completed file is saved.

        Args:
            session: In-memory data, with the save coordinator already attached.
        """
        current = session.current()
        completed = self.complete(current)
        if completed is not current:
            _logger.info("Data file completed with the default timer configuration")
            session.apply(completed)

    def _new_timer(self) -> TimerConfig:
        """Create a timer configuration from the defaults.

        Returns:
            The configuration.
        """
        return TimerConfig.create(TimerConfigId(self._ids.new_id()), self._clock.now_utc(), self._timer)
