"""Read use cases of the timer."""

from concentrator.application.ports.sound_catalog_port import SoundCatalogPort
from concentrator.application.ports.sound_player_port import SoundPlayerPort
from concentrator.application.ports.timer_config_reader_port import TimerConfigReaderPort
from concentrator.application.timer.timer_engine import TimerEngine
from concentrator.application.timer.timer_view import TimerView
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.timer.duration import Duration
from concentrator.domain.timer.sound_ref import SoundRef
from concentrator.domain.timer.timer_config import TimerConfig
from concentrator.domain.timer.timer_settings import TimerSettings


class TimerQueries:
    """Current countdown, stored configuration and available sounds."""

    def __init__(
        self,
        engine: TimerEngine,
        reader: TimerConfigReaderPort,
        catalog: SoundCatalogPort,
        player: SoundPlayerPort,
        snooze: Duration,
    ) -> None:
        """Create the queries.

        Args:
            engine: Runtime countdown.
            reader: Timer configuration reader.
            catalog: Built-in sounds and sound files.
            player: Tells whether a file can be played.
            snooze: ``timer.snooze_minutes``.
        """
        self._engine = engine
        self._reader = reader
        self._catalog = catalog
        self._player = player
        self._snooze = snooze

    @property
    def snooze(self) -> Duration:
        """Length of a snooze."""
        return self._snooze

    def current_view(self) -> TimerView:
        """Describe the countdown now.

        Returns:
            The read model.
        """
        return self._engine.view()

    def settings(self) -> TimerSettings:
        """Return the current timer settings.

        Returns:
            The stored settings (the ini defaults if none can be read).
        """
        return self._engine.settings()

    def config(self) -> DataResult[TimerConfig]:
        """Return the stored configuration.

        Returns:
            The configuration of the open data file.
        """
        return self._reader.read()

    def builtin_sounds(self) -> tuple[SoundRef, ...]:
        """Return the built-in sounds.

        Returns:
            The sounds, sorted by name.
        """
        return self._catalog.builtin_sounds()

    def check_sound(self, sound: SoundRef) -> ValidationResult:
        """Check that a chosen sound exists and can be played (edit dialog).

        Args:
            sound: Chosen sound.

        Returns:
            Success, ``AUDIO_FILE_NOT_FOUND``, ``AUDIO_FORMAT_UNSUPPORTED`` or ``AUDIO_DEVICE_UNAVAILABLE``.
        """
        resolved = self._catalog.resolve(sound)
        if resolved.data is None:
            return resolved.validation
        return self._player.check(resolved.data)
